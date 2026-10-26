import csv
import io
from dataclasses import dataclass


@dataclass(frozen=True)
class MTAStationRow:
    complex_id: str
    stop_id: str
    name: str
    borough: str
    routes: tuple[str, ...]
    latitude: float
    longitude: float
    north_direction_label: str | None
    south_direction_label: str | None


def parse_station_rows(csv_text: str) -> list[MTAStationRow]:
    rows: list[MTAStationRow] = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        stop_id = (row.get("GTFS Stop ID") or "").strip()
        complex_id = (row.get("Complex ID") or "").strip()
        if not stop_id or not complex_id:
            continue
        rows.append(
            MTAStationRow(
                complex_id=complex_id,
                stop_id=stop_id,
                name=(row.get("Stop Name") or "Unknown station").strip(),
                borough=(row.get("Borough") or "").strip(),
                routes=tuple((row.get("Daytime Routes") or "").split()),
                latitude=float(row["GTFS Latitude"]),
                longitude=float(row["GTFS Longitude"]),
                north_direction_label=(row.get("North Direction Label") or "").strip() or None,
                south_direction_label=(row.get("South Direction Label") or "").strip() or None,
            )
        )
    return rows
