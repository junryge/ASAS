# /code-review

Perform a comprehensive automated code review on a pull request or branch.

## Usage

```
/code-review <PR_NUMBER_OR_BRANCH>
```

## Arguments

- `PR_NUMBER_OR_BRANCH` (required): Either a GitHub pull request number (e.g., `142`) or a branch name (e.g., `feature/add-auth`). When a branch name is given, the diff is computed against the repository's default branch.

## Workflow

### Step 1: Resolve the target diff

1. If the argument is a number, fetch the PR metadata using `gh pr view <number>` to get the base branch, head branch, title, and body.
2. If the argument is a branch name, determine the default branch with `git rev-parse --abbrev-ref origin/HEAD` and use that as the base.
3. Generate the full diff: `git diff <base>...<head>`.
4. Collect the list of changed files: `git diff --name-only <base>...<head>`.

### Step 2: Gather repository context

1. Read the project's `CLAUDE.md` file (if present) to understand documented conventions, coding standards, and project-specific rules.
2. Read any linter or formatter configuration files (`.eslintrc*`, `pyproject.toml`, `biome.json`, `.prettierrc*`, `rustfmt.toml`, etc.) to understand enforced style rules.
3. For each changed file, retrieve the last 5 commits touching that file using `git log -5 --oneline -- <file>` so agents have historical context.

### Step 3: Launch 5 parallel review agents

Dispatch the following agents concurrently using the Agent tool. Pass each agent the full diff, the list of changed files, and the repository context gathered above.

#### Agent 1 -- Convention Compliance

Use the `convention-checker` agent. Ask it to:
- Compare every changed file against the rules in `CLAUDE.md` and any linter configs.
- Flag violations of naming conventions, import ordering, file structure, module boundaries, and any project-specific rules documented in `CLAUDE.md`.
- For each finding, provide: file path, line range, rule violated, severity score (0-100), and a suggested fix.

#### Agent 2 -- Bug Detection

Use the `bug-detector` agent. Ask it to:
- Analyze the diff for potential bugs, logic errors, off-by-one mistakes, null/undefined dereferences, race conditions, resource leaks, unhandled error paths, and security vulnerabilities.
- For each finding, provide: file path, line range, bug category, severity score (0-100), explanation of the failure scenario, and a suggested fix.

#### Agent 3 -- Historical Context

Launch a sub-agent to:
- For each changed file, review the recent commit history (gathered in Step 2) and any open issues or recent PRs that touched the same files.
- Identify whether any change reverts a previous fix, reintroduces a known issue, or conflicts with ongoing work on another branch.
- For each finding, provide: file path, related commit or PR reference, severity score (0-100), and an explanation.

#### Agent 4 -- PR Description Quality

Launch a sub-agent to:
- Evaluate the pull request title and body (if a PR number was provided; skip if reviewing a branch directly).
- Check that the description explains *why* the change was made, not just *what* changed.
- Verify the presence of a test plan, links to related issues, and any required sections defined in `CLAUDE.md` or a PR template.
- Assign a severity score (0-100) for each missing or inadequate element.

#### Agent 5 -- Code Comments and Readability

Use the `readability-reviewer` agent. Ask it to:
- Assess the readability of changed code: function length, nesting depth, naming clarity, and cognitive complexity.
- Check that public APIs, complex algorithms, and non-obvious logic have adequate comments or docstrings.
- Identify dead code, commented-out code, and TODO/FIXME/HACK markers that should be tracked as issues.
- For each finding, provide: file path, line range, category, severity score (0-100), and a suggested improvement.

### Step 4: Aggregate and filter findings

1. Collect all findings from the 5 agents.
2. Deduplicate findings that refer to the same file and line range with overlapping descriptions.
3. Filter out findings with a severity score below 80 to focus on the most impactful issues.
4. Sort remaining findings by severity (descending), then by file path.

### Step 5: Generate the review report

Output a structured review report in the following format:

```
## Code Review Report

**Target:** PR #<number> / branch `<name>`
**Files reviewed:** <count>
**Total findings:** <count> (after filtering, severity >= 80)

### Critical Findings (severity >= 90)

| # | File | Lines | Category | Agent | Score | Summary |
|---|------|-------|----------|-------|-------|---------|
| 1 | ... | ... | ... | ... | ... | ... |

<For each critical finding, include a detailed explanation and suggested fix below the table.>

### Important Findings (severity 80-89)

| # | File | Lines | Category | Agent | Score | Summary |
|---|------|-------|----------|-------|-------|---------|
| 1 | ... | ... | ... | ... | ... | ... |

### PR Description Assessment

<Summary from Agent 4, or "N/A -- branch review" if no PR was provided.>

### Convention Compliance Summary

<High-level summary from Agent 1: how well the PR follows project conventions.>

### Recommendations

<Bulleted list of top 3-5 actionable recommendations, ordered by impact.>
```

### Step 6: Offer follow-up actions

After presenting the report, ask the user if they would like to:
1. Post the review as inline comments on the GitHub PR (using `gh api` to create a review).
2. Auto-fix convention violations where safe (formatting, import ordering, etc.).
3. Deep-dive into any specific finding for more analysis.
4. Re-run the review after changes have been made.
