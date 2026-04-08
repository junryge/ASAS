---
name: review
description: Code review for bugs, quality, and best practices. TRIGGER when the user asks to review code, check for issues, audit code quality, or review a pull request.
---
# Code Review

Perform thorough code reviews focusing on correctness, security, performance, and maintainability.

## Steps

1. **Understand the scope** - Determine what to review: staged changes (`git diff --staged`), a PR (`gh pr diff <number>`), specific files, or the entire codebase.
2. **Read the code carefully** - Understand the intent, not just the syntax. Read related files for context.
3. **Check each category** below and report findings.
4. **Provide actionable feedback** - For each issue, explain the problem, why it matters, and suggest a fix with code.

## Review Categories

### Correctness
- Logic errors, off-by-one bugs, null/undefined handling
- Edge cases: empty inputs, boundary values, concurrent access
- Error handling: are errors caught, logged, and surfaced properly?

### Security
- Input validation and sanitization
- SQL injection, XSS, CSRF vulnerabilities
- Hardcoded secrets, credentials, or API keys
- Proper authentication and authorization checks

### Performance
- N+1 queries, unnecessary loops, redundant computations
- Missing indexes for database queries
- Large allocations, memory leaks, unclosed resources

### Maintainability
- Clear naming, consistent style, appropriate abstractions
- Dead code, commented-out code, TODO items
- Functions that are too long or do too many things
- Missing or misleading documentation

### Testing
- Are new code paths covered by tests?
- Are edge cases tested?
- Do tests actually assert meaningful behavior?

## Output Format

Organize findings by severity:

- **Critical** - Bugs, security vulnerabilities, data loss risks
- **Warning** - Performance issues, potential bugs, poor patterns
- **Suggestion** - Style improvements, better approaches, minor cleanups

For each finding, include:
1. File and line number
2. Description of the issue
3. Suggested fix with code snippet

## Rules

- Be specific: point to exact lines, not vague areas
- Praise good patterns you notice -- reviews should not be only negative
- Distinguish opinion from objective issues
- If the code is clean, say so -- do not invent problems
