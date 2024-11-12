# PDF Co-Viewer Web App

This web application allows multiple users to synchronize their view of a PDF. An admin can control which page is displayed, and all other viewers in the room will have their view updated to match the current page set by the admin. The app uses **FastAPI** for the backend and **Streamlit** for the frontend.

## Features
- Upload a PDF file.
- Synchronize page view between multiple users.
- Admin controls to change pages and broadcast updates to all users in the room.
- Real-time viewer count updates.

## Project Structure
- **Backend**: FastAPI handles the WebSocket connections, room management, and PDF file uploads.
- **Frontend**: Streamlit provides an easy-to-use interface for uploading PDFs and viewing synchronized pages.

## Requirements

Ensure you have the following dependencies installed. You can install them by running the command:

```bash
pip install -r requirements.txt

## How to Use

### 1. Start the Backend Server
First, ensure the FastAPI backend is running. Use the following command in your terminal:

```bash
uvicorn main:app --reload --port 8000

### 2. Start the Frontend Server
```bash
streamlit run app.py
