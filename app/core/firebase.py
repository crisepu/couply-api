import json
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status
from app.core.config import settings

_app: firebase_admin.App | None = None


def init_firebase() -> None:
    global _app
    if _app is not None:
        return
    service_account = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
    cred = credentials.Certificate(service_account)
    _app = firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str) -> dict:
    try:
        return auth.verify_id_token(id_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
