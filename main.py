from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from routes import auth, dashboard
from routes.stock_routes import router as stock_router 

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dashboard API", version="1.0.0")

# CORS — allow your HTML frontend to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(stock_router) 

@app.get("/")
def root():
    return {"message": "Dashboard API is running"}