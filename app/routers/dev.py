from fastapi import APIRouter, HTTPException
from firebase_admin import auth
from app.core.config import settings

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/custom-token")
async def get_custom_token(uid: str = "dev-user-1"):
    if settings.ENVIRONMENT != "dev":
        raise HTTPException(status_code=404, detail="Not found")
    token = auth.create_custom_token(uid)
    return {"custom_token": token.decode("utf-8"), "uid": uid}
