# ⚙️ Candor Dust - Backend API & System Design

The **Candor Dust Backend** is the industrial core of the system. Built with **FastAPI**, it provides a secure, auditable gateway between clinical users and the AI inference engine.

---

## 🏗️ System Design & Architecture

The backend follows a modular monolith architecture, designed for reliability and future scalability.

### Core Modules
- **`models.py`**: Relational data schema (Users, Scans, AuditLogs, Invitations) using SQLAlchemy.
- **`auth.py`**: JWT-based security with fine-grained RBAC (Admin, Doctor, Patient).
- **`task_queue.py`**: An asynchronous, in-process task scheduler that manages the scan lifecycle (Pending -> Processing -> Completed).
- **`model_client.py`**: A dedicated client wrapper that handles HTTP communication, retries, and data formatting for the Ray Serve model service.

### The Scan Lifecycle
1. **Upload**: Doctor uploads an MRI via `POST /api/predict`.
2. **Persistence**: The raw image is saved as a secure Blob in the database; a `Scan` record is created with `status="PENDING"`.
3. **Queueing**: The scan ID is pushed to the internal `prediction_queue`.
4. **Inference**: A background worker picks up the task, calls the Model Service, and receives predictions + Grad-CAM data.
5. **Finalization**: The database is updated with results, and a notification is pushed via **WebSockets**.

---

## 🔒 Security & RBAC

| Role | Permissions |
|------|-------------|
| **Admin** | Full system control, user creation/deletion, view all audit logs. |
| **Doctor** | Upload scans, review predictions, manage patients, view statistics. |
| **Patient** | View personal scan history and validated results. |

- **Authentication**: JWT (JSON Web Tokens) with 30-minute expiration.
- **Passwords**: Hashed using `bcrypt`.
- **Authorization**: Role-based dependency injection in FastAPI routes.

---

## 📜 Audit Logging & Traceability

Trust is built on accountability. Every significant action is recorded in the `audit_logs` table:
- User ID of the actor.
- Action type (e.g., `scan_queued`, `review_completed`, `user_deleted`).
- Timestamp & IP Address.
- Metadata (Scan IDs, previous status, etc.).

---

## 🔌 API Specifications (Summary)

### Scans & Predictions
- `GET /scans`: Retrieve scan history (filtered by role).
- `GET /scans/{id}`: Full detail including Grad-CAM and inputs.
- `POST /predict`: Unified upload and inference entry point.
- `POST /scans/{id}/review`: Submit clinical review and notes.

### Patients & Users
- `GET /patients`: Summary of all patients with scan counts and last activity.
- `POST /register`: Onboard new users.
- `DELETE /users/{id}`: Managed deletion with cascade removal of associated health data.

---

## 🛠️ Performance & Scalability
- **Asynchronicity**: Fully leverages Python's `async/await` for high-throughput I/O.
- **Streaming Image Handling**: Images are processed as binary streams to minimize memory footprint.
- **Ray Integration**: Offloading heavy computation (ViT inference) to a separate Ray-managed service allows the API to remain responsive under heavy load.

---
*For model-specific details, see [model/README.md](../model/README.md).*
