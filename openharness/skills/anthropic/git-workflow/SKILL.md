---
name: git-workflow
description: Git branch strategies, merge, rebase, and cherry-pick. TRIGGER when the user asks about git branching, merge conflicts, rebase, cherry-pick, git flow, or branch management.
---
# Git Workflow

Manage git branching strategies, merges, rebases, and advanced git operations.

## Steps

1. **Understand the current state** - Run `git status`, `git branch -a`, and `git log --oneline --graph -20` to understand the repository state.
2. **Identify the goal** - Determine what the user needs: create a branch, merge, rebase, resolve conflicts, cherry-pick, or set up a branching strategy.
3. **Execute the operation** - Perform the git operation with clear explanations.
4. **Verify the result** - Check `git log --oneline --graph -10` and `git status` to confirm success.

## Common Operations

### Branch Management
```bash
# Create and switch to a feature branch
git checkout -b feature/user-auth

# List all branches (local and remote)
git branch -a

# Delete a merged branch
git branch -d feature/old-branch

# Delete a remote branch
git push origin --delete feature/old-branch

# Rename current branch
git branch -m new-name
```

### Merging
```bash
# Merge feature into main (merge commit)
git checkout main
git merge feature/user-auth

# Merge with no fast-forward (preserves branch history)
git merge --no-ff feature/user-auth
```

### Rebasing
```bash
# Rebase feature branch onto latest main
git checkout feature/user-auth
git rebase main

# If conflicts occur during rebase:
# 1. Fix conflicts in the files
# 2. git add <resolved-files>
# 3. git rebase --continue
# To abort: git rebase --abort
```

### Cherry-Pick
```bash
# Apply a specific commit to current branch
git cherry-pick abc1234

# Cherry-pick without committing (stage changes only)
git cherry-pick --no-commit abc1234

# Cherry-pick a range of commits
git cherry-pick abc1234..def5678
```

### Conflict Resolution
```bash
# See which files have conflicts
git status

# After manually resolving conflicts in each file:
git add <resolved-file>
git commit  # or git rebase --continue if rebasing
```

## Branching Strategies

### GitHub Flow (simple, recommended for most projects)
- `main` is always deployable
- Create feature branches from `main`
- Open pull requests for review
- Merge to `main` after approval
- Deploy from `main`

### Git Flow (for scheduled releases)
- `main` -- production releases only
- `develop` -- integration branch
- `feature/*` -- branch from `develop`
- `release/*` -- branch from `develop` for release prep
- `hotfix/*` -- branch from `main` for urgent fixes

## Rules

- NEVER force-push to `main` or `master` unless the user explicitly requests it
- Always check `git status` before and after operations
- When resolving merge conflicts, understand both sides before choosing
- Prefer `git rebase` for local feature branches, `git merge` for shared branches
- Before destructive operations (reset, force-push), warn the user and confirm
- If a rebase or merge goes wrong, use `git rebase --abort` or `git merge --abort` to recover
