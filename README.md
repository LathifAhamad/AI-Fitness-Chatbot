# FitBot AI

An intelligent fitness chatbot built with FastAPI and a static frontend. It serves a workout and nutrition assistant UI from `static/index.html` and provides backend chatbot endpoints from `app.py`.

## Features

- FastAPI backend
- Static frontend UI
- Chat-based fitness guidance
- CORS enabled
- Easy local setup
- Deployable with `uvicorn`

## Project Structure

- `app.py` — FastAPI application entrypoint
- `static/` — frontend files
  - `index.html`
  - `login.html`
  - `styles.css`
  - `app.js`
  - `particles.js`
  - `cursor.js`
- `requirements.txt` — Python dependencies
- `Procfile` / `render.yaml` / `DEPLOY.md` — deployment support files

## Prerequisites

- Python 3.10+
- Git

## Local Setup

```bash
cd "AI FITNESS CHATBOT/AI FITNESS CHATBOT"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
