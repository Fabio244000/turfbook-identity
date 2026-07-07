# TurfBook — Identity

Identity microservice for TurfBook, a synthetic grass court booking platform.
Handles user registration and authentication. Built with FastAPI following
hexagonal architecture, designed to run serverless on AWS Lambda.

## Exposed API

| Method | Endpoint     | Description                                  |
|--------|--------------|----------------------------------------------|
| POST   | `/users`     | Register a new user (player or owner)        |

## Tech stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy + Alembic
- Docker / Docker Compose

## Getting started

### 1. Create the virtual environment

```bash
conda create -n turfbook-identity-env python=3.12
conda activate turfbook-identity-env
pip install -r requirements/local.txt
```

### 2. Set environment variables

Copy the example file and adjust if needed:

```bash
cp .env.example .env
```

### 3. Run with Docker Compose

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

## Development

Run code quality checks:

```bash
pre-commit run --all-files
```
