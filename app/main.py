from fastapi import FastAPI
from app.api.v1.routers.agents import router as agents_router

app = FastAPI(title="Agent Service", version="1.0.0")
app.include_router(agents_router)
