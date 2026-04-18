from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.firebase import verify_firebase_token
from app.schemas.user import UserCreate, UserResponse
from app.services import auth_service
from app.models.user import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    decoded = verify_firebase_token(credentials.credentials)
    data = UserCreate(
        firebase_uid=decoded["uid"],
        email=decoded.get("email", ""),
        name=decoded.get("name"),
    )
    user = await auth_service.create_user(db, data)
    return user


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
