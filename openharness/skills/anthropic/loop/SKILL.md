---
name: loop
description: Run a prompt or command on a recurring interval. TRIGGER when the user asks to repeat a task on a schedule, poll for status, or run something periodically (e.g., "check every 5 minutes", "keep running").
---
# Loop

Run a prompt or slash command on a recurring interval.

## Usage

```
/loop [interval] [command or prompt]
```

- **interval**: Duration like `5m`, `30s`, `1h`. Defaults to `10m` if omitted.
- **command**: A slash command (e.g., `/review`) or a natural language prompt.

## Examples

```
/loop 5m /review          # Review code every 5 minutes
/loop 30s git status       # Check git status every 30 seconds
/loop 1h check deployment  # Monitor deployment hourly
/loop build and test       # Build and test every 10 minutes (default)
```

## Steps

1. **Parse the arguments** - Extract the interval and the command/prompt from the user's input.
2. **Validate the interval** - Ensure it is a reasonable duration (minimum 10 seconds, maximum 24 hours).
3. **Execute the loop** - Run the command or prompt, then wait for the interval, then repeat.
4. **Report results** - After each iteration, summarize what changed or what was found.
5. **Stop conditions** - The loop stops when:
   - The user asks to stop
   - A critical error occurs
   - The task is complete (e.g., deployment succeeded)

## Rules

- Always confirm the loop parameters before starting
- Report meaningful diffs between iterations, not full output each time
- If nothing changed since the last iteration, say so briefly
- Include a clear way for the user to stop the loop
- Be mindful of rate limits and resource usage for short intervals
