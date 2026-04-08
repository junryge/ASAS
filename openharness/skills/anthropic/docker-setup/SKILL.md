---
name: docker-setup
description: Create Dockerfiles, docker-compose, and container configurations. TRIGGER when the user asks to containerize an application, create a Dockerfile, set up docker-compose, or configure Docker.
---
# Docker Setup

Create optimized Dockerfiles, docker-compose configurations, and container setups for applications.

## Steps

1. **Identify the application stack** - Determine the language, framework, and dependencies (Node.js, Python, Go, etc.).
2. **Create the Dockerfile** - Write a multi-stage, production-optimized Dockerfile.
3. **Create .dockerignore** - Exclude unnecessary files from the build context.
4. **Set up docker-compose** - Define services, networks, and volumes for local development.
5. **Test the build** - Build and run the container to verify it works.

## Dockerfile Examples

### Node.js (Multi-stage)
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/index.js"]
```

### Python (Multi-stage)
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt -o requirements.txt --without-hashes
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home appuser
COPY --from=builder /install /usr/local
COPY . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### Go
```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

## Docker Compose

### Full-stack development setup
```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder  # Use build stage for development
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules  # Preserve container's node_modules
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgres://postgres:postgres@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    command: npm run dev

  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

## .dockerignore
```
node_modules
.git
.gitignore
.env
.env.*
*.md
dist
coverage
.vscode
.idea
__pycache__
*.pyc
.pytest_cache
```

## Common Commands
```bash
# Build
docker build -t myapp .
docker compose build

# Run
docker compose up -d
docker compose logs -f app

# Shell into a running container
docker compose exec app sh

# Rebuild after dependency changes
docker compose up -d --build

# Clean up
docker compose down -v  # -v removes volumes too
docker system prune -f
```

## Rules

- Use multi-stage builds to minimize production image size
- Never hardcode secrets in Dockerfiles -- use environment variables or Docker secrets
- Run containers as a non-root user
- Pin base image versions (use `node:20-alpine`, not `node:latest`)
- Add `.dockerignore` to exclude unnecessary files and speed up builds
- Include HEALTHCHECK instructions for production containers
- Use COPY instead of ADD unless you specifically need tar extraction or URL download
- Order Dockerfile instructions from least to most frequently changed (for layer caching)
- Copy dependency files first, install deps, then copy source code
