from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routers.agents import router as agents_router
from app.api.v1.routers.metrics import router as metrics_router

app = FastAPI(title="Agent Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)
app.include_router(agents_router)
app.include_router(metrics_router)
