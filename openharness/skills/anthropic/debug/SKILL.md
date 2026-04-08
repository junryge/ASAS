---
name: debug
description: Diagnose and fix bugs systematically. TRIGGER when the user reports a bug, error, crash, unexpected behavior, or asks to debug or troubleshoot an issue.
---
# Debug

Systematically diagnose and fix bugs using a structured approach.

## Steps

1. **Reproduce the issue** - Get the exact error message, stack trace, or unexpected behavior. Run the failing command or test to see it firsthand.
2. **Understand the expected behavior** - Ask the user what should happen versus what is happening.
3. **Form hypotheses** - Based on the error and code, list 2-3 likely causes ranked by probability.
4. **Investigate** - Read the relevant source files. Trace the execution path from entry point to failure. Check:
   - Stack traces and error messages for exact file/line info
   - Recent changes: `git log --oneline -20` and `git diff HEAD~5`
   - Configuration files and environment variables
   - Dependencies and version mismatches
5. **Isolate the root cause** - Narrow down by:
   - Adding targeted logging or print statements
   - Running with minimal reproduction cases
   - Checking if the issue exists on other branches: `git stash && git checkout main`
   - Binary search through history with `git bisect`
6. **Fix the bug** - Apply the minimal correct fix. Do not refactor unrelated code.
7. **Verify the fix** - Run the failing test or reproduce steps again. Run the full test suite to check for regressions.
8. **Explain** - Tell the user what caused the bug and why the fix works.

## Common Debugging Patterns

### Stack Trace Analysis
- Read from bottom to top for the root cause
- Focus on frames in the project's own code, not library internals
- Look for the transition point where project code calls into library code

### Log-Based Debugging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Variable state: %s", vars(obj))
```

### Git Bisect
```bash
git bisect start
git bisect bad          # current commit is broken
git bisect good abc123  # this commit was working
# Git checks out middle commits; test each one
git bisect reset        # when done
```

## Rules

- Always reproduce the bug before attempting a fix
- Fix the root cause, not the symptom
- Make the smallest change that fixes the issue
- Verify no regressions after the fix
- If unsure of the cause, say so and suggest further investigation steps
