---
name: logging
description: Set up structured logging frameworks. TRIGGER when the user asks to add logging, set up a logger, configure log levels, implement structured logging, or improve log output.
---
# Logging

Set up structured logging for consistent, searchable, and useful application logs.

## Steps

1. **Choose a logging library** - Select the appropriate library for the project's language and stack.
2. **Configure log levels** - Set up appropriate levels for development vs production.
3. **Add structured fields** - Use JSON-structured logs with consistent fields.
4. **Instrument key operations** - Add logging at important points in the application.
5. **Set up log output** - Configure where logs go (stdout, file, external service).

## Logging Libraries

| Language | Library |
|----------|---------|
| Node.js | pino, winston |
| Python | structlog, logging (stdlib) |
| Go | slog (stdlib), zerolog, zap |
| Java | SLF4J + Logback |
| Rust | tracing |

## Node.js (pino)

### Setup
```typescript
// logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  ...(process.env.NODE_ENV === 'development' && {
    transport: {
      target: 'pino-pretty',
      options: { colorize: true },
    },
  }),
  redact: ['req.headers.authorization', 'password', 'token'],
});

// Create child loggers with context
export function createLogger(module: string) {
  return logger.child({ module });
}
```

### Usage
```typescript
import { createLogger } from './logger';

const log = createLogger('user-service');

async function createUser(data: CreateUserInput) {
  log.info({ email: data.email }, 'Creating user');

  try {
    const user = await db.users.create(data);
    log.info({ userId: user.id }, 'User created successfully');
    return user;
  } catch (error) {
    log.error({ error, email: data.email }, 'Failed to create user');
    throw error;
  }
}
```

### Request Logging Middleware
```typescript
import { randomUUID } from 'crypto';

app.use((req, res, next) => {
  const requestId = req.headers['x-request-id'] || randomUUID();
  req.log = logger.child({ requestId, method: req.method, path: req.path });

  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    req.log.info({ statusCode: res.statusCode, duration }, 'Request completed');
  });

  next();
});
```

## Python (structlog)

### Setup
```python
# logger.py
import structlog
import logging

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

def get_logger(module: str):
    return structlog.get_logger(module=module)
```

### Usage
```python
from logger import get_logger

log = get_logger("user_service")

def create_user(data: dict) -> User:
    log.info("creating_user", email=data["email"])

    try:
        user = db.users.create(**data)
        log.info("user_created", user_id=user.id)
        return user
    except IntegrityError:
        log.warning("duplicate_user", email=data["email"])
        raise
    except Exception:
        log.exception("user_creation_failed", email=data["email"])
        raise
```

### Request Context (FastAPI)
```python
import structlog
from uuid import uuid4

@app.middleware("http")
async def logging_middleware(request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    log.info("request_completed", status_code=response.status_code, duration_ms=round(duration * 1000))
    response.headers["x-request-id"] = request_id
    return response
```

## Go (slog)

```go
package main

import (
    "log/slog"
    "os"
)

func main() {
    handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    })
    logger := slog.New(handler)
    slog.SetDefault(logger)

    slog.Info("server starting", "port", 8080)
}

func createUser(email string) (*User, error) {
    slog.Info("creating user", "email", email)

    user, err := db.CreateUser(email)
    if err != nil {
        slog.Error("failed to create user", "error", err, "email", email)
        return nil, err
    }

    slog.Info("user created", "user_id", user.ID)
    return user, nil
}
```

## Log Levels Guide

| Level | When to Use | Example |
|-------|-------------|---------|
| **trace** | Very detailed debugging info | Function entry/exit, variable values |
| **debug** | Diagnostic info for developers | Query parameters, cache hits/misses |
| **info** | Normal operations | Server started, request completed, user created |
| **warn** | Unexpected but handled situations | Deprecated API used, retry succeeded, rate limit approaching |
| **error** | Failures that need attention | Database connection failed, external API error |
| **fatal** | Application cannot continue | Missing required config, port already in use |

## Structured Log Output

```json
{
  "level": "info",
  "timestamp": "2025-03-15T10:30:00.000Z",
  "module": "user-service",
  "requestId": "req_abc123",
  "message": "User created successfully",
  "userId": "usr_456",
  "duration": 45
}
```

## Rules

- Use structured (JSON) logging in production -- never unstructured `console.log` or `print`
- Include a request ID in every log for a request, so related logs can be correlated
- Log at the right level: do not log everything as `info` or `error`
- Never log sensitive data: passwords, tokens, credit card numbers, PII
- Use `redact` or filtering to prevent accidental secret leakage
- Log the "why" and context, not just "what happened"
- Use consistent field names across the application (e.g., always `userId`, not sometimes `user_id`)
- In production, set level to `info` or `warn` -- `debug` generates too much volume
- Log errors once at the handling boundary, not at every level of the call stack
