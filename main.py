from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import auth, dashboard

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dashboard API", version="1.0.0")

# CORS — allow your HTML frontend to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL in production e.g. ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(dashboard.router)

@app.get("/")
def root():
    return {"message": "Dashboard API is running"}