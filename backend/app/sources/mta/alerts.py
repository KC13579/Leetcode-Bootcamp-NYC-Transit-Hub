from dataclasses import dataclass
from datetime import UTC, datetime

from google.transit import gtfs_realtime_pb2


@dataclass(frozen=True)
class MTAAlert:
    id: str
    title: str
    description: str | None
    routes: tuple[str, ...]
    stop_ids: tuple[str, ...]
    effect: str
    starts_at: datetime | None
    ends_at: datetime | None


def _text(translated_string: object) -> str | None:
    translations = translated_string.translation
    if not translations:
        return None
    english = next(
        (item.text for item in translations if item.language in ("en", "")),
        None,
    )
    return english or translations[0].text


def _as_datetime(timestamp: int) -> datetime | None:
    return datetime.fromtimestamp(timestamp, tz=UTC) if timestamp else None


def parse_active_alerts(payload: bytes, now: datetime | None = None) -> list[MTAAlert]:
    message = gtfs_realtime_pb2.FeedMessage()
    message.ParseFromString(payload)
    now = now or datetime.now(UTC)
    now_timestamp = int(now.timestamp())
    parsed: list[MTAAlert] = []

    for entity in message.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert
        periods = list(alert.active_period)
        active_period = next(
            (
                period
                for period in periods
                if (not period.start or period.start <= now_timestamp)
                and (not period.end or period.end >= now_timestamp)
            ),
            None,
        )
        if periods and active_period is None:
            continue

        routes = sorted(
            {item.route_id for item in alert.informed_entity if item.route_id}
        )
        stop_ids = sorted(
            {item.stop_id for item in alert.informed_entity if item.stop_id}
        )
        title = _text(alert.header_text)
        if not title:
            continue
        effect = gtfs_realtime_pb2.Alert.Effect.Name(alert.effect)
        parsed.append(
            MTAAlert(
                id=entity.id,
                title=title,
                description=_text(alert.description_text),
                routes=tuple(routes),
                stop_ids=tuple(stop_ids),
                effect=effect,
                starts_at=_as_datetime(active_period.start) if active_period else None,
                ends_at=_as_datetime(active_period.end) if active_period else None,
            )
        )
    return parsed
