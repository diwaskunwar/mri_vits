# Candor Dust - Backend Service

## 🏛️ System Overview

The **Candor Dust Backend** is a high-performance REST API built with **FastAPI**. it serves as the central orchestrator for the clinical workflow, managing security, data persistence, and AI model communication.

### Core Features
- **Advanced RBAC (Role-Based Access Control)**: 
  - **Admin**: System-wide oversight, user management, and detailed audit logs.
  - **Doctor**: Management of assigned patients and initiation of scan predictions.
  - **Patient**: Secure access to personal scan history and results.
- **AI Orchestration Pipeline**: 
  - Handles image upload and asynchronous prediction queuing.
  - Communicates with the ViT model service via a localized client.
  - Implements a tiered confidence policy (Low confidence triggers mandatory human review).
- **Audit Logging**: Every sensitive action (logins, deletions, diagnosis changes) is recorded in a tamper-resistant audit trail.
- **Real-time Synchronization**: Uses **WebSockets** to push scan processing updates (status changes, completion) directly to the frontend.
- **Background Processing**: Implements an internal task queue to handle CPU/GPU intensive inference without blocking the main event loop.

## 🛠️ Configuration (.env)

The backend expects a `.env` file in the `backend/` directory with the following keys:

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `DATABASE_URL` | The SQLAlchemy connection string. | `sqlite:///./candor_dust.db` |
| `SECRET_KEY` | A long random string used for JWT signature. | *REQUIRED* |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity period. | `30` |
| `MODEL_SERVICE_URL` | Endpoint of the running Model Service. | `http://localhost:8001/predict` |
| `WS_NOTIFICATION_RETRY` | Number of retries for WebSocket messages. | `3` |

## 🚀 Deployment & Local Run

### Local Development (using `uv`)
We use **uv** for blazing-fast dependency management and environment isolation.

1. **Setup Environment**:
   ```bash
   uv sync
   ```
2. **Launch API Server**:
   ```bash
   uv run fastapi dev src/main.py --reload
   ```
   *The server will be available at http://localhost:8000. Interactive docs at /docs.*

### Using Docker
The backend is containerized for seamless deployment.

1. **Build**:
   ```bash
   docker build -t candor-backend ./backend
   ```
2. **Run**:
   ```bash
   docker run -d -p 8000:8000 --env-file ./backend/.env candor-backend
   ```

## 🔌 Technical Layer
- **ORM**: SQLAlchemy with Pydantic for data validation.
- **Inference Client**: A dedicated `model_client.py` handles communication with the Ray-served ViT model.
- **Security**: Passlib with Bcrypt for secure password hashing.

---
*For the frontend interface, see the [frontend/README.md](../frontend/README.md).*
