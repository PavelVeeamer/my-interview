"""The loop: one window of cases per interval, handed to the pipeline.

Everything with a side effect that the pipeline deliberately does not do is here — the
clock, the watermark, the ingest, the session and the wait. The pipeline is then pure
orchestration over ports, and this module is the only one that has to be reasoned about
in terms of time.

The watermark is in memory and nowhere else. A restart re-reads ``backfill_sec`` and the
dedup cache absorbs the repetition, which is what v3 did; persisting it would put the
engine outside its write scope for the sake of an optimisation dedup already makes free.
It advances only when the whole ingest succeeded: a per-target failure must not hold the
window back, and an ingest failure must, or the records that query never returned are
skipped forever.
"""

import asyncio
import logging
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import datetime, timedelta
from itertools import chain

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.config import ConfigCache
from app.adapters.tickets import Roster, mention_names
from app.core.ports import CaseSource, Clock, DedupCache, MessageSink
from app.core.render.context import RenderContext
from app.models.repositories import MessageMapRepository
from app.engine.pipeline import CycleReport, EnginePorts, run_cycle
from app.schemas.cases import CaseModel
from app.schemas.enums import CaseSourceKind
from app.settings import EngineSettings

logger = logging.getLogger(__name__)


class Poller:
    """One asyncio poll loop over one ticket system instance."""

    def __init__(
        self,
        source: CaseSource,
        config: ConfigCache,
        roster: Roster,
        sessions: async_sessionmaker[AsyncSession],
        cache: DedupCache,
        sink: MessageSink,
        clock: Clock,
        settings: EngineSettings,
        *,
        instance_url: str,
        heartbeat: Callable[[], None] | None = None,
    ) -> None:
        self._source = source
        self._config = config
        self._roster = roster
        self._sessions = sessions
        self._cache = cache
        self._sink = sink
        self._clock = clock
        self._settings = settings
        self._instance_url = instance_url
        self._heartbeat = heartbeat
        self._watermark: datetime | None = None

    async def run(self, shutdown: asyncio.Event) -> None:
        """Cycles until ``shutdown`` is set, checked between cycles and never mid-send."""
        while not shutdown.is_set():
            started = self._clock.now()
            try:
                report = await self.cycle()
            except Exception:
                logger.exception("Poll cycle failed; the watermark holds and the next cycle retries it")
            else:
                logger.info(
                    "Cycle done: %d created, %d updated, %d skipped, %d deferred, %d errors",
                    report.created,
                    report.updated,
                    report.skipped,
                    report.deferred,
                    report.errors,
                )
                if self._heartbeat is not None:
                    self._heartbeat()

            await self._pause(self.delay_after(started), shutdown)

    async def cycle(self) -> CycleReport:
        """One window: config, ingest, roster, pipeline."""
        now = self._clock.now()
        snapshot = await self._config.snapshot()
        since = self.since(now)

        cases = await self._ingest(since, now)
        self._watermark = now

        roster = await self._roster.resolve(mention_names(chain.from_iterable(cases.values())))
        ctx = RenderContext(instance_url=self._instance_url, now=now, roster=roster)

        async with self._sessions() as session:
            ports = EnginePorts(MessageMapRepository(session), self._cache, self._sink, session.commit)
            return await run_cycle(
                cases, snapshot, ctx, ports, max_updates=self._settings.max_updates_per_cycle
            )

    def since(self, now: datetime) -> datetime:
        """The start of the window this cycle asks for.

        The overlap carries the boundary back a little: Ticket API clock skew and pagination that
        is not a snapshot can otherwise drop a record that lands exactly on it, and
        reprocessing one is free because dedup decides create-versus-update. The backfill
        is a floor as well as the seed — after a long ingest outage an uncapped window
        grows into a query that times out forever, which never recovers on its own.
        """
        backfill = now - timedelta(seconds=self._settings.backfill_sec)
        if self._watermark is None:
            return backfill
        return max(self._watermark - timedelta(seconds=self._settings.overlap_sec), backfill)

    def delay_after(self, started: datetime) -> float:
        """What is left of the interval once the cycle is paid for; never negative."""
        elapsed = (self._clock.now() - started).total_seconds()
        return max(0.0, self._settings.poll_interval_sec - elapsed)

    async def _ingest(self, since: datetime, until: datetime) -> dict[CaseSourceKind, Sequence[CaseModel]]:
        return {
            CaseSourceKind.tech_case: list(await self._source.tech_cases(since, until)),
            CaseSourceKind.kb: list(await self._source.kb_articles(since, until)),
            CaseSourceKind.escalation: list(await self._source.escalations(since, until)),
        }

    async def _pause(self, delay: float, shutdown: asyncio.Event) -> None:
        if not delay:
            logger.warning("The cycle outran the poll interval; starting the next one without waiting")
            return
        with suppress(TimeoutError):
            await asyncio.wait_for(shutdown.wait(), delay)
