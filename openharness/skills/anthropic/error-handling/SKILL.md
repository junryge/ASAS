---
name: error-handling
description: Implement proper error handling patterns. TRIGGER when the user asks to add error handling, handle exceptions, improve error messages, implement error boundaries, or create custom error types.
---
# Error Handling

Implement robust error handling patterns that make applications reliable and debuggable.

## Steps

1. **Audit current error handling** - Look for unhandled promises, bare `except` blocks, missing error boundaries, and swallowed errors.
2. **Define error types** - Create custom error classes for different failure categories (validation, auth, not found, external service).
3. **Implement handling at each layer** - Add appropriate error handling at the controller, service, and infrastructure layers.
4. **Set up global handlers** - Add catch-all error handlers as a safety net.
5. **Test error paths** - Verify that errors are caught, logged, and surfaced correctly.

## Error Handling Patterns

### Custom Error Types (TypeScript)
```typescript
// errors.ts
export class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500,
    public readonly isOperational: boolean = true,
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, public readonly fields?: Record<string, string>) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`, 'NOT_FOUND', 404);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Authentication required') {
    super(message, 'UNAUTHORIZED', 401);
  }
}

export class ExternalServiceError extends AppError {
  constructor(service: string, cause?: Error) {
    super(`External service ${service} failed`, 'EXTERNAL_SERVICE_ERROR', 502);
    if (cause) this.cause = cause;
  }
}
```

### Express.js Error Middleware
```typescript
// errorHandler.ts
import { Request, Response, NextFunction } from 'express';
import { AppError } from './errors';
import { logger } from './logger';

export function errorHandler(err: Error, req: Request, res: Response, next: NextFunction) {
  if (err instanceof AppError) {
    // Operational errors: expected, handle gracefully
    logger.warn('Operational error', {
      code: err.code,
      message: err.message,
      path: req.path,
    });

    return res.status(err.statusCode).json({
      error: {
        code: err.code,
        message: err.message,
        ...(err instanceof ValidationError && err.fields ? { fields: err.fields } : {}),
      },
    });
  }

  // Programmer errors: unexpected, log full details
  logger.error('Unexpected error', {
    error: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
    },
  });
}

// Usage in app.ts
app.use(errorHandler);
```

### Async Error Handling (Express)
```typescript
// Wrap async route handlers to catch rejected promises
function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<any>) {
  return (req: Request, res: Response, next: NextFunction) => {
    fn(req, res, next).catch(next);
  };
}

app.get('/users/:id', asyncHandler(async (req, res) => {
  const user = await userService.findById(req.params.id);
  if (!user) throw new NotFoundError('User', req.params.id);
  res.json({ data: user });
}));
```

### Python Exception Handling
```python
# errors.py
class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 500):
        super().__init__(message)
        self.code = code
        self.status_code = status_code

class ValidationError(AppError):
    def __init__(self, message: str, fields: dict | None = None):
        super().__init__(message, "VALIDATION_ERROR", 400)
        self.fields = fields or {}

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} with id {id} not found", "NOT_FOUND", 404)

# FastAPI error handler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": str(exc)}},
    )

@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception("Unexpected error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )
```

### React Error Boundary
```tsx
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Error boundary caught:', error, info.componentStack);
    // Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div role="alert">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### Retry with Exponential Backoff
```typescript
async function withRetry<T>(
  fn: () => Promise<T>,
  options: { maxRetries?: number; baseDelay?: number } = {},
): Promise<T> {
  const { maxRetries = 3, baseDelay = 1000 } = options;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries) throw error;
      const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw new Error('Unreachable');
}

// Usage
const data = await withRetry(() => fetchFromExternalAPI(url), { maxRetries: 3 });
```

## Anti-Patterns to Avoid

```typescript
// BAD: swallowing errors silently
try { await riskyOperation(); } catch (e) { /* silent */ }

// BAD: catching and only logging
try { await riskyOperation(); } catch (e) { console.log(e); }

// BAD: throwing generic errors
throw new Error('Something went wrong');

// BAD: returning error strings instead of throwing
function getUser(id) {
  if (!id) return 'Invalid ID';  // Caller will forget to check
}
```

## Rules

- Never swallow errors silently -- always log or rethrow
- Distinguish between operational errors (expected, handle gracefully) and programmer errors (bugs, crash or log)
- Use specific error types, not generic `Error` or bare strings
- Include enough context in error messages to diagnose the issue (what failed, with what input)
- Do not expose internal error details (stack traces, SQL queries) in API responses
- Always handle promise rejections -- use unhandledRejection handlers as a safety net
- Retry only idempotent, transient failures (network timeouts) -- never retry validation errors
- Log errors once at the boundary, not at every catch in the chain
