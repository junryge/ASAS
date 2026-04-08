---
name: performance
description: Profile and optimize code performance. TRIGGER when the user asks to optimize performance, speed up code, reduce memory usage, profile an application, or fix slow queries.
---
# Performance

Profile, identify, and fix performance bottlenecks in applications.

## Steps

1. **Establish a baseline** - Measure current performance with concrete numbers (response time, throughput, memory usage) before making changes.
2. **Identify the bottleneck** - Profile the application to find where time/memory is actually spent. Do not guess.
3. **Analyze the hotspot** - Understand why the bottleneck exists (algorithmic complexity, I/O, memory allocation, contention).
4. **Optimize** - Apply the appropriate optimization technique.
5. **Measure again** - Verify the optimization actually improved performance. Compare against the baseline.

## Profiling Tools

### Python
```python
# cProfile for CPU profiling
import cProfile
cProfile.run('my_function()', sort='cumulative')

# line_profiler for line-by-line timing
# pip install line_profiler
@profile
def slow_function():
    ...
# Run: kernprof -l -v script.py

# memory_profiler for memory usage
# pip install memory_profiler
from memory_profiler import profile

@profile
def memory_heavy():
    data = [i ** 2 for i in range(1_000_000)]
    return sum(data)

# timeit for microbenchmarks
import timeit
timeit.timeit('sorted(data)', setup='data = list(range(1000))', number=10000)
```

### Node.js
```javascript
// Built-in profiler
// node --prof app.js
// node --prof-process isolate-*.log > profile.txt

// Performance hooks
const { performance, PerformanceObserver } = require('perf_hooks');

performance.mark('start');
doExpensiveWork();
performance.mark('end');
performance.measure('expensive-work', 'start', 'end');

const obs = new PerformanceObserver((items) => {
  items.getEntries().forEach((entry) => {
    console.log(`${entry.name}: ${entry.duration.toFixed(2)}ms`);
  });
});
obs.observe({ entryTypes: ['measure'] });

// console.time for quick measurements
console.time('operation');
await doWork();
console.timeEnd('operation');
```

### Go
```go
import (
    "net/http"
    _ "net/http/pprof"
    "runtime"
    "testing"
)

// Enable pprof in your server
func main() {
    go func() {
        http.ListenAndServe(":6060", nil)
    }()
    // Then visit http://localhost:6060/debug/pprof/
}

// Benchmark functions
func BenchmarkMyFunction(b *testing.B) {
    for i := 0; i < b.N; i++ {
        myFunction()
    }
}
// Run: go test -bench=. -benchmem
```

## Common Optimizations

### Database Query Optimization
```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_orders_created_at ON orders (created_at);

-- Use EXPLAIN ANALYZE to understand query plans
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123 ORDER BY created_at DESC LIMIT 20;

-- Avoid SELECT * -- select only needed columns
SELECT id, total, status FROM orders WHERE user_id = 123;
```

### N+1 Query Problem
```python
# BAD: N+1 queries
users = User.query.all()
for user in users:
    print(user.orders)  # Each access triggers a query

# GOOD: eager loading
users = User.query.options(joinedload(User.orders)).all()
```

### Algorithmic Improvements
```python
# BAD: O(n^2) - checking membership in a list
def find_duplicates(items):
    seen = []
    dupes = []
    for item in items:
        if item in seen:      # O(n) lookup
            dupes.append(item)
        seen.append(item)
    return dupes

# GOOD: O(n) - using a set
def find_duplicates(items):
    seen = set()
    dupes = []
    for item in items:
        if item in seen:      # O(1) lookup
            dupes.append(item)
        seen.add(item)
    return dupes
```

### Caching Expensive Computations
```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def expensive_calculation(n):
    # Result is cached for repeated calls with same argument
    return sum(i ** 2 for i in range(n))
```

### Batch Operations
```python
# BAD: one insert per iteration
for item in items:
    db.execute("INSERT INTO records (value) VALUES (%s)", (item,))

# GOOD: batch insert
db.executemany("INSERT INTO records (value) VALUES (%s)", [(item,) for item in items])
```

### Async I/O
```python
import asyncio
import aiohttp

# BAD: sequential HTTP requests
results = []
for url in urls:
    response = requests.get(url)
    results.append(response.json())

# GOOD: concurrent HTTP requests
async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [await r.json() for r in responses]
```

## Rules

- Always measure before and after optimization -- prove the improvement with numbers
- Profile before optimizing -- do not guess where the bottleneck is
- Optimize the biggest bottleneck first (Amdahl's Law)
- Do not sacrifice readability for micro-optimizations unless the profiler shows it matters
- Consider trade-offs: memory vs speed, complexity vs performance
- Add benchmarks for performance-critical code so regressions are caught
- Document why non-obvious optimizations were made (future developers will wonder)
- Test correctness after every optimization -- fast but wrong is worse than slow
