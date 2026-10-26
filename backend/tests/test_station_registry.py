from app.transit.station_registry import StationRegistry


class FakeClient:
    async def get_stations_csv(self) -> str:
        return (
            "Complex ID,GTFS Stop ID,Stop Name,Borough,Daytime Routes,"
            "GTFS Latitude,GTFS Longitude,North Direction Label,South Direction Label\n"
            "611,R16,Times Sq-42 St,M,N Q R W,40.754,-73.987,Queens,Brooklyn\n"
            "611,127,Times Sq-42 St,M,1 2 3,40.755,-73.987,Uptown,Downtown\n"
        )


async def test_registry_combines_stops_into_canonical_complex():
    registry = StationRegistry(FakeClient())

    await registry.ensure_loaded()
    station = registry.get("mta-complex:611")

    assert station is not None
    assert set(station.stop_ids) == {"R16", "127"}
    assert registry.resolve_stop_id("R16N") == "mta-complex:611"
    assert registry.resolve_stop_id("127S") == "mta-complex:611"
