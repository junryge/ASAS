---
name: caching
description: Implement caching strategies (Redis, in-memory). TRIGGER when the user asks to add caching, set up Redis, implement memoization, cache API responses, or improve response times with caching.
---
# Caching

Implement caching strategies to improve application performance and reduce load on databases and external services.

## Steps

1. **Identify what to cache** - Find the bottleneck: slow database queries, expensive computations, frequent API calls, or static content.
2. **Choose the caching layer** - In-memory (application-level), distributed (Redis/Memcached), or CDN/HTTP caching.
3. **Define cache keys** - Design a consistent key naming scheme.
4. **Set TTL and invalidation** - Determine how long data should be cached and how to invalidate stale data.
5. **Implement the cache** - Add caching with proper error handling (cache failures should not break the app).
6. **Monitor** - Track hit rates, miss rates, and memory usage.

## In-Memory Caching

### Node.js (node-cache)
```typescript
import NodeCache from 'node-cache';

const cache = new NodeCache({ stdTTL: 300, checkperiod: 60 });

async function getUser(id: string): Promise<User> {
  const cacheKey = `user:${id}`;

  // Check cache first
  const cached = cache.get<User>(cacheKey);
  if (cached) return cached;

  // Cache miss: fetch from database
  const user = await db.users.findById(id);
  if (user) {
    cache.set(cacheKey, user);
  }
  return user;
}

// Invalidate when data changes
async function updateUser(id: string, data: Partial<User>) {
  await db.users.update(id, data);
  cache.del(`user:${id}`);
}
```

### Python (functools.lru_cache)
```python
from functools import lru_cache
from cachetools import TTLCache

# Simple memoization (no TTL)
@lru_cache(maxsize=1024)
def fibonacci(n: int) -> int:
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# TTL-based cache
user_cache = TTLCache(maxsize=1000, ttl=300)

def get_user(user_id: str) -> User:
    if user_id in user_cache:
        return user_cache[user_id]

    user = db.users.get(user_id)
    if user:
        user_cache[user_id] = user
    return user
```

## Redis Caching

### Node.js (ioredis)
```typescript
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL);

// Cache-aside pattern
async function getCachedUser(id: string): Promise<User> {
  const cacheKey = `user:${id}`;

  // Try cache
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // Fetch from database
  const user = await db.users.findById(id);
  if (user) {
    await redis.set(cacheKey, JSON.stringify(user), 'EX', 300); // 5 min TTL
  }
  return user;
}

// Invalidate on write
async function updateUser(id: string, data: Partial<User>) {
  await db.users.update(id, data);
  await redis.del(`user:${id}`);
  // Also invalidate related caches
  await redis.del(`user-list:page:*`);
}

// Cache with lock (prevent thundering herd)
async function getCachedWithLock(key: string, fetchFn: () => Promise<any>, ttl = 300) {
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached);

  const lockKey = `lock:${key}`;
  const acquired = await redis.set(lockKey, '1', 'EX', 10, 'NX');

  if (acquired) {
    try {
      const data = await fetchFn();
      await redis.set(key, JSON.stringify(data), 'EX', ttl);
      return data;
    } finally {
      await redis.del(lockKey);
    }
  }

  // Another process is fetching; wait and retry
  await new Promise(resolve => setTimeout(resolve, 100));
  return getCachedWithLock(key, fetchFn, ttl);
}
```

### Python (redis-py)
```python
import redis
import json

r = redis.Redis.from_url(os.environ["REDIS_URL"])

def get_cached_user(user_id: str) -> dict | None:
    cache_key = f"user:{user_id}"

    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    user = db.users.get(user_id)
    if user:
        r.setex(cache_key, 300, json.dumps(user.to_dict()))
    return user

def invalidate_user(user_id: str):
    r.delete(f"user:{user_id}")
```

## HTTP Caching

```typescript
// Express.js cache headers
app.get('/api/products', (req, res) => {
  res.set({
    'Cache-Control': 'public, max-age=300, s-maxage=600',  // 5 min browser, 10 min CDN
    'ETag': computeETag(data),
    'Vary': 'Accept-Encoding',
  });
  res.json(data);
});

// Static assets: long cache with content hash in filename
app.use('/static', express.static('public', {
  maxAge: '1y',
  immutable: true,
}));

// Private, user-specific data
app.get('/api/profile', auth, (req, res) => {
  res.set('Cache-Control', 'private, max-age=60');
  res.json(profile);
});
```

## Cache Key Naming Convention

```
# Pattern: service:entity:identifier[:qualifier]
user:123                    # Single user
user:123:orders             # User's orders
products:list:page:1:size:20  # Paginated product list
search:results:sha256(query)  # Search results by query hash
config:feature-flags         # Application config
```

## Caching Strategies

| Strategy | Description | Use When |
|----------|-------------|----------|
| **Cache-aside** | App checks cache, fetches from DB on miss | Most common, read-heavy workloads |
| **Write-through** | App writes to cache and DB simultaneously | Data consistency is critical |
| **Write-behind** | App writes to cache, async flush to DB | Write-heavy, eventual consistency OK |
| **Read-through** | Cache fetches from DB on miss automatically | Using a cache library that supports it |

## Rules

- Cache should be a performance optimization, not a correctness requirement -- the app must work without it
- Always set a TTL on cached data to prevent stale data and memory leaks
- Handle cache failures gracefully -- fall back to the source of truth
- Use consistent key naming conventions across the application
- Invalidate cache entries when the underlying data changes
- Monitor cache hit rates -- a rate below 80% may indicate the wrong data is being cached
- Be careful with caching user-specific data -- ensure one user cannot see another's cached data
- Never cache sensitive data (auth tokens, passwords) without encryption
- Size your cache appropriately -- monitor memory usage and eviction rates
