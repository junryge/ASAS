---
name: commit
description: Create clean git commits with proper messages. TRIGGER when the user asks to commit changes, create a commit, or save their work to git.
---
# Git Commit

Create well-structured git commits with clear, conventional commit messages.

## Steps

1. **Check the current state** - Run `git status` and `git diff --staged` to understand what is being committed. If nothing is staged, run `git diff` to see unstaged changes.
2. **Review recent history** - Run `git log --oneline -10` to understand the project's commit message style and conventions.
3. **Stage changes selectively** - Prefer `git add <specific-files>` over `git add -A`. Never stage `.env`, credentials, or secrets. Ask the user if staging scope is unclear.
4. **Draft a commit message** - Follow Conventional Commits or match the repo's existing style:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for restructuring without behavior change
   - `docs:` for documentation
   - `test:` for adding/updating tests
   - `chore:` for tooling, deps, config
5. **Commit** - Use a heredoc for multi-line messages:
   ```bash
   git commit -m "$(cat <<'EOF'
   feat: add user profile endpoint

   Implements GET /api/users/:id with pagination support.
   Includes input validation and proper error responses.
   EOF
   )"
   ```
6. **Verify** - Run `git status` and `git log -1` to confirm the commit succeeded.

## Commit Message Guidelines

- First line: imperative mood, under 72 characters, no period at end
- Blank line before body (if body is needed)
- Body: explain the "why", not the "what" (the diff shows the what)
- Reference issue numbers when applicable: `Closes #42`

## Rules

- NEVER amend a previous commit unless the user explicitly asks for it
- NEVER use `--no-verify` to skip hooks unless the user explicitly requests it
- NEVER commit files that likely contain secrets (`.env`, `credentials.json`, API keys)
- If a pre-commit hook fails, fix the issue and create a NEW commit
- Do not force-push unless explicitly requested
