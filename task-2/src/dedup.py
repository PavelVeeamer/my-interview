"""Dedup: decides whether a notification about a case goes out to a channel again."""

import json
from contextlib import suppress
from dataclasses import dataclass
from typing import Self


class InMemoryCache:
    """Stand-in for Redis: string keys, string values, TTL ignored."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._data[key] = value


@dataclass
class AlertInterval:
    """A band of "minutes left before the SLA is breached", e.g. 30<>10."""

    high_edge: int
    low_edge: int

    def __str__(self) -> str:
        return f"{self.high_edge}<>{self.low_edge}"

    def __contains__(self, minutes: float) -> bool:
        return self.high_edge >= minutes > self.low_edge

    @classmethod
    def from_string(cls, s: str) -> Self | None:
        with suppress(Exception) as result:
            high, low = s.split("<>", 2)
            result = cls(int(high), int(low))
        return result

    @classmethod
    def from_time(cls, minutes_left: float, intervals=None) -> Self | None:
        if not minutes_left:
            return None
        return next((interval for interval in intervals or [] if minutes_left in interval), None)


DEFAULT_INTERVALS = [
    AlertInterval.from_string("60<>30"),
    AlertInterval.from_string("30<>10"),
    AlertInterval.from_string("10<>0"),
]


@dataclass
class CacheItem:
    """What was last sent about a case, stored in the cache as JSON."""

    key: str
    value: dict
    ttl: int

    def dumps(self) -> str:
        return json.dumps(self.value)

    def need_to_emit(self, cache: InMemoryCache, channel) -> bool:
        """True if the notification has to be sent."""
        old_cache_item = self.load_old_item(cache)
        return not old_cache_item or self.value != old_cache_item.value

    def load_old_item(self, cache: InMemoryCache) -> Self | None:
        raw = cache.get(self.key)
        if raw is None:
            return None
        return type(self)(key=self.key, value=json.loads(raw), ttl=self.ttl)


@dataclass
class IntervalCacheItem(CacheItem):
    def need_to_emit(self, cache: InMemoryCache, channel) -> bool:
        old_cache_item = self.load_old_item(cache)
        if not old_cache_item:
            return True

        intervals = channel.intervals or DEFAULT_INTERVALS
        old_interval = AlertInterval.from_time(old_cache_item.value.get("minutes_left"), intervals)
        current_interval = AlertInterval.from_time(self.value["minutes_left"], intervals)
        # check only current interval, because old interval can be None, but current should be not None
        if current_interval and old_interval != current_interval:
            return True

        current = {k: v for k, v in self.value.items() if k != "minutes_left"}
        old = {k: v for k, v in old_cache_item.value.items() if k != "minutes_left"}
        return current != old
