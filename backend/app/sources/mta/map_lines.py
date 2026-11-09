from collections import defaultdict
from csv import DictReader
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile

from backend.app.models import MapLine, MapNetwork


DEFAULT_LINE_COLOR = "#8A8A8A"
ROUTE_ALIASES = {"6X": "6", "7X": "7", "FX": "F"}


def _rows(archive: ZipFile, filename: str) -> list[dict[str, str]]:
    """Read a UTF-8 CSV table from a GTFS ZIP archive."""
    with archive.open(filename) as raw_file:
        text_file = TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
        return list(DictReader(text_file))


def _path_length(points: list[tuple[float, float]]) -> float:
    """Estimate relative coordinate-path length for selecting representative map shapes."""
    return sum(
        ((lat_b - lat_a) ** 2 + (lon_b - lon_a) ** 2) ** 0.5
        for (lat_a, lon_a), (lat_b, lon_b) in zip(points, points[1:])
    )


def _simplify(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Reduce map geometry points while preserving the final coordinate."""
    if len(points) <= 2:
        return points
    simplified = points[::3]
    if simplified[-1] != points[-1]:
        simplified.append(points[-1])
    return simplified


def parse_map_network(
    gtfs_zip: bytes,
    *,
    max_shapes_per_route: int = 4,
) -> MapNetwork:
    """Build lightweight map geometry from the official MTA static GTFS archive."""
    with ZipFile(BytesIO(gtfs_zip)) as archive:
        route_rows = _rows(archive, "routes.txt")
        trip_rows = _rows(archive, "trips.txt")
        shape_rows = _rows(archive, "shapes.txt")

    route_details = {
        row["route_id"]: (
            row.get("route_short_name") or row["route_id"],
            f"#{row['route_color']}" if row.get("route_color") else DEFAULT_LINE_COLOR,
        )
        for row in route_rows
    }
    shape_route_ids = {
        row["shape_id"]: row["route_id"]
        for row in trip_rows
        if row.get("shape_id") and row.get("route_id") in route_details
    }

    shape_points: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for row in shape_rows:
        shape_id = row.get("shape_id")
        if shape_id not in shape_route_ids:
            continue
        shape_points[shape_id].append(
            (
                int(row["shape_pt_sequence"]),
                float(row["shape_pt_lat"]),
                float(row["shape_pt_lon"]),
            )
        )

    candidates: dict[
        str, dict[tuple[tuple[float, float], tuple[float, float]], MapLine]
    ] = defaultdict(dict)
    lengths: dict[str, float] = {}

    for shape_id, sequenced_points in shape_points.items():
        route_id = shape_route_ids[shape_id]
        route, color = route_details[route_id]
        route = ROUTE_ALIASES.get(route, route)
        points = [(lat, lon) for _, lat, lon in sorted(sequenced_points)]
        if len(points) < 2:
            continue

        endpoints = tuple(
            sorted(
                (
                    (round(points[0][0], 4), round(points[0][1], 4)),
                    (round(points[-1][0], 4), round(points[-1][1], 4)),
                )
            )
        )
        line = MapLine(
            id=f"{route}:{shape_id}",
            route=route,
            color=color,
            coordinates=_simplify(points),
        )
        length = _path_length(points)
        previous = candidates[route].get(endpoints)
        if previous is None or length > lengths[previous.id]:
            candidates[route][endpoints] = line
            lengths[line.id] = length

    lines: list[MapLine] = []
    for route in sorted(candidates):
        route_lines = sorted(
            candidates[route].values(),
            key=lambda line: lengths[line.id],
            reverse=True,
        )
        lines.extend(route_lines[:max_shapes_per_route])

    return MapNetwork(lines=lines)
