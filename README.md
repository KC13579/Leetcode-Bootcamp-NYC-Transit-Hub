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

The backend reads public MTA GTFS-realtime, subway-alert and elevator feeds, and
the MTA station list published on data.ny.gov. No MTA API key is required.

On Windows, activate the environment with `backend\.venv\Scripts\activate`.

Run backend tests with:

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

Do not commit `.env` files.

## Frontend

Requires Node.js 18 or newer. With the backend running:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The app has three tabs:

- **Plan**: subway map, station or address search, route options and a route map.
- **Status**: live status for every line, rider-friendly alert explanations,
  and reroute / skipped-stop evidence for each line.
- **Saved**: saved stations and lines, plus sign-in when Firebase is configured.

Station pages show live arrivals, elevator/escalator status and alerts.

### Optional integrations

| Feature | What to configure | Without it |
| --- | --- | --- |
| Real trip planning and address search | `GOOGLE_MAPS_API_KEY` in `backend/.env` | Station-to-station demo routes, clearly labeled |
| Accounts that sync saved items | `FIREBASE_PROJECT_ID` and credentials in `backend/.env`, plus the `VITE_FIREBASE_*` values in `frontend/.env` (see `frontend/.env.example`) | Saved items are kept on the device |
