# NYC Transit Hub

## Project
A 6-person class project to build a web application for NYC public
transportation.

The application should help NYC transit riders understand their trip
and current service conditions in real time.

## Core User Questions
- How do I get from A to B?
- When is my train coming?
- Is my route affected by a disruption?
- What exactly changed?
- Which stations are affected?
- What should I do instead?
- How long will my trip take?

## Core Features

### 1. Trip Planning + Interactive Map
Users can enter an origin and destination and receive transit routes
with estimated travel time, walking portions, transfers, and a map
showing the selected route.

### 2. Real-Time Service Status
Show current status for MTA subway services, including delays,
reroutes, suspensions, and other service changes.

### 3. Delay / Reroute Information
Translate MTA service alerts into useful information for riders:
what happened, which service/stations are affected, and what the
change means for the rider.

### 4. Station Information
Station pages should show:
- Lines serving the station
- Current service disruptions
- Elevator/escalator accessibility information
- Relevant alerts
- Upcoming train arrivals

### 5. Accounts + Favorites
Users should eventually be able to create accounts and save
frequently used stations and transit services.

Firebase will be added later; it is NOT part of the initial backend setup.

## External Data

### MTA
- Subway GTFS-RT feeds
- MTA Service Alert feeds
- MTA GTFS Static Data
- MTA Subway Station / Station Complex data
- MTA Elevator & Escalator feeds

MTA feeds currently do not require an API key for the feeds we are using.

### Google
- Google Places API: origin/destination search
- Google Routes API: transit route planning and travel times
- Google Maps JavaScript API: interactive map

### Firebase
Planned later:
- Firebase Authentication
- Firestore
- Firebase Cloud Messaging

## Proposed Technology

Frontend:
- React
- Google Maps JavaScript API

Backend:
- Python
- FastAPI

External data:
- MTA feeds
- Google APIs

Firebase:
- Later, not initially

## Important Architecture Principles

The backend should separate:

1. External data retrieval/parsing
2. Transit/business logic
3. Trip planning logic
4. HTTP API endpoints
5. Shared data models

The frontend should not need to understand raw MTA GTFS/protobuf
structures.

MTA source-specific code should be isolated from application logic.

The project should remain reasonably simple because this is a
6-person, 9-week class project. Avoid unnecessary abstractions.

## Team Structure

The team has 6 people, working roughly as 3 pairs:

Pair A:
- Real-time arrivals
- Station information
- Accessibility

Pair B:
- Service alerts
- Service status dashboard
- Delay/reroute information

Pair C:
- Trip planning
- Interactive map
- Google APIs

Ownership should be primarily feature-based so each pair can work
end-to-end rather than having one person responsible for an entire
architectural layer.

## Current Status

The repository is currently essentially empty.

We are establishing the project architecture before implementing
features.

Do NOT assume that proposed architecture is final.
