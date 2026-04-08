---
name: simplify
description: Review and refactor code for simplicity and reuse. TRIGGER when the user asks to simplify code, reduce complexity, clean up code, or remove duplication.
---
# Simplify

Review code for unnecessary complexity, duplication, and opportunities to improve clarity and reuse.

## Steps

1. **Identify the scope** - Determine which files or changes to review. Use `git diff` for recent changes or read specific files the user points to.
2. **Analyze complexity** - Look for:
   - Functions longer than 30 lines
   - Deeply nested conditionals (3+ levels)
   - Duplicated logic across files
   - Over-engineered abstractions (interfaces with one implementation, factories that create one thing)
   - Dead code, unused imports, commented-out blocks
3. **Propose simplifications** - For each finding, suggest a concrete improvement.
4. **Apply changes** - Refactor the code, ensuring behavior is preserved.
5. **Verify** - Run existing tests to confirm nothing is broken.

## Common Simplifications

### Extract repeated logic
```python
# Before: duplicated validation in multiple handlers
def create_user(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    ...

def update_user(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    ...

# After: shared validation
def validate_email(email: str) -> str:
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    return email
```

### Flatten nested conditionals
```python
# Before
def process(item):
    if item is not None:
        if item.is_valid():
            if item.status == "active":
                return handle(item)
    return None

# After: early returns
def process(item):
    if item is None:
        return None
    if not item.is_valid():
        return None
    if item.status != "active":
        return None
    return handle(item)
```

### Replace complex conditionals with lookup tables
```python
# Before
def get_status_label(code):
    if code == 0:
        return "pending"
    elif code == 1:
        return "active"
    elif code == 2:
        return "archived"
    else:
        return "unknown"

# After
STATUS_LABELS = {0: "pending", 1: "active", 2: "archived"}

def get_status_label(code):
    return STATUS_LABELS.get(code, "unknown")
```

## Rules

- Preserve existing behavior -- simplification must not change what the code does
- Run tests after every change
- Do not over-abstract; simple inline code is often clearer than a premature abstraction
- If unsure whether a simplification improves clarity, ask the user
