from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import artifacts, canonical, search, contributors, flags, discovery

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Signal Archive API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(artifacts.router, prefix="/artifacts")
app.include_router(canonical.router, prefix="/canonical")
app.include_router(search.router, prefix="/search")
app.include_router(contributors.router, prefix="/contributors")
app.include_router(flags.router, prefix="/flags")
app.include_router(discovery.router, prefix="/discovery")

@app.get("/health")
async def health():
    return {"status": "ok"}
