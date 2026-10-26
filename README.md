# NYC Transit Hub

A class-project backend API for NYC subway stations, realtime arrivals, and
current service alerts.

The demo intentionally does not include trip planning, accessibility,
accounts, Firebase, or other future features described in `PROJECT.md`.

## Backend

Requires Python 3.11 or newer.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive API documentation is at
`http://localhost:8000/docs`.

Available endpoints:

- `GET /api/health`
- `GET /api/stations`
- `GET /api/stations/{station_id}`
- `GET /api/stations/{station_id}/arrivals`
- `GET /api/alerts`
- `GET /api/status`

The backend reads public MTA station, GTFS-realtime, and subway-alert feeds.
No MTA API key is required.

Run backend tests with:

```bash
cd backend
pytest
```

Do not commit `.env` files.