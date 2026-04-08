---
name: update-config
description: Configure settings via settings.json. TRIGGER when the user asks to update configuration, change settings, modify preferences, or configure Claude Code project settings.
---
# Update Config

Manage project and user configuration through settings files.

## Steps

1. **Identify the config scope** - Determine whether the user wants to change:
   - **Project settings**: `.claude/settings.json` (checked into repo, shared with team)
   - **User settings**: `~/.claude/settings.json` (personal, not shared)
   - **App-specific config**: `package.json`, `tsconfig.json`, `.eslintrc`, etc.
2. **Read the current config** - Read the existing settings file to understand current values.
3. **Make the change** - Update the specific field the user requested. Preserve all other existing settings.
4. **Validate the config** - Ensure the JSON/YAML/TOML is valid after editing. Check for common mistakes like trailing commas or missing quotes.
5. **Confirm the change** - Show the user what was changed (before vs after).

## Claude Code Settings

### Project settings (`.claude/settings.json`)
```json
{
  "permissions": {
    "allow": [
      "Bash(npm test)",
      "Bash(npm run lint)",
      "Bash(git status)",
      "Bash(git diff)"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(git push --force)"
    ]
  },
  "hooks": {
    "session-start": [
      {
        "command": "cat ARCHITECTURE.md",
        "description": "Load architecture context"
      }
    ]
  }
}
```

### User settings (`~/.claude/settings.json`)
```json
{
  "preferences": {
    "theme": "dark",
    "verbose": false
  },
  "permissions": {
    "allow": [
      "Bash(git status)"
    ]
  }
}
```

## Common Config Operations

### Add a permission
```json
// Add to .claude/settings.json -> permissions.allow
"Bash(npm run build)"
```

### Update nested values
When editing JSON configs, always read the full file first, then make surgical edits to preserve structure and comments.

### Validate JSON
```bash
# Check JSON syntax
python3 -c "import json; json.load(open('.claude/settings.json'))"
# or
node -e "JSON.parse(require('fs').readFileSync('.claude/settings.json', 'utf8'))"
```

## Rules

- ALWAYS read the existing config file before making changes
- NEVER overwrite the entire file -- make targeted edits to preserve existing settings
- Validate JSON/YAML syntax after every edit
- If the config file does not exist, create it with the minimal required structure
- Do not modify config files outside the project unless the user explicitly asks for user-level settings
- Back up complex configs before making large changes: `cp settings.json settings.json.bak`
