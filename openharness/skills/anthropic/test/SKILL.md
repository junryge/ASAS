---
name: test
description: Write and run tests (unit, integration, e2e). TRIGGER when the user asks to write tests, add test coverage, run tests, or fix failing tests.
---
# Test

Write and run tests to ensure code correctness and prevent regressions.

## Steps

1. **Detect the testing framework** - Check `package.json` (jest, vitest, mocha), `pyproject.toml`/`setup.cfg` (pytest), `Cargo.toml` (built-in), `go.mod` (built-in), or other config files to identify the project's testing setup.
2. **Understand the code under test** - Read the source file and understand its public API, edge cases, and dependencies.
3. **Identify test cases** - Cover:
   - Happy path (normal usage)
   - Edge cases (empty input, null, boundary values, large inputs)
   - Error cases (invalid input, network failures, permission errors)
   - Integration points (database, APIs, file system)
4. **Write the tests** - Follow the project's existing test patterns and conventions.
5. **Run the tests** - Execute and verify they pass. Fix any failures.

## Test Patterns

### Unit Test (Python / pytest)
```python
import pytest
from mymodule import calculate_total

def test_calculate_total_basic():
    assert calculate_total([10, 20, 30]) == 60

def test_calculate_total_empty():
    assert calculate_total([]) == 0

def test_calculate_total_negative():
    assert calculate_total([-5, 10]) == 5

def test_calculate_total_invalid_input():
    with pytest.raises(TypeError):
        calculate_total("not a list")
```

### Unit Test (TypeScript / vitest)
```typescript
import { describe, it, expect } from 'vitest';
import { calculateTotal } from './calculator';

describe('calculateTotal', () => {
  it('sums positive numbers', () => {
    expect(calculateTotal([10, 20, 30])).toBe(60);
  });

  it('returns 0 for empty array', () => {
    expect(calculateTotal([])).toBe(0);
  });

  it('throws on invalid input', () => {
    expect(() => calculateTotal(null as any)).toThrow();
  });
});
```

### Mocking External Dependencies
```python
from unittest.mock import patch, MagicMock

@patch('mymodule.requests.get')
def test_fetch_user(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"name": "Alice"}
    )
    user = fetch_user(1)
    assert user.name == "Alice"
    mock_get.assert_called_once_with("https://api.example.com/users/1")
```

## Test File Placement

- Follow the project's existing convention
- Common patterns: `tests/test_<module>.py`, `__tests__/<module>.test.ts`, `<module>_test.go`
- Co-located tests: `src/utils.ts` -> `src/utils.test.ts`

## Rules

- Match the project's existing test style and framework
- Tests should be independent -- no test should depend on another test's state
- Use descriptive test names that explain the scenario
- Avoid testing implementation details; test behavior and public APIs
- Clean up any test fixtures or temporary files after tests complete
- If tests fail, diagnose and fix the issue before reporting success
