---
name: deployment
description: Deploy applications (cloud, serverless, on-prem). TRIGGER when the user asks to deploy an application, set up hosting, configure a server, deploy to AWS/GCP/Vercel/Fly.io, or go to production.
---
# Deployment

Deploy applications to various hosting platforms with proper configuration and best practices.

## Steps

1. **Assess the application** - Determine the type (static site, API server, full-stack, worker) and requirements (database, storage, env vars).
2. **Choose the platform** - Match the deployment target to the application needs.
3. **Prepare the application** - Create build scripts, environment config, and health checks.
4. **Configure the platform** - Set up the hosting configuration file.
5. **Deploy** - Execute the deployment and verify it works.
6. **Set up monitoring** - Ensure health checks, logging, and alerts are in place.

## Platform Selection Guide

| App Type | Recommended Platforms |
|----------|----------------------|
| Static site / SPA | Vercel, Netlify, Cloudflare Pages, S3+CloudFront |
| Node.js / Python API | Fly.io, Railway, Render, AWS ECS, GCP Cloud Run |
| Full-stack (Next.js) | Vercel, Fly.io, AWS Amplify |
| Serverless functions | AWS Lambda, Vercel Functions, Cloudflare Workers |
| Containers | Fly.io, AWS ECS/Fargate, GCP Cloud Run, Kubernetes |
| Databases | Neon (Postgres), PlanetScale (MySQL), Supabase, AWS RDS |

## Vercel

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "nextjs",
  "env": {
    "DATABASE_URL": "@database-url"
  },
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "no-store" }
      ]
    }
  ]
}
```

```bash
# Deploy
npx vercel --prod

# Set environment variables
npx vercel env add DATABASE_URL production
```

## Fly.io

```toml
# fly.toml
app = "my-app"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[env]
  NODE_ENV = "production"
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1

  [http_service.concurrency]
    type = "requests"
    hard_limit = 250
    soft_limit = 200

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512

[checks]
  [checks.health]
    type = "http"
    port = 8080
    path = "/health"
    interval = "10s"
    timeout = "2s"
```

```bash
# Deploy
fly launch
fly deploy

# Set secrets
fly secrets set DATABASE_URL="postgres://..."
fly secrets set JWT_SECRET="..."

# Scale
fly scale count 2
fly scale vm shared-cpu-2x

# View logs
fly logs

# SSH into the machine
fly ssh console
```

## AWS (CDK / CloudFormation)

### Fargate Service
```typescript
// cdk/lib/stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';

export class AppStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string) {
    super(scope, id);

    const service = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'Service', {
      taskImageOptions: {
        image: ecs.ContainerImage.fromAsset('.'),
        containerPort: 8080,
        environment: {
          NODE_ENV: 'production',
        },
      },
      desiredCount: 2,
      cpu: 256,
      memoryLimitMiB: 512,
      publicLoadBalancer: true,
    });

    service.targetGroup.configureHealthCheck({
      path: '/health',
      healthyHttpCodes: '200',
    });
  }
}
```

## Docker-based Deployment

### docker-compose.prod.yml
```yaml
services:
  app:
    image: myapp:latest
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app
    restart: unless-stopped
```

## Pre-Deployment Checklist

```bash
#!/bin/bash
# deploy-check.sh

echo "=== Pre-deployment Checklist ==="

# 1. Tests pass
echo "Running tests..."
npm test || { echo "FAIL: Tests failed"; exit 1; }

# 2. Build succeeds
echo "Building..."
npm run build || { echo "FAIL: Build failed"; exit 1; }

# 3. No secrets in code
echo "Checking for secrets..."
if grep -rn "password\s*=\s*['\"]" src/ --include="*.ts"; then
  echo "WARN: Possible hardcoded secrets found"
fi

# 4. Environment variables documented
echo "Required env vars:"
grep -rh "process.env\.\w\+" src/ | sort -u

# 5. Health check works
echo "Checking health endpoint..."
curl -sf http://localhost:8080/health || echo "WARN: Health check not responding"

echo "=== Checklist Complete ==="
```

## Environment Configuration

```bash
# .env.example (commit this, NOT .env)
DATABASE_URL=postgres://user:pass@localhost:5432/myapp
REDIS_URL=redis://localhost:6379
JWT_SECRET=change-me-in-production
LOG_LEVEL=info
PORT=8080
```

## Rules

- NEVER commit secrets, credentials, or `.env` files to the repository
- Always use environment variables for configuration that varies between environments
- Set up health checks so the platform can detect and replace unhealthy instances
- Use HTTPS in production -- configure TLS/SSL certificates
- Enable automated deployments from the main branch after CI passes
- Always have a rollback strategy (keep previous versions, use blue-green or canary deployments)
- Test the production build locally before deploying
- Set resource limits (memory, CPU) to prevent runaway processes
- Configure logging to an external service (not just stdout) for production
- Set up monitoring and alerting before launch, not after the first outage
