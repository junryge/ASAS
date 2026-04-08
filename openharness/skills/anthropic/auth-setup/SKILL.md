---
name: auth-setup
description: Set up authentication (JWT, OAuth, session-based). TRIGGER when the user asks to add authentication, implement login, set up JWT, configure OAuth, add session management, or secure API endpoints.
---
# Auth Setup

Set up authentication and authorization for web applications and APIs.

## Steps

1. **Choose the auth strategy** - Based on the application type:
   - **Session-based**: Traditional web apps with server-rendered pages
   - **JWT**: SPAs, mobile apps, microservices
   - **OAuth 2.0 / OIDC**: Third-party login (Google, GitHub, etc.)
   - **API keys**: Service-to-service authentication
2. **Implement registration and login** - Hash passwords, issue tokens or sessions.
3. **Protect routes** - Add authentication middleware to protected endpoints.
4. **Handle token lifecycle** - Implement refresh, expiry, and revocation.
5. **Test security** - Verify auth cannot be bypassed.

## JWT Authentication (Node.js)

### Setup
```bash
npm install jsonwebtoken bcrypt
```

### Password Hashing
```typescript
import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
```

### Token Generation
```typescript
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET!;
const ACCESS_TOKEN_TTL = '15m';
const REFRESH_TOKEN_TTL = '7d';

function generateTokens(userId: string, role: string) {
  const accessToken = jwt.sign(
    { sub: userId, role },
    JWT_SECRET,
    { expiresIn: ACCESS_TOKEN_TTL },
  );

  const refreshToken = jwt.sign(
    { sub: userId, type: 'refresh' },
    JWT_SECRET,
    { expiresIn: REFRESH_TOKEN_TTL },
  );

  return { accessToken, refreshToken };
}

function verifyToken(token: string) {
  return jwt.verify(token, JWT_SECRET);
}
```

### Auth Routes
```typescript
// Register
app.post('/auth/register', asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  const existing = await db.users.findByEmail(email);
  if (existing) throw new ConflictError('Email already registered');

  const hash = await hashPassword(password);
  const user = await db.users.create({ email, password: hash });

  const tokens = generateTokens(user.id, user.role);
  res.status(201).json({ user: { id: user.id, email }, ...tokens });
}));

// Login
app.post('/auth/login', asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  const user = await db.users.findByEmail(email);
  if (!user || !(await verifyPassword(password, user.password))) {
    throw new UnauthorizedError('Invalid email or password');
  }

  const tokens = generateTokens(user.id, user.role);
  res.json({ user: { id: user.id, email }, ...tokens });
}));

// Refresh token
app.post('/auth/refresh', asyncHandler(async (req, res) => {
  const { refreshToken } = req.body;
  const payload = verifyToken(refreshToken);

  if (payload.type !== 'refresh') throw new UnauthorizedError('Invalid token');

  const user = await db.users.findById(payload.sub);
  if (!user) throw new UnauthorizedError('User not found');

  const tokens = generateTokens(user.id, user.role);
  res.json(tokens);
}));
```

### Auth Middleware
```typescript
function authenticate(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    throw new UnauthorizedError('Missing authorization header');
  }

  try {
    const token = header.slice(7);
    const payload = verifyToken(token);
    req.user = { id: payload.sub, role: payload.role };
    next();
  } catch {
    throw new UnauthorizedError('Invalid or expired token');
  }
}

function authorize(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!roles.includes(req.user.role)) {
      throw new ForbiddenError('Insufficient permissions');
    }
    next();
  };
}

// Usage
app.get('/admin/users', authenticate, authorize('admin'), getUsers);
app.get('/profile', authenticate, getProfile);
```

## OAuth 2.0 (Passport.js with Google)

```typescript
import passport from 'passport';
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';

passport.use(new GoogleStrategy(
  {
    clientID: process.env.GOOGLE_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    callbackURL: '/auth/google/callback',
  },
  async (accessToken, refreshToken, profile, done) => {
    let user = await db.users.findByGoogleId(profile.id);
    if (!user) {
      user = await db.users.create({
        googleId: profile.id,
        email: profile.emails?.[0]?.value,
        name: profile.displayName,
      });
    }
    return done(null, user);
  },
));

app.get('/auth/google', passport.authenticate('google', { scope: ['profile', 'email'] }));

app.get('/auth/google/callback',
  passport.authenticate('google', { failureRedirect: '/login' }),
  (req, res) => {
    const tokens = generateTokens(req.user.id, req.user.role);
    res.redirect(`/auth/success?token=${tokens.accessToken}`);
  },
);
```

## Python (FastAPI + JWT)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str, role: str) -> str:
    payload = {"sub": user_id, "role": role, "exp": datetime.utcnow() + timedelta(minutes=15)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user = await db.users.get(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/profile")
async def profile(user=Depends(get_current_user)):
    return {"id": user.id, "email": user.email}
```

## Rules

- NEVER store plaintext passwords -- always use bcrypt or argon2 with a cost factor >= 12
- Store JWT secrets in environment variables, never in code
- Use short-lived access tokens (15 min) and longer-lived refresh tokens (7 days)
- Validate all token claims (expiry, issuer, audience) on every request
- Implement rate limiting on login endpoints to prevent brute force attacks
- Return the same error message for "user not found" and "wrong password" to prevent user enumeration
- Use HTTPS in production -- tokens are useless if intercepted
- Invalidate refresh tokens on password change and logout
- Do not store JWTs in localStorage (XSS risk) -- use httpOnly cookies for web apps
- Implement CSRF protection when using cookie-based auth
