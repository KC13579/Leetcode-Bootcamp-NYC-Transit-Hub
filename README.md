# NYC Transit Hub

A class-project backend API for NYC subway stations, realtime arrivals, and
current service alerts.

Transit planning, accessibility, reroutes, Firebase-authenticated favorites and
notification subscriptions are implemented in controller, service and repository
layers. Google and Firebase features require your own provider configuration;
unconfigured integrations return HTTP 503. Every backend method has an English
entry docstring.
See [the backend development framework](backend/README.md) for layer ownership,
endpoints, configuration and verification steps.

## Backend

Requires Python 3.11 or newer. Run these commands from the repository root.

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e './backend[dev]'
python -m uvicorn backend.app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive API documentation is at
`http://localhost:8000/docs`.

Available endpoints:

- `GET /api/health`
- `GET /api/map/lines`
- `GET /api/stations`
- `GET /api/stations/{station_id}`
- `GET /api/stations/{station_id}/arrivals`
- `GET /api/alerts`
- `GET /api/status`

The backend reads public MTA station, GTFS-realtime, and subway-alert feeds.
No MTA API key is required.

Run backend tests with:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

Do not commit `.env` files.
