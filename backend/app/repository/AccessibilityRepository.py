import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from backend.app.models.planning import AccessibilityEquipment, StationAccessibility
from backend.app.sources.mta.client import MTAClient
from backend.app.repository.StationRepository import StationRepository


class AccessibilityRepository:
    def __init__(self, client: MTAClient, stations: StationRepository):
        """Store the dependencies and initialize the state required by this component."""
        self.client = client
        self.stations = stations

    async def get_station_accessibility(self, station_id: str) -> StationAccessibility:
        """Load station equipment and report outages without assuming missing records mean normal operation."""
        inventory, outages = await asyncio.gather(
            self.client.get_json_feed(
                "nyct%2Fnyct_ene_equipments.json", ttl_seconds=3600
            ),
            self.client.get_json_feed("nyct%2Fnyct_ene.json"),
        )
        equipment = []
        for row in inventory:
            canonical = f"mta-complex:{str(row.get('stationcomplexid', '')).strip()}"
            if canonical != station_id:
                stop = str(row.get("elevatorsgtfsstopid", "")).strip()
                if self.stations.resolve_stop_id(stop) != station_id:
                    continue
            equipment_id = str(row.get("equipmentno", ""))
            if not equipment_id or row.get("equipmenttype") not in {"EL", "ES"}:
                continue
            matches = [
                item for item in outages if str(item.get("equipment")) == equipment_id
            ]
            now = datetime.now(UTC)
            active = [
                item
                for item in matches
                if item.get("isupcomingoutage") != "Y"
                and (
                    self._time(item.get("outagedate")) is None
                    or self._time(item.get("outagedate")) <= now
                )
            ]
            future = [item for item in matches if item not in active]
            outage = (
                max(
                    active,
                    key=lambda item: self._time(item.get("outagedate"))
                    or datetime.min.replace(tzinfo=UTC),
                )
                if active
                else (
                    min(
                        future,
                        key=lambda item: self._time(item.get("outagedate"))
                        or datetime.max.replace(tzinfo=UTC),
                    )
                    if future
                    else {}
                )
            )
            equipment.append(
                AccessibilityEquipment(
                    equipment_id=equipment_id,
                    kind="elevator" if row["equipmenttype"] == "EL" else "escalator",
                    status="out_of_service" if active else "unknown",
                    location=row.get("serving") or row.get("shortdescription"),
                    reason=outage.get("reason"),
                    outage_start=self._time(outage.get("outagedate")),
                    expected_restore_at=self._time(
                        outage.get("estimatedreturntoservice")
                    ),
                    upcoming=bool(outage) and not active,
                    alternative_route=row.get("alternativeroute") or None,
                )
            )
        return StationAccessibility(
            station_id=station_id,
            equipment=equipment,
            updated_at=datetime.now(UTC),
            equipment_status_complete=False,
            note="Equipment absent from the outage feed has unknown live status; ADA status describes station design, not a guaranteed step-free path.",
        )

    @staticmethod
    def _time(value: str | None) -> datetime | None:
        """Parse a provider timestamp into a timezone-aware datetime when available."""
        if not value:
            return None
        try:
            return (
                datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
                .replace(tzinfo=ZoneInfo("America/New_York"))
                .astimezone(UTC)
            )
        except ValueError:
            return None
