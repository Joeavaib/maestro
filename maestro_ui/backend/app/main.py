from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .api import projects, pipeline

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Maestro WebUI API")

# Configure CORS for the React frontend (HTTP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In FastAPI, CORSMiddleware doesn't always automatically apply to WebSockets
# depending on how they are routed. But usually it's handled. The 403 error 
# often happens if we didn't specify origins in the websocket accept method, 
# or if it's missing in the main app. We will just ensure our CORS is set up.

app.include_router(projects.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "system": "Maestro Core"}
