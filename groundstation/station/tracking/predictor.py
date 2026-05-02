"""
Modern satellite pass predictor.

Replaces the legacy BeyondTools with:
- clean async API
- typed pass objects
- UTC-aware datetimes
- separation of prediction vs. tracking data generation
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import degrees

from beyond.dates import Date
from beyond.frames import create_station
from beyond.io.tle import Tle


@dataclass
class PassEvent:
    aos_time: datetime
    aos_az: float
    max_time: datetime
    max_az: float
    max_el: float
    los_time: datetime
    los_az: float


@dataclass
class TrackPoint:
    time: datetime
    az: float
    el: float
    range_km: float


class Predictor:
    """
    High-level satellite pass predictor.

    Responsibilities:
    - compute first visible pass
    - generate tracking data (az/el vs time)
    """

    def __init__(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        min_max_elevation: float = 10.0,
        max_pred_days: int = 3,
        step_seconds: int = 5,
    ):
        self.station = create_station(
            "GroundStation",
            (latitude, longitude, altitude),
        )

        self.min_max_el = min_max_elevation
        self.max_pred_time = timedelta(days=max_pred_days)
        self.step = timedelta(seconds=step_seconds)

    @staticmethod
    def _to_utc(dt: str) -> datetime:
        """Convert naive ISO string to UTC-aware datetime."""
        return datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f").replace(
            tzinfo=timezone.utc
        )

    def predict_first_pass(self, tle_text: str) -> PassEvent | None:
        """
        Return the first pass above min_max_el elevation.
        """

        tle = Tle(tle_text)
        ok_aos = False
        ok_max = False
        data = {}

        for orb in self.station.visibility(
            tle.orbit(),
            start=Date.now(),
            stop=self.max_pred_time,
            step=timedelta(seconds=10),
            events=True,
        ):
            if orb.event and orb.event.info.startswith("AOS"):
                data["aos_time"] = self._to_utc(orb.date)
                data["aos_az"] = degrees(-orb.theta) % 360
                ok_aos = True

            if orb.event and orb.event.info.startswith("MAX"):
                el = degrees(orb.phi)
                if el >= self.min_max_el:
                    data["max_time"] = self._to_utc(orb.date)
                    data["max_az"] = degrees(-orb.theta) % 360
                    data["max_el"] = el
                    ok_max = True
                else:
                    ok_aos = False
                    ok_max = False

            if orb.event and orb.event.info.startswith("LOS"):
                if ok_aos and ok_max:
                    data["los_time"] = self._to_utc(orb.date)
                    data["los_az"] = degrees(-orb.theta) % 360

                    return PassEvent(**data)

        return None

    def generate_track(
        self,
        tle_text: str,
        delay_hours: float = 0.0,
    ) -> tuple[list[TrackPoint], PassEvent | None]:
        """
        Generate tracking points (az/el/range) and return the pass event.
        """

        tle = Tle(tle_text)
        track: list[TrackPoint] = []
        data = {}
        ok_aos = False
        ok_max = False

        for orb in self.station.visibility(
            tle.orbit(),
            start=Date.now() + timedelta(hours=delay_hours),
            stop=self.max_pred_time,
            step=self.step,
            events=True,
        ):
            dt = self._to_utc(orb.date)
            az = degrees(-orb.theta) % 360
            el = degrees(orb.phi)
            rng = orb.r / 1000.0  # meters → km

            track.append(TrackPoint(dt, az, el, rng))

            if orb.event and orb.event.info.startswith("AOS"):
                data["aos_time"] = dt
                data["aos_az"] = az
                ok_aos = True

            if orb.event and orb.event.info.startswith("MAX"):
                if el >= self.min_max_el:
                    data["max_time"] = dt
                    data["max_az"] = az
                    data["max_el"] = el
                    ok_max = True
                else:
                    ok_aos = False
                    ok_max = False

            if orb.event and orb.event.info.startswith("LOS"):
                if ok_aos and ok_max:
                    data["los_time"] = dt
                    data["los_az"] = az
                    return track, PassEvent(**data)
                else:
                    track.clear()

        return [], None
