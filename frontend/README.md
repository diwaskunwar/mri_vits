# Candor Dust - Frontend Interface

## 🏛️ System Overview

The **Candor Dust Frontend** is a professional, clinical-grade Single Page Application (SPA). It is designed to provide doctors and administrators with a high-trust interface for AI-assisted brain tumor diagnosis.

### Key Features
- **Dynamic Clinical Dashboards**:
  - **Administrator**: Real-time aggregation of system health, processing metrics, and user activity.
  - **Practitioner (Doctor)**: Streamlined patient management list with quick-upload capabilities and history tracking.
  - **Patient**: Simplified view focusing on their own scan journey and final validated reports.
- **AI Feedback Visualization**:
  - **Confidence Badging**: Visual indicators (Green/Yellow/Red) derived from the model's self-assessment.
  - **Status Synchronization**: Real-time processing feedback via WebSockets (Pending → Processing → Completed).
- **Interactive Scan Detail**:
  - Side-by-side comparison of original MRI scans and AI classification data.
  - Interactive "Human Review" workflow for clinicians to overwrite or validate low-confidence AI predictions.
- **Premium UX**: A "glassmorphism" based clean medical aesthetic using modern typography and high-contrast accessibility standards.

## 🛠️ Configuration (.env)

The frontend requires the following environment variables in a `.env` file within the `frontend/` directory:

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | The public URL of the backend API. | `http://localhost:8000` |

*Note: In Vite, all variables must be prefixed with `VITE_` to be bundled into the client-side code.*

## 🚀 Deployment & Local Run

### Local Development (using `npm`)
1. **Install Dependencies**:
   ```bash
   npm install
   ```
2. **Launch Dev Server**:
   ```bash
   npm run dev
   ```
   *The app will usually reside at http://localhost:3000.*

### Production Build
1. **Compile**:
   ```bash
   npm run build
   ```
2. **Serve Built Assets**:
   Use a static file server like Nginx or use the internal preview:
   ```bash
   npm run preview
   ```

## 🔌 Technical Layer
- **Core Framework**: **React 18** with **TypeScript**.
- **State Engine**: **Redux Toolkit** managing global authentication, user roles, and scan snapshots.
- **Styling**: **Tailwind CSS** with a custom clinical color palette.
- **Icons**: **Lucide React**.

---
*For the backend logic, see the [backend/README.md](../backend/README.md).*
