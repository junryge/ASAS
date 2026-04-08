---
name: security-audit
description: Scan code for security vulnerabilities (OWASP top 10). TRIGGER when the user asks to audit security, check for vulnerabilities, scan for security issues, or review code for OWASP risks.
---
# Security Audit

Scan code for security vulnerabilities, focusing on the OWASP Top 10 and language-specific security risks.

## Steps

1. **Determine scope** - Identify what to audit: entire codebase, specific files, recent changes (`git diff`), or a pull request.
2. **Check for secrets** - Scan for hardcoded credentials, API keys, tokens, and passwords.
3. **Audit OWASP Top 10** - Check each vulnerability category below.
4. **Check dependencies** - Look for known vulnerable dependencies.
5. **Report findings** - Organize by severity with remediation steps.

## OWASP Top 10 Checklist

### 1. Injection (SQL, NoSQL, Command, LDAP)
```python
# VULNERABLE: SQL injection
query = f"SELECT * FROM users WHERE id = {user_input}"

# SAFE: parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_input,))
```

### 2. Broken Authentication
- Check for: weak password policies, missing rate limiting, session tokens in URLs, missing MFA
- Verify: passwords are hashed (bcrypt/argon2), sessions expire, tokens are rotated

### 3. Sensitive Data Exposure
- Check for: secrets in code or config, unencrypted data in transit or at rest
- Scan for patterns:
```bash
# Look for potential secrets
grep -rn "password\s*=\|api_key\s*=\|secret\s*=\|token\s*=" --include="*.py" --include="*.ts" --include="*.js" .
grep -rn "BEGIN.*PRIVATE KEY" .
```

### 4. XML External Entities (XXE)
```python
# VULNERABLE
from lxml import etree
tree = etree.parse(user_xml)

# SAFE: disable external entities
parser = etree.XMLParser(resolve_entities=False, no_network=True)
tree = etree.parse(user_xml, parser)
```

### 5. Broken Access Control
- Verify: authorization checks on every endpoint, proper role validation, no IDOR vulnerabilities
- Check that users cannot access other users' resources by changing IDs in URLs

### 6. Security Misconfiguration
- Check for: debug mode in production, default credentials, unnecessary features enabled, missing security headers
```python
# Django: ensure these are set in production
DEBUG = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

### 7. Cross-Site Scripting (XSS)
```javascript
// VULNERABLE: innerHTML with user input
element.innerHTML = userInput;

// SAFE: use textContent or sanitize
element.textContent = userInput;
// or use DOMPurify
element.innerHTML = DOMPurify.sanitize(userInput);
```

### 8. Insecure Deserialization
```python
# VULNERABLE: pickle with untrusted data
import pickle
data = pickle.loads(user_input)

# SAFE: use JSON or validated schemas
import json
data = json.loads(user_input)
```

### 9. Using Components with Known Vulnerabilities
```bash
# Check npm dependencies
npm audit

# Check Python dependencies
pip-audit
# or
safety check

# Check Go dependencies
govulncheck ./...
```

### 10. Insufficient Logging & Monitoring
- Verify: authentication attempts are logged, access control failures are logged, input validation failures are logged
- Check: logs do NOT contain sensitive data (passwords, tokens, PII)

## Dependency Scanning Commands
```bash
# Node.js
npm audit --json
npx auditjs ossi

# Python
pip-audit
safety check -r requirements.txt

# Ruby
bundle audit check --update

# Go
govulncheck ./...
```

## Output Format

Organize findings by severity:

- **CRITICAL** - Actively exploitable vulnerabilities, exposed secrets
- **HIGH** - Injection risks, broken auth, access control failures
- **MEDIUM** - Missing security headers, weak configurations
- **LOW** - Informational findings, minor hardening suggestions

For each finding:
1. File and line number
2. Vulnerability type (OWASP category)
3. Description of the risk
4. Remediation with code example

## Rules

- Never expose or log actual secrets found during the audit -- redact them
- Check all user input entry points (HTTP params, headers, file uploads, WebSocket messages)
- Verify that security controls exist at the server side, not just client side
- If no vulnerabilities are found, say so -- do not fabricate issues
- Recommend running automated tools (npm audit, pip-audit) in addition to manual review
