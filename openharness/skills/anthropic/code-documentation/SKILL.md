---
name: code-documentation
description: Generate documentation (JSDoc, Sphinx, typedoc). TRIGGER when the user asks to document code, add JSDoc comments, generate API docs, set up Sphinx, create typedoc, or improve code documentation.
---
# Code Documentation

Generate and maintain code documentation using language-appropriate documentation tools.

## Steps

1. **Assess current documentation** - Check for existing doc comments, README, and generated docs.
2. **Identify the documentation tool** - Match the tool to the language:
   - TypeScript/JavaScript: TSDoc/JSDoc, TypeDoc
   - Python: docstrings (Google/NumPy/Sphinx style), Sphinx, MkDocs
   - Go: godoc conventions
   - Rust: rustdoc (`///` comments)
   - Java: Javadoc
3. **Write doc comments** - Add documentation to public APIs, classes, functions, and types.
4. **Generate docs** - Run the documentation generator and verify output.
5. **Set up automation** - Add doc generation to the CI pipeline.

## TypeScript / JavaScript (JSDoc/TSDoc)

### Function Documentation
```typescript
/**
 * Creates a new user account and sends a welcome email.
 *
 * @param data - The user registration data
 * @param options - Optional configuration
 * @param options.sendEmail - Whether to send a welcome email (default: true)
 * @returns The newly created user
 * @throws {ValidationError} If the email is already registered
 * @throws {ExternalServiceError} If the email service is unavailable
 *
 * @example
 * ```ts
 * const user = await createUser({
 *   email: 'alice@example.com',
 *   name: 'Alice Smith',
 *   password: 'securePassword123',
 * });
 * console.log(user.id); // "usr_abc123"
 * ```
 */
async function createUser(
  data: CreateUserInput,
  options?: { sendEmail?: boolean },
): Promise<User> {
  // implementation
}
```

### Interface Documentation
```typescript
/**
 * Configuration for the database connection pool.
 *
 * @example
 * ```ts
 * const config: PoolConfig = {
 *   host: 'localhost',
 *   port: 5432,
 *   maxConnections: 20,
 *   idleTimeoutMs: 30000,
 * };
 * ```
 */
interface PoolConfig {
  /** Database server hostname */
  host: string;

  /** Database server port (default: 5432) */
  port?: number;

  /** Maximum number of connections in the pool */
  maxConnections: number;

  /**
   * Time in milliseconds before an idle connection is closed.
   * Set to 0 to disable idle timeout.
   */
  idleTimeoutMs: number;
}
```

### TypeDoc Setup
```bash
npm install --save-dev typedoc

# Generate docs
npx typedoc --entryPoints src/index.ts --out docs
```

```json
// typedoc.json
{
  "entryPoints": ["src/index.ts"],
  "out": "docs",
  "excludePrivate": true,
  "excludeInternal": true,
  "readme": "README.md",
  "plugin": ["typedoc-plugin-markdown"]
}
```

## Python (Docstrings + Sphinx)

### Google Style Docstrings
```python
def create_user(email: str, name: str, role: str = "user") -> User:
    """Create a new user account.

    Validates the email, hashes the password, stores the user in the database,
    and sends a welcome email asynchronously.

    Args:
        email: The user's email address. Must be unique.
        name: The user's full name.
        role: The user's role. One of "user", "admin", "moderator".
            Defaults to "user".

    Returns:
        The newly created User object with an assigned ID.

    Raises:
        ValidationError: If the email format is invalid or already registered.
        DatabaseError: If the database write fails.

    Example:
        >>> user = create_user("alice@example.com", "Alice Smith")
        >>> print(user.id)
        'usr_abc123'
    """
```

### NumPy Style Docstrings
```python
def calculate_statistics(data: list[float]) -> dict:
    """Calculate descriptive statistics for a dataset.

    Parameters
    ----------
    data : list of float
        The input dataset. Must contain at least one value.

    Returns
    -------
    dict
        A dictionary containing:
        - mean : float
        - median : float
        - std : float
        - min : float
        - max : float

    Raises
    ------
    ValueError
        If the input list is empty.

    Examples
    --------
    >>> calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
    {'mean': 3.0, 'median': 3.0, 'std': 1.414, 'min': 1.0, 'max': 5.0}
    """
```

### Sphinx Setup
```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

# Initialize Sphinx
sphinx-quickstart docs
```

```python
# docs/conf.py
project = 'MyProject'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',     # Google/NumPy style docstrings
    'sphinx_autodoc_typehints', # Type hint support
    'sphinx.ext.viewcode',     # Link to source code
]
html_theme = 'sphinx_rtd_theme'
autodoc_member_order = 'bysource'
napoleon_google_docstring = True
```

```bash
# Generate API docs from source
sphinx-apidoc -o docs/api src/
sphinx-build -b html docs docs/_build
```

### MkDocs Setup
```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
```

```yaml
# mkdocs.yml
site_name: MyProject
theme:
  name: material
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
            docstring_style: google
nav:
  - Home: index.md
  - API Reference: api.md
```

## Go (godoc)

```go
// Package user provides functions for managing user accounts.
//
// The user package handles registration, authentication, and profile
// management. All database operations are transactional.
package user

// User represents a registered user account.
type User struct {
    // ID is the unique identifier assigned on creation.
    ID string

    // Email is the user's email address. Must be unique.
    Email string

    // Name is the user's display name.
    Name string
}

// Create registers a new user account.
//
// It validates the email, hashes the password, and stores the user
// in the database. Returns an error if the email is already taken.
//
// Example:
//
//	user, err := userService.Create("alice@example.com", "Alice", "password123")
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(user.ID)
func (s *Service) Create(email, name, password string) (*User, error) {
    // implementation
}
```

## What to Document

| Priority | What | Why |
|----------|------|-----|
| **Always** | Public API functions and methods | Users need to know how to call them |
| **Always** | Function parameters, return types, errors | Contract between caller and implementation |
| **Always** | Non-obvious behavior, gotchas | Prevents misuse |
| **Usually** | Interfaces and types | Documents the domain model |
| **Usually** | Package/module purpose | Explains what this code area is responsible for |
| **Sometimes** | Complex internal logic | Helps future maintainers |
| **Never** | Obvious code (`// increment i` on `i++`) | Adds noise, no value |

## Rules

- Document the "why" and "what", not the "how" -- the code shows the how
- Keep doc comments up to date when the code changes -- wrong docs are worse than no docs
- Include at least one usage example for public APIs
- Document error conditions and edge cases -- callers need to know what can go wrong
- Use the documentation style already established in the project
- Do not write trivial docs that just restate the function name ("getName returns the name")
- Generate and host docs as part of CI -- stale generated docs are misleading
- Include type information in docs for dynamically-typed languages (Python, JavaScript)
