from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.database import engine, Base, SessionLocal
from src.v1.routes import users, scans, audit, invitations, images, ws
from src import model_client
from src.models import User, Scan, AuditLog, Invitation
from src.auth import get_password_hash
from datetime import datetime


def create_default_users():
    """Create default users if they don't exist"""
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@candordust.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                role="admin",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(admin)
            db.commit()
            print("Created default admin user: admin / admin123")
        
        # Create a test doctor user
        doctor = db.query(User).filter(User.username == "doctor").first()
        if not doctor:
            doctor = User(
                username="doctor",
                email="doctor@candordust.com",
                hashed_password=get_password_hash("doctor123"),
                full_name="Dr. Doctor",
                role="doctor",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(doctor)
            db.commit()
            print("Created doctor user: doctor / doctor123")
            
        # Create a test patient user
        patient = db.query(User).filter(User.username == "patient").first()
        if not patient:
            patient = User(
                username="patient",
                email="patient@candordust.com",
                hashed_password=get_password_hash("patient123"),
                full_name="Test Patient",
                role="patient",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(patient)
            db.commit()
            print("Created patient user: patient / patient123")
            
    except Exception as e:
        print(f"Error creating default users: {e}")
        db.rollback()
    finally:
        db.close()


import asyncio
from src.task_queue import process_prediction_queue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    create_default_users()
    print(f"Model service URL: {settings.MODEL_SERVICE_URL}")
    
    # Start background workers for the queue
    num_workers = 3
    app.state.queue_workers = []
    for _ in range(num_workers):
        task = asyncio.create_task(process_prediction_queue())
        app.state.queue_workers.append(task)
        
    yield
    # Shutdown
    for task in app.state.queue_workers:
        task.cancel()
    
    # Wait for tasks to finish cancelling
    await asyncio.gather(*app.state.queue_workers, return_exceptions=True)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Candor Dust - Brain Tumor Detection API",
        description="API for brain tumor detection",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(users.router, prefix="/api", tags=["Authentication"])
    app.include_router(scans.router, prefix="/api", tags=["Scans"])
    app.include_router(audit.router, prefix="/api", tags=["Audit Logs"])
    app.include_router(invitations.router, prefix="/api", tags=["Invitations"])
    app.include_router(images.router, prefix="/api", tags=["Images"])
    app.include_router(ws.router, prefix="/api/ws", tags=["WebSockets"])

    @app.get("/")
    async def root():
        return {"message": "Candor Dust API", "status": "running"}

    @app.get("/api/health")
    async def health_check():
        model_health = await model_client.health_check()
        return {
            "status": "healthy",
            "database": "connected",
            "model_service": model_health,
        }
    
    return app


app = create_app()

