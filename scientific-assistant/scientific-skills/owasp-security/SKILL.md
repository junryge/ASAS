---
name: OWASP Security
description: OWASP Top 10 2025 security checklist for code review and secure development
version: 1.0.0
tags: [security, owasp, code-review, vulnerability, pentest]
---

# OWASP Security Code Review Skill

## OWASP Top 10: 2025 Checklist

### A01: Broken Access Control
- Deny by default: all resources require authentication unless explicitly public
- Enforce server-side access control — never rely on client-side checks
- Validate user ownership of requested resources (IDOR prevention)
- Disable directory listing and remove default credentials
- Rate-limit API access to prevent automated abuse
- Log and alert on access control failures

```python
## BAD: No ownership check
@app.route('/api/user/<user_id>/data')
def get_data(user_id):
    return db.get_user_data(user_id)

## GOOD: Verify ownership
@app.route('/api/user/<user_id>/data')
@login_required
def get_data(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        abort(403)
    return db.get_user_data(user_id)
```

### A02: Cryptographic Failures
- Never store passwords in plaintext — use bcrypt/scrypt/argon2
- Use TLS 1.2+ for all data in transit
- Encrypt sensitive data at rest (AES-256-GCM)
- Never hardcode secrets — use environment variables or secret managers
- Generate random values with `secrets` module, not `random`

### A03: Injection
- Use parameterized queries for ALL database access
- Validate and sanitize all user input on the server side
- Use ORM methods instead of raw SQL where possible
- Escape output based on context (HTML, JS, URL, CSS)
- Apply Content-Security-Policy headers

```python
## BAD: SQL Injection
query = f"SELECT * FROM users WHERE name = '{user_input}'"

## GOOD: Parameterized query
cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))
```

### A04: Insecure Design
- Implement threat modeling during design phase
- Apply principle of least privilege
- Validate business logic server-side (price, quantity, discounts)
- Use rate limiting for resource-intensive operations
- Implement proper error handling without exposing internals

### A05: Security Misconfiguration
- Remove default accounts and unnecessary features
- Keep all software, frameworks, and dependencies updated
- Configure security headers: CSP, X-Frame-Options, X-Content-Type-Options
- Disable detailed error messages in production
- Review cloud storage permissions (S3 buckets, Azure blobs)

### A06: Vulnerable Components
- Maintain inventory of all dependencies and versions
- Monitor for CVEs: use `pip-audit`, `npm audit`, `safety check`
- Remove unused dependencies
- Pin dependency versions in production
- Prefer well-maintained packages with active security response

### A07: Authentication Failures
- Implement multi-factor authentication (MFA)
- Enforce strong password policy: min 8 chars, check against breached lists
- Use secure session management: HttpOnly, Secure, SameSite cookies
- Implement account lockout after failed attempts (5-10 tries)
- Never expose session tokens in URLs

### A08: Data Integrity Failures
- Verify digital signatures on software updates
- Use integrity checks (SRI) for CDN-hosted scripts
- Validate serialized data from untrusted sources
- Implement CI/CD pipeline security: signed commits, protected branches
- Review auto-update mechanisms for tampering resistance

### A09: Logging & Monitoring Failures
- Log authentication events (success and failure)
- Log access control failures and input validation failures
- Ensure logs contain sufficient context but NO sensitive data
- Implement alerting for suspicious patterns
- Retain logs for incident response (minimum 90 days)

### A10: Server-Side Request Forgery (SSRF)
- Validate and sanitize ALL user-supplied URLs
- Deny access to internal networks (169.254.x.x, 10.x.x.x, 127.x.x.x)
- Use allowlists for external service connections
- Disable HTTP redirects for server-side requests
- Use network segmentation to limit SSRF impact

## Language-Specific Security

### Python
- Use `secrets.token_urlsafe()` for tokens, not `random`
- Use `subprocess` with `shell=False` and explicit args list
- Avoid `eval()`, `exec()`, `pickle.loads()` with untrusted data
- Use `defusedxml` for XML parsing (prevent XXE)
- Set `DEBUG=False` in production Flask/Django

### JavaScript/Node.js
- Use `helmet` middleware for security headers
- Validate input with `joi` or `zod`
- Use `DOMPurify` for HTML sanitization
- Avoid `eval()`, `new Function()`, `innerHTML` with user data
- Enable CORS with specific origins, not `*`

### SQL
- Always use parameterized queries or ORM
- Grant minimum required database privileges
- Use separate DB accounts for read vs write operations
- Encrypt connections with SSL/TLS
- Regular backup and test restore procedures

## Security Headers Checklist
```
Content-Security-Policy: default-src 'self'; script-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## Code Review Security Checklist
- [ ] No hardcoded secrets/API keys/passwords
- [ ] All user input validated and sanitized
- [ ] SQL queries use parameterized statements
- [ ] Authentication checks on all protected endpoints
- [ ] Authorization: users can only access their own data
- [ ] Sensitive data encrypted at rest and in transit
- [ ] Error messages don't leak internal details
- [ ] Dependencies checked for known vulnerabilities
- [ ] Logging includes security events without sensitive data
- [ ] CSRF protection enabled for state-changing operations
