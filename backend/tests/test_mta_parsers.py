from datetime import UTC, datetime, timedelta

from google.transit import gtfs_realtime_pb2

from app.sources.mta.alerts import parse_active_alerts
from app.sources.mta.realtime import feed_paths_for_routes, parse_arrivals
from app.sources.mta.static import parse_station_rows


def test_parses_static_station_csv():
    csv_text = (
        "Complex ID,GTFS Stop ID,Stop Name,Borough,Daytime Routes,"
        "GTFS Latitude,GTFS Longitude,North Direction Label,South Direction Label\n"
        "611,R16,Times Sq-42 St,M,N Q R W,40.754,-73.987,Queens,Brooklyn\n"
    )

    rows = parse_station_rows(csv_text)

    assert rows[0].complex_id == "611"
    assert rows[0].routes == ("N", "Q", "R", "W")


def test_parses_realtime_arrival():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "trip"
    entity.trip_update.trip.trip_id = "trip-1"
    entity.trip_update.trip.route_id = "N"
    update = entity.trip_update.stop_time_update.add()
    update.stop_id = "R16N"
    update.arrival.time = 1_800_000_000

    arrivals = parse_arrivals(feed.SerializeToString())

    assert arrivals[0].stop_id == "R16N"
    assert arrivals[0].route == "N"
    assert arrivals[0].arrival_time == datetime.fromtimestamp(1_800_000_000, tz=UTC)


def test_shuttle_stations_query_both_possible_feeds():
    assert feed_paths_for_routes(["S"]) == {
        "nyct%2Fgtfs",
        "nyct%2Fgtfs-ace",
    }


def test_excludes_inactive_alerts():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "old-alert"
    entity.alert.header_text.translation.add(text="Old delay", language="en")
    period = entity.alert.active_period.add()
    period.start = int((now - timedelta(hours=2)).timestamp())
    period.end = int((now - timedelta(hours=1)).timestamp())

    assert parse_active_alerts(feed.SerializeToString(), now=now) == []
