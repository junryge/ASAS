---
name: monitoring
description: Set up logging, metrics, alerting, and health checks. TRIGGER when the user asks to add monitoring, set up metrics, create health checks, configure alerting, or implement observability.
---
# Monitoring

Set up application monitoring including health checks, metrics collection, alerting, and dashboards.

## Steps

1. **Assess the stack** - Identify the application framework, hosting environment, and existing monitoring tools.
2. **Add health checks** - Create endpoints that report application and dependency health.
3. **Instrument metrics** - Add counters, histograms, and gauges for key business and operational metrics.
4. **Set up alerting** - Define alert rules for critical conditions.
5. **Create dashboards** - Build dashboards for visibility into application behavior.

## Health Checks

### Express.js (Node.js)
```javascript
// health.js
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/health/ready', async (req, res) => {
  const checks = {
    database: await checkDatabase(),
    redis: await checkRedis(),
    externalApi: await checkExternalApi(),
  };

  const allHealthy = Object.values(checks).every(c => c.status === 'ok');
  const statusCode = allHealthy ? 200 : 503;

  res.status(statusCode).json({
    status: allHealthy ? 'ok' : 'degraded',
    checks,
    timestamp: new Date().toISOString(),
  });
});

async function checkDatabase() {
  try {
    await db.query('SELECT 1');
    return { status: 'ok' };
  } catch (err) {
    return { status: 'error', message: err.message };
  }
}
```

### FastAPI (Python)
```python
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness():
    checks = {}
    try:
        await db.execute("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}

    all_ok = all(c["status"] == "ok" for c in checks.values())
    status_code = 200 if all_ok else 503
    return Response(
        content=json.dumps({"status": "ok" if all_ok else "degraded", "checks": checks}),
        status_code=status_code,
        media_type="application/json",
    )
```

## Metrics with Prometheus

### Node.js (prom-client)
```javascript
const client = require('prom-client');

// Default metrics (CPU, memory, event loop)
client.collectDefaultMetrics();

// Custom metrics
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 5],
});

const activeConnections = new client.Gauge({
  name: 'active_connections',
  help: 'Number of active connections',
});

const requestCounter = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code'],
});

// Middleware
app.use((req, res, next) => {
  const end = httpRequestDuration.startTimer();
  res.on('finish', () => {
    end({ method: req.method, route: req.route?.path || req.path, status_code: res.statusCode });
    requestCounter.inc({ method: req.method, route: req.route?.path || req.path, status_code: res.statusCode });
  });
  next();
});

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});
```

### Python (prometheus_client)
```python
from prometheus_client import Counter, Histogram, generate_latest
import time

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(duration)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Key Metrics to Track

| Category | Metrics |
|----------|---------|
| **Latency** | p50, p95, p99 response times |
| **Traffic** | Requests per second by endpoint |
| **Errors** | Error rate (4xx, 5xx), error types |
| **Saturation** | CPU, memory, disk, connection pool usage |
| **Business** | Signups, orders, payments, conversions |

## Alerting Rules (Prometheus)

```yaml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate (> 5%)"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p95 latency > 1 second"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is unreachable"
```

## Rules

- Every production service must have `/health` and `/metrics` endpoints
- Use the RED method: Rate, Errors, Duration for request-driven services
- Use the USE method: Utilization, Saturation, Errors for resources
- Set alerts on symptoms (high error rate), not causes (high CPU) when possible
- Avoid alert fatigue -- only alert on actionable conditions
- Include runbook links in alert annotations
- Do not log sensitive data (passwords, tokens, PII) in metrics or logs
- Test alerts by intentionally triggering them in staging
