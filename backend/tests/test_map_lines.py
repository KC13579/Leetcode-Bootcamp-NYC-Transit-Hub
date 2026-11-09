from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from backend.app.sources.mta.map_lines import parse_map_network


def _gtfs_zip() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "routes.txt",
            "route_id,route_short_name,route_color\nA,A,0039A6\n",
        )
        archive.writestr(
            "trips.txt",
            "route_id,trip_id,shape_id\n"
            "A,trip-north,shape-north\n"
            "A,trip-south,shape-south\n",
        )
        archive.writestr(
            "shapes.txt",
            "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
            "shape-north,40.70,-74.00,1\n"
            "shape-north,40.71,-73.99,2\n"
            "shape-north,40.72,-73.98,3\n"
            "shape-south,40.72,-73.98,1\n"
            "shape-south,40.71,-73.99,2\n"
            "shape-south,40.70,-74.00,3\n",
        )
    return buffer.getvalue()


def test_parse_map_network_deduplicates_opposite_directions():
    network = parse_map_network(_gtfs_zip())

    assert len(network.lines) == 1
    assert network.lines[0].route == "A"
    assert network.lines[0].color == "#0039A6"
    assert network.lines[0].coordinates[0] == (40.70, -74.00)
    assert network.lines[0].coordinates[-1] == (40.72, -73.98)
