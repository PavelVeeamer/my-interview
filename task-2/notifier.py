"""Sends SLA notifications about support cases to chat channels."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from dedup import AlertInterval, InMemoryCache, IntervalCacheItem


@dataclass
class Channel:
    name: str
    intervals: list[AlertInterval] | None = None


@dataclass
class Notification:
    case_id: str
    title: str
    status: str
    minutes_left: float

    def cache_item(self) -> IntervalCacheItem:
        return IntervalCacheItem(
            key=f"sla:{self.case_id}",
            value={"title": self.title, "status": self.status, "minutes_left": self.minutes_left},
            ttl=int(timedelta(days=7).total_seconds()),
        )

    def render(self) -> str:
        return f"[{self.case_id}] {self.title} — {self.status}, {self.minutes_left:.0f} min left"


class Sender(Protocol):
    def post(self, channel: str, case_id: str, text: str) -> None:
        """Post a new message about the case."""

    def update(self, channel: str, case_id: str, text: str) -> None:
        """Edit the message already posted about the case."""


def process_notification(notification: Notification, cache: InMemoryCache, channels: list[Channel], sender: Sender) -> None:
    cache_item = notification.cache_item()
    to_send = [channel for channel in channels if cache_item.need_to_emit(cache, channel)]
    for channel in to_send:
        sender.post(channel.name, notification.case_id, notification.render())
        cache.set(cache_item.key, cache_item.dumps(), cache_item.ttl)
