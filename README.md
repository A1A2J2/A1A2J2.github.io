# LLM Chatbot SaaS

A full-stack, web-based SaaS chatbot platform where users can chat with multiple open-source LLM models (Llama 7B, Qwen2 7B, 14B, 32B) powered by Ollama.

## Features

*   **Multi-Model Support:** Chat with Llama 2 (7B, 14B, 32B) and Qwen2 (7B), configurable via Ollama.
*   **Authentication:** 
    *   Traditional Username & Password (JWT-based).
    *   **Passwordless Passkeys (WebAuthn)** for highly secure, frictionless logins using device biometrics (Face ID, Touch ID, Windows Hello).
*   **Usage Tracking & Tiers:** 
    *   Tracks monthly token usage per model group.
    *   Supports Free and Paid subscription tiers with rate-limiting.
*   **Conversation History:** Threaded chat management with a sidebar to navigate past conversations.
*   **Modern UI:** Responsive, vanilla HTML/CSS/JS frontend with real-time token tracking.

## Architecture

*   **Backend:** Python 3, FastAPI, SQLAlchemy
*   **Frontend:** Vanilla JavaScript, HTML5, CSS3
*   **Database:** SQLite
*   **AI Engine:** Ollama API

## Setup Instructions

### Prerequisites

1.  **Python 3.10+** installed.
2.  **Ollama** installed and running on your machine (`ollama serve`).

### 1. Model Preparation

Pull the required models into your local Ollama instance:

```bash
ollama pull llama2:7b
ollama pull qwen2:7b
ollama pull llama2:14b
ollama pull llama2:32b
```

### 2. Backend Setup

Navigate to the backend directory and install dependencies:

```bash
cd chatbot-backend
python3 -m pip install -r requirements.txt
python3 -m pip install webauthn # For Passkeys
```

*(Note: It is highly recommended to use a virtual environment `python3 -m venv venv`)*

### 3. Running the Server

Start the FastAPI application:

```bash
cd chatbot-backend
uvicorn main:app --reload
```

The application will start on `http://127.0.0.1:8000`.

### 4. Accessing the App

Open your browser and navigate to `http://localhost:8000`. You will be greeted by the login screen where you can sign up using a password or a Passkey.

## Project Structure

*   `chatbot-backend/main.py`: Application entry point.
*   `chatbot-backend/routes/`: FastAPI routers for `/auth`, `/chat`, `/usage`, and `/webauthn`.
*   `chatbot-backend/frontend/`: Static HTML, CSS, and JS files served by FastAPI.
*   `chatbot-backend/database.py`: SQLite SQLAlchemy models and connection setup.

## Next Steps / Roadmap

*   Stripe Integration for Paid Tiers (Spec defined).
*   Password Reset Flow.
*   Email Service Integration for notifications.