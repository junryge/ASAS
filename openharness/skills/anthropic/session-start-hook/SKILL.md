---
name: session-start-hook
description: Create startup hooks for project initialization. TRIGGER when the user asks to set up a session hook, project init script, onboarding automation, or Claude Code startup configuration.
---
# Session Start Hook

Create and manage hooks that run automatically when a new Claude Code session starts in a project.

## Steps

1. **Identify the project root** - Look for `.claude/` directory, or `package.json`, `pyproject.toml`, `Cargo.toml`, or `.git/` to determine the project root.
2. **Check for existing hooks** - Look for `.claude/hooks/` or `.claude/session-start` files that may already exist.
3. **Determine what the hook should do** - Common session-start tasks include:
   - Loading project context (architecture docs, coding standards)
   - Checking environment setup (required tools, env vars)
   - Displaying recent changes or open TODOs
   - Running health checks (dependency status, test results)
4. **Create the hook** - Write a hook configuration that runs on session start.
5. **Test the hook** - Verify it runs correctly and does not block or slow down session startup.

## Hook Configuration

Session start hooks live in the project's `.claude/` configuration directory:

```json
// .claude/settings.json
{
  "hooks": {
    "session-start": [
      {
        "command": "cat ARCHITECTURE.md",
        "description": "Load project architecture context"
      },
      {
        "command": "git log --oneline -5",
        "description": "Show recent commits"
      }
    ]
  }
}
```

## Common Hook Examples

### Project context loader
```bash
#!/bin/bash
# .claude/hooks/session-start.sh
echo "=== Project: $(basename $(pwd)) ==="
echo "=== Recent Changes ==="
git log --oneline -5
echo "=== Open TODOs ==="
grep -r "TODO" src/ --include="*.ts" -l 2>/dev/null | head -10
echo "=== Test Status ==="
npm test --silent 2>&1 | tail -3
```

### Environment validator
```bash
#!/bin/bash
# Check required tools
for cmd in node npm docker; do
  if ! command -v $cmd &>/dev/null; then
    echo "WARNING: $cmd is not installed"
  fi
done

# Check required env vars
for var in DATABASE_URL API_KEY; do
  if [ -z "${!var}" ]; then
    echo "WARNING: $var is not set"
  fi
done
```

## Rules

- Hooks must be fast -- keep execution under 5 seconds to avoid delaying session startup
- Never include secrets or credentials in hook scripts
- Hooks should be idempotent (safe to run multiple times)
- Use informational output only -- hooks should not modify project state
- If a hook fails, report the failure but do not block the session from starting
