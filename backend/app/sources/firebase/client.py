import asyncio
import hashlib
import threading
from datetime import UTC, datetime, timedelta

import firebase_admin
from firebase_admin import auth, credentials, firestore, messaging
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError
from google.cloud.firestore_v1.base_query import FieldFilter

from backend.app.config import Settings
from backend.app.core.errors import APIError


class FirebaseClient:
    def __init__(self, settings: Settings):
        """Store the dependencies and initialize the state required by this component."""
        self.settings = settings
        self._app = None
        self._db = None
        self._lock = threading.Lock()

    def get_app(self):
        """Lazily initialize the configured Firebase Admin application."""
        if not self.settings.firebase_project_id:
            raise APIError(
                503,
                "Firebase is not configured. Set FIREBASE_PROJECT_ID and application credentials.",
            )
        with self._lock:
            if self._app is None:
                try:
                    credential = (
                        credentials.Certificate(self.settings.firebase_credentials)
                        if self.settings.firebase_credentials
                        else credentials.ApplicationDefault()
                    )
                    name = (
                        "nyc-transit-"
                        + hashlib.sha256(
                            self.settings.firebase_project_id.encode()
                        ).hexdigest()[:12]
                    )
                    try:
                        self._app = firebase_admin.get_app(name)
                    except ValueError:
                        self._app = firebase_admin.initialize_app(
                            credential,
                            {"projectId": self.settings.firebase_project_id},
                            name=name,
                        )
                except (ValueError, OSError, GoogleAuthError) as exc:
                    raise APIError(
                        503, "Firebase credentials could not be loaded."
                    ) from exc
        return self._app

    def get_database(self):
        """Lazily obtain the configured Firestore client."""
        if self._db is None:
            try:
                self._db = firestore.client(app=self.get_app())
            except (ValueError, GoogleAuthError) as exc:
                raise APIError(503, "Firestore credentials are not available.") from exc
        return self._db

    async def verify_token(self, token: str) -> str:
        """Verify Firebase token signatures, expiry and revocation before returning the user ID."""
        try:
            decoded = await asyncio.to_thread(
                auth.verify_id_token, token, app=self.get_app(), check_revoked=True
            )
        except auth.CertificateFetchError as exc:
            raise APIError(
                503, "Firebase token verification is temporarily unavailable."
            ) from exc
        except (
            auth.InvalidIdTokenError,
            auth.UserDisabledError,
            auth.UserNotFoundError,
            ValueError,
        ) as exc:
            raise APIError(401, "Invalid or expired Firebase ID token.") from exc
        except (GoogleAuthError, firebase_admin.exceptions.FirebaseError) as exc:
            raise APIError(
                503, "Firebase authentication is temporarily unavailable."
            ) from exc
        uid = decoded.get("uid")
        if not isinstance(uid, str) or not uid:
            raise APIError(401, "The Firebase token has no valid user ID.")
        return uid

    async def _run(self, operation):
        """Run synchronous Firebase data access off the event loop and normalize provider failures."""
        try:
            return await asyncio.to_thread(operation)
        except (GoogleAPICallError, GoogleAuthError) as exc:
            raise APIError(503, "Firestore is temporarily unavailable.") from exc

    async def list_docs(
        self, collection: str, filters: list[tuple] | None = None
    ) -> list[dict]:
        """Read Firestore documents matching the repository-supplied filters."""

        def operation():
            """Execute the synchronous Firestore operation in the worker thread."""
            query = self.get_database().collection(collection)
            for field, operator, value in filters or []:
                query = query.where(filter=FieldFilter(field, operator, value))
            return [
                dict(doc.to_dict(), _id=doc.id)
                for doc in query.stream(timeout=15, retry=None)
            ]

        return await self._run(operation)

    async def get_doc(self, collection: str, key: str) -> dict | None:
        """Read one Firestore document or return None when it does not exist."""

        def operation():
            """Execute the synchronous Firestore operation in the worker thread."""
            doc = (
                self.get_database()
                .collection(collection)
                .document(key)
                .get(timeout=15, retry=None)
            )
            return doc.to_dict() if doc.exists else None

        return await self._run(operation)

    async def set_doc(self, collection: str, key: str, data: dict) -> None:
        """Idempotently write a complete Firestore document with a bounded request timeout."""
        await self._run(
            lambda: self.get_database()
            .collection(collection)
            .document(key)
            .set(data, timeout=15, retry=None)
        )

    async def delete_doc(self, collection: str, key: str) -> None:
        """Idempotently delete a Firestore document with a bounded request timeout."""
        await self._run(
            lambda: self.get_database()
            .collection(collection)
            .document(key)
            .delete(timeout=15, retry=None)
        )

    async def claim_delivery(self, key: str) -> bool:
        """Acquire a delivery lease transactionally unless the event was already sent or claimed."""

        def operation():
            """Execute the synchronous Firestore operation in the worker thread."""
            db = self.get_database()
            ref = db.collection("transit_deliveries").document(key)

            @firestore.transactional
            def claim(transaction):
                """Transactionally claim an unsent event using a time-limited lease."""
                snapshot = ref.get(transaction=transaction)
                data = snapshot.to_dict() or {}
                now = datetime.now(UTC)
                if data.get("sent") or data.get("lease_until", now) > now:
                    return False
                transaction.set(
                    ref,
                    {
                        "sent": False,
                        "lease_until": now + timedelta(minutes=2),
                        "expires_at": now + timedelta(days=7),
                    },
                )
                return True

            return claim(db.transaction())

        return await self._run(operation)

    async def finish_delivery(self, key: str, sent: bool) -> None:
        """Persist a delivery outcome and release its retry lease."""
        await self.set_doc(
            "transit_deliveries",
            key,
            {
                "sent": sent,
                "lease_until": datetime.now(UTC),
                "expires_at": datetime.now(UTC) + timedelta(days=7),
            },
        )

    async def send_notification(
        self, token: str, title: str, body: str, data: dict[str, str]
    ) -> bool:
        """Send an FCM notification and discard registrations reported as invalid."""
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title[:120], body=body[:1000]),
            data=data,
        )
        try:
            await asyncio.to_thread(messaging.send, message, app=self.get_app())
        except messaging.UnregisteredError:
            await self.delete_doc(
                "transit_devices", hashlib.sha256(token.encode()).hexdigest()
            )
            return False
        except firebase_admin.exceptions.FirebaseError as exc:
            raise APIError(503, "Firebase notification delivery failed.") from exc
        return True

    async def delete_device_for_user(self, user_id: str, token: str) -> None:
        # Do not reveal whether a different user owns the same registration token.
        """Transactionally remove a device only when the stored owner matches the verified user."""
        key = hashlib.sha256(token.encode()).hexdigest()

        def operation():
            """Execute the synchronous Firestore operation in the worker thread."""
            from firebase_admin import firestore

            db = self.get_database()
            ref = db.collection("transit_devices").document(key)

            @firestore.transactional
            def remove(transaction):
                """Transactionally delete a device registration only for its matching owner."""
                row = ref.get(transaction=transaction).to_dict() or {}
                if row.get("user_id") == user_id:
                    transaction.delete(ref)

            remove(db.transaction())

        await self._run(operation)
