---
name: ci-cd
description: Set up CI/CD pipelines (GitHub Actions, GitLab CI). TRIGGER when the user asks to set up continuous integration, continuous deployment, create a CI pipeline, configure GitHub Actions, or automate builds and deployments.
---
# CI/CD

Set up continuous integration and continuous deployment pipelines.

## Steps

1. **Identify the platform** - Determine which CI/CD platform to use: GitHub Actions, GitLab CI, CircleCI, or others based on the repository host.
2. **Define the pipeline stages** - Typical stages: lint, test, build, deploy.
3. **Create the config file** - Write the pipeline configuration with appropriate triggers, caching, and parallelization.
4. **Add secrets** - Identify required secrets (API keys, deploy tokens) and instruct the user how to add them.
5. **Test the pipeline** - Push the config and verify the pipeline runs successfully.

## GitHub Actions

### Basic CI Pipeline
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
```

### Deploy Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - name: Deploy to production
        run: |
          # Example: deploy to AWS
          aws s3 sync dist/ s3://${{ secrets.S3_BUCKET }}
          aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DISTRIBUTION_ID }} --paths "/*"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
```

### Python CI
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest --cov --cov-report=xml
```

## GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  NODE_ENV: test

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/

lint:
  stage: lint
  image: node:20-alpine
  script:
    - npm ci
    - npm run lint

test:
  stage: test
  image: node:20-alpine
  services:
    - postgres:16
  variables:
    POSTGRES_DB: test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgres://postgres:postgres@postgres:5432/test
  script:
    - npm ci
    - npm test -- --coverage

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy:
  stage: deploy
  only:
    - main
  environment:
    name: production
  script:
    - echo "Deploy to production"
```

## Pipeline Best Practices

### Caching
- Cache dependency directories (`node_modules`, `.pip`, `.cargo`)
- Use hash-based cache keys (`hashFiles('**/package-lock.json')`)

### Parallelization
- Run independent jobs (lint, type-check, unit tests) in parallel
- Use matrix strategies for multi-version testing

### Security
- Never print secrets in logs
- Use environment-specific secrets (staging vs production)
- Pin action versions to full SHA hashes for supply chain security

## Rules

- Always cache dependencies to speed up builds
- Use `concurrency` groups to cancel redundant runs on PR updates
- Pin CI tool versions (actions, Docker images) for reproducibility
- Keep pipeline duration under 10 minutes when possible
- Require CI to pass before allowing PR merges
- Separate CI (test on every push/PR) from CD (deploy only on main)
- Store secrets in the CI platform's secret management, never in the config file
- Add status badges to the README so build status is visible
