---
name: dependency-update
description: Update and audit package dependencies. TRIGGER when the user asks to update dependencies, upgrade packages, check for outdated libraries, or audit dependency vulnerabilities.
---
# Dependency Update

Update, audit, and manage package dependencies safely.

## Steps

1. **Detect the package manager** - Identify the project's ecosystem:
   - `package.json` / `package-lock.json` -- npm/yarn/pnpm
   - `pyproject.toml` / `requirements.txt` -- pip/poetry/uv
   - `Cargo.toml` -- cargo
   - `go.mod` -- go modules
   - `Gemfile` -- bundler
2. **Check current state** - List outdated and vulnerable dependencies.
3. **Plan updates** - Distinguish between patch, minor, and major updates. Assess risk.
4. **Apply updates** - Update dependencies, starting with the safest (patches first).
5. **Test** - Run the test suite after each batch of updates to catch regressions.
6. **Audit security** - Run security audit tools to check for known vulnerabilities.

## Commands by Ecosystem

### Node.js (npm)
```bash
# Check outdated
npm outdated

# Update within semver ranges
npm update

# Update a specific package to latest
npm install <package>@latest

# Security audit
npm audit
npm audit fix

# Interactive upgrade tool
npx npm-check-updates -i
```

### Python (pip / poetry / uv)
```bash
# pip: check outdated
pip list --outdated

# pip: update specific package
pip install --upgrade <package>

# poetry: check outdated
poetry show --outdated

# poetry: update within constraints
poetry update

# poetry: update specific package to latest
poetry add <package>@latest

# uv: update
uv lock --upgrade

# Security audit
pip-audit
safety check -r requirements.txt
```

### Go
```bash
# Check for available updates
go list -m -u all

# Update all dependencies
go get -u ./...

# Update specific dependency
go get -u github.com/pkg/errors

# Tidy up go.sum
go mod tidy

# Vulnerability check
govulncheck ./...
```

### Rust
```bash
# Check outdated
cargo outdated

# Update within semver ranges
cargo update

# Security audit
cargo audit
```

## Update Strategy

### Safe order of operations
1. **Patch updates first** (1.2.3 -> 1.2.4) - Bug fixes only, lowest risk
2. **Minor updates** (1.2.3 -> 1.3.0) - New features, backward compatible
3. **Major updates** (1.2.3 -> 2.0.0) - Breaking changes, highest risk; read changelogs

### For each major update
1. Read the changelog and migration guide
2. Check for breaking changes that affect your code
3. Update one major dependency at a time
4. Run tests after each major update
5. Fix any breaking changes before proceeding

## Rules

- ALWAYS run tests after updating dependencies
- Update one major version at a time, not all at once
- Read changelogs for major version bumps before updating
- Commit dependency updates separately from feature changes
- If a lockfile exists (`package-lock.json`, `poetry.lock`, `Cargo.lock`), always commit it with the update
- Do not remove dependencies unless the user explicitly asks
- If an update breaks tests, revert it and report the issue
