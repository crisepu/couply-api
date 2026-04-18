from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.firebase import init_firebase
from app.routers import auth, couple, expenses, balance
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield


app = FastAPI(title="Couply API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(couple.router)
app.include_router(expenses.router)
app.include_router(balance.router)

if settings.ENVIRONMENT == "dev":
    from app.routers import dev
    app.include_router(dev.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
