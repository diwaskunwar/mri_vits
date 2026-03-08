# 🧠 Candor Dust - Brain Tumor Detection AI

> An end-to-end medical imaging classification system designed to detect and categorize brain tumors from MRI/CT scans.

## 🌟 Project Overview

Candor Dust is a trustworthy AI prototype that assists healthcare professionals in analyzing medical imagery. The system prioritizes clinical safety by implementing confidence-based workflows, ensuring that low-confidence AI predictions are marked for human review.

## 👥 Essential Functionalities

- **Role-Based Access Control**: Tailored dashboards and permissions for **Administrators**, **Doctors**, and **Patients**.
- **Automated Prediction Pipeline**: High-speed classification of brain scans into Glioma, Meningioma, Pituitary, or No Tumor categories.
- **Trust-First Design**: Integrated confidence scoring and review workflows to ensure AI reliability in a medical context.
- **Patient Management**: Centralized records for tracking scan history and health performance over time.

## 🛠️ Technology Stack

The project utilizes a modern, scalable tech stack to handle both data management and heavy AI processing:

### Backend & Core
- **FastAPI**: A high-performance Python framework for building robust APIs.
- **Ray Serve**: Used for scaling ML inference across multi-GPU environments.
- **SQLAlchemy & Pydantic**: For secure data modeling and validation.

### Frontend
- **React & TypeScript**: A type-safe, component-based user interface.
- **Redux Toolkit**: Centralized state management for authentication and global application logic.
- **Tailwind CSS & Lucide React**: Premium, responsive UI design and iconography.

### Artificial Intelligence
- **VGG19 (Transfer Learning)**: A deep convolutional neural network pre-trained on ImageNet and fine-tuned for specialized brain tumor detection.
- **TensorFlow/Keras**: The underlying engine for training and executing model inference.

## 📂 Project Structure

For detailed system overviews of each component, please refer to their respective documentation:

- **[Backend Service](./backend/README.md)**: FastAPI, Multi-GPU Scaling, and API documentation.
- **[Frontend Interface](./frontend/README.md)**: React Dashboard, User Roles, and UI Design.
- **[AI Model](./model/README.md)**: VGG19 Architecture, Transfer Learning, and Inference Pipeline.

## ⚠️ Important Disclaimer

**This project is a research prototype only.** 
It is not a certified medical device and is not approved for clinical use. All outputs should be reviewed by qualified medical professionals.

---
*Candor Dust - Empowering healthcare with trustworthy AI.*
