# AegisDesk Docker Deployment

AegisDesk is containerized as two services:

- `backend`: FastAPI + RAG/LLM/Policy Engine on port 8000
- `frontend`: React/Vite production build served by Nginx on port 3000
- MongoDB remains MongoDB Atlas; Docker does not create or reset a local database.

## 1. Copy project files

From the AegisDesk project root, place:

- `backend/Dockerfile`
- `backend/requirements-docker.txt`
- `frontend/Dockerfile`
- `frontend/nginx/default.conf`
- `docker-compose.yml`
- `.dockerignore`

## 2. Environment

Create a root `.env` file from `.env.docker.example` and fill in the existing MongoDB Atlas URI.

Do not commit `.env`.

## 3. Build and start

```powershell
docker compose build
docker compose up -d
```

Check:

```powershell
docker compose ps
docker compose logs backend --tail 100
docker compose logs frontend --tail 50
```

Open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

## 4. Stop

```powershell
docker compose down
```

This does not delete MongoDB Atlas data. The Hugging Face cache volume remains unless explicitly removed.

## 5. Rebuild after code changes

```powershell
docker compose up -d --build
```
