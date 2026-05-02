"""
Satellite Pass Scheduler

Responsibilities:
- determine which satellite has the next visible pass
- compute prediction windows
- provide async scheduling loop for automatic tracking
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from .predictor import PassEvent, Predictor
from .tle_manager import TleManager


@dataclass
class ScheduledPass:
    name: str
    norad_id: int
    event: PassEvent


class Scheduler:
    """
    High-level scheduler that:
    - loads TLEs
    - predicts passes for tracked satellites
    - selects the next pass above min elevation
    """

    def __init__(
        self,
        predictor: Predictor,
        tle_manager: TleManager,
        tracked: dict[str, int],  # { "ISS": 25544, ... }
    ):
        self.predictor = predictor
        self.tle_manager = tle_manager
        self.tracked = tracked  # name → NORAD ID

    def _predict_single(self, name: str, norad: int) -> ScheduledPass | None:
        tle_text = self.tle_manager.get_tle_text(norad)
        if not tle_text:
            return None

        event = self.predictor.predict_first_pass(tle_text)
        if not event:
            return None

        return ScheduledPass(name=name, norad_id=norad, event=event)

    def predict_all(self) -> list[ScheduledPass]:
        results = []

        for name, norad in self.tracked.items():
            sp = self._predict_single(name, norad)
            if sp:
                results.append(sp)

        # Sort by AOS time
        results.sort(key=lambda p: p.event.aos_time)
        return results

    def next_pass(self) -> ScheduledPass | None:
        all_passes = self.predict_all()
        now = datetime.now(timezone.utc)

        for p in all_passes:
            if p.event.aos_time > now:
                return p

        return None

    async def run_scheduler(
        self,
        callback_start: callable,
        callback_end: callable,
        poll_interval: float = 60.0,
    ):
        """
        Background loop that:
        - waits for next pass
        - triggers callback_start(event)
        - waits until LOS
        - triggers callback_end(event)
        """

        import asyncio

        while True:
            nxt = self.next_pass()

            if not nxt:
                await asyncio.sleep(poll_interval)
                continue

            now = datetime.now(timezone.utc)
            wait_seconds = (nxt.event.aos_time - now).total_seconds()

            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            # Start tracking
            callback_start(nxt)

            # Wait until LOS
            los_wait = (nxt.event.los_time - datetime.now(timezone.utc)).total_seconds()
            if los_wait > 0:
                await asyncio.sleep(los_wait)

            # End tracking
            callback_end(nxt)
