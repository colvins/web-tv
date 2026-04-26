# web-tv

Production skeleton for a Web TV application.

## Stack

- Backend: FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Redis, Pydantic Settings
- Frontend: Vue 3, Vite, TypeScript, Tailwind CSS, Naive UI, Pinia, Vue Router, hls.js
- Runtime: Docker Compose with Nginx on host port `8080`

## Structure

```text
backend/app/
  api/v1/
  core/
  db/models/
  schemas/
  services/
  utils/
  workers/
frontend/
nginx/
```

## Run

```bash
cp .env.example .env
docker compose up -d --build
```

Open the app at `http://localhost:8080`.

Health check:

```bash
curl http://localhost:8080/api/v1/health
```

## Development Checks

```bash
cd frontend && npm run build
docker compose config
docker compose up -d --build
```
