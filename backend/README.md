# Backend implementation

The backend uses Controller -> Service -> Repository layers. All registered
feature methods have implementations and English entry docstrings. Imports use
`backend.app.*`; React remains the view layer.

## Run

Run commands from the repository root, which contains `backend` and `frontend`:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e './backend[dev]'
cp backend/.env.example backend/.env
backend/.venv/bin/python -m uvicorn backend.app.main:app --reload
```

The existing PyCharm `NYC Transit API` configuration uses the same module and
project-root working directory. Swagger is at http://localhost:8000/docs.
`backend/.env` is loaded automatically without overriding process variables.

## External configuration

Public MTA features need no credentials for the configured sources. Google and
Firebase use real provider adapters and require your project's configuration;
there is no production fallback to mock routes, mock authentication or an
in-memory user database.

| Setting | Purpose |
| --- | --- |
| GOOGLE_MAPS_API_KEY | Server key for Google Routes and Places API (New) |
| FIREBASE_PROJECT_ID | Firebase project used for token verification and Firestore |
| GOOGLE_APPLICATION_CREDENTIALS | Absolute path to a service-account JSON file, or leave empty when Application Default Credentials are available |
| NOTIFICATIONS_ENABLED | Defaults to false; enables the periodic FCM worker when explicitly set to true |
| NOTIFICATION_INTERVAL_SECONDS | Worker interval, at least 30 seconds |
| FEED_MAX_AGE_SECONDS | Maximum accepted source age for a fresh service-alert snapshot |
| ALLOWED_ORIGINS | Comma-separated frontend origins; defaults to http://localhost:5173 |

Enable the Google APIs in your own project. Configure Firebase Authentication
for frontend login and create a Firestore database. Use an appropriately scoped
server identity with the required Firebase Auth, Firestore and FCM permissions.
No cloud project, billing, credentials or provider services are created by this
repository. Keep service-account files outside the repository.

Missing Google/Firebase configuration returns HTTP 503 for the affected
features. Missing or invalid Bearer tokens return HTTP 401. Firebase verification
uses the Admin SDK, including signature, expiry and revocation checks; a caller
cannot choose the user ID used for personal data access.

## Feature map

All paths have the `/api` prefix.

| Method and path | Responsibility | Controller / Service / Repository |
| --- | --- | --- |
| GET /health | Process liveness | Health / none / none |
| GET /stations | Name or line search | Station / Station / Station |
| GET /stations/{station_id} | Canonical station metadata | Station / Station / Station |
| GET /stations/{station_id}/arrivals | Upcoming train arrivals | Station / Arrival / Arrival |
| GET /stations/{station_id}/accessibility | Equipment inventory and reported outages | Station / Accessibility / Accessibility |
| GET /map/lines | Static map geometry | Map / Map / Map |
| GET /alerts | Structured service alerts with cause, scope and freshness | Alert / Alert / Alert |
| GET /status | Per-line alert aggregation | Status / Status / shared AlertService |
| POST /trips/plan | Google TRANSIT alternatives with walking/transit steps | Trip / Trip / Trip |
| POST /trips/impacts | Segment-level time and disruption matching | Trip / Trip / shared AlertService |
| GET /places/autocomplete | NYC-biased place suggestions | Place / Place / Place |
| GET /places/{place_id} | Place name, address and coordinates | Place / Place / Place |
| GET /routes/{route_id}/reroutes | Explicit changes from trip-update and scheduled-stop evidence | Reroute / Reroute / Reroute |
| GET /me/favorites | Current user's favorites | Favorite / Favorite / Favorite |
| PUT /me/favorites/{kind}/{target_id} | Idempotent favorite creation | Favorite / Favorite / Favorite |
| DELETE /me/favorites/{kind}/{target_id} | Idempotent favorite removal | Favorite / Favorite / Favorite |
| GET /me/subscriptions | Current user's notification preferences | Notification / Notification / Notification |
| PUT /me/subscriptions/{kind}/{target_id} | Explicit subscription opt-in or opt-out | Notification / Notification / Notification |
| DELETE /me/subscriptions/{kind}/{target_id} | Subscription removal | Notification / Notification / Notification |
| PUT /me/subscriptions/devices/register | Register the logged-in device's FCM token | Notification / Notification / Notification |
| POST /me/subscriptions/devices/remove | Remove the logged-in user's FCM registration | Notification / Notification / Notification |

Private requests require `Authorization: Bearer <Firebase ID token>`.
`kind` is `station` or `route`. Project station IDs use `mta-complex:<id>`.
`direction=0` means northbound and `direction=1` means southbound for the subway
reroute endpoint. Place autocomplete/detail calls accept a shared `session_token`.

## Important data behavior

- `/health` reports application liveness, not external-provider readiness.
- Routes include provider duration, transfer count, walking/transit segments and
  geometry. Station IDs are assigned to provider stops only when matching is
  unambiguous. Missing matches stay null. No returned routes means an empty list.
- Line geometry is static; it is not a train location or a live reroute shape.
- Accessibility joins equipment by station-complex/GTFS IDs and outages by
  equipment ID. A reported outage is out of service. Missing outage evidence
  remains unknown, because an outage-only feed cannot prove normal operation.
  `accessible` describes the station's static ADA design; it does not guarantee
  an available step-free path. Partial station accessibility remains null.
- Reroutes retain individual trip IDs. Only explicit SKIPPED updates identify
  skipped stops; missing updates do not. Added stops require an exact scheduled
  trip match. Listed future stops are partial evidence rather than a guaranteed
  complete stopping pattern. Stale or insufficient evidence stays unknown.
- Trip impact checks match line, known station endpoints, compatible direction
  IDs and time windows. Unresolved intermediate-stop overlap is marked unknown,
  not asserted to affect a precise segment. Google headsign text is not treated
  as a GTFS direction ID.
- Statuses are Unknown when source timestamps are absent or stale; an empty
  stale feed does not produce Good Service.
- Upstream failures return sanitized 502/504 responses. Configuration or quota
  unavailability returns 503. No external error response exposes credentials.

## Notifications and persistence

Firestore collections are `transit_favorites`, `transit_subscriptions`,
`transit_devices` and `transit_deliveries`. Favorite and subscription keys combine
verified user ID, target kind and target ID through SHA-256; writes are idempotent.
Device removal checks ownership transactionally. SDK Firestore calls run off the
async event loop.

Register a device token, then explicitly enable a subscription before enabling
the worker. It checks active service alerts and station equipment outages,
ignores stale alerts, acquires a Firestore delivery lease and stores the result.
Repeated snapshots are deduplicated across devices and subscription targets.
Invalid FCM registrations are removed. Notification errors are isolated so other
subscribers can still be processed. The worker is cancelled on app shutdown.

Delivery is retryable, not exactly once: a process crash after FCM accepts a
message but before Firestore records success can lead to a retry. Use the
`expires_at` field for a Firestore TTL policy on `transit_deliveries` if desired.
Configure a single worker initially; leases provide cross-process deduplication,
but this is a classroom-sized polling system rather than a durable queue.

## Tests and verification

```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

The suite exercises controller/service/repository behavior, location mapping,
upstream errors, token verification calls, per-user isolation, opt-out, delivery
deduplication, explicit skip evidence, freshness and English method documentation.
Google requests, Firebase verification and Firestore/FCM operations are substituted
with test adapters or SDK mocks. Real public MTA station, accessibility, status
and reroute requests have also been checked. Real Google/Firebase integration
still needs your credentials; tests do not create cloud data or send real pushes.

Provider documentation:
- https://www.mta.info/developers
- https://developers.google.com/maps/documentation/routes/transit-route
- https://developers.google.com/maps/documentation/places/web-service/using-session-tokens
- https://firebase.google.com/docs/auth/admin/verify-id-tokens
- https://firebase.google.com/docs/cloud-messaging/send/admin-sdk
