# /code-review

Perform an automated, multi-agent code review on a pull request or branch.

## Usage

```
/code-review <PR_NUMBER_OR_BRANCH>
```

## Arguments

- `PR_NUMBER_OR_BRANCH` (required): A pull request number (e.g. `142`) or a branch name (e.g. `feature/auth-refactor`). When a PR number is given, the diff is fetched from the remote. When a branch name is given, it is compared against the default branch (`main` or `master`).

## Workflow

### Step 1: Resolve the target

1. If the argument is a number, treat it as a PR number. Run `gh pr diff <number>` to retrieve the diff and `gh pr view <number> --json title,body,commits,files` to get PR metadata.
2. If the argument is a branch name, run `git diff $(git merge-base HEAD main)..HEAD` (fall back to `master` if `main` does not exist) to get the diff and `git log --oneline $(git merge-base HEAD main)..HEAD` for commit history.
3. Collect the list of changed files and their full contents after the change using `git show HEAD:<path>` for each file.

### Step 2: Launch 5 parallel review agents

Dispatch the following agents simultaneously using subagents. Pass each agent the full diff, the list of changed files, and the file contents.

#### Agent 1 -- Convention Compliance (convention-checker)

Check every changed file against the project's CLAUDE.md, .editorconfig, linter configs (.eslintrc, pyproject.toml, etc.), and any style guides found in the repo. Report violations with file, line, rule, and suggested fix.

#### Agent 2 -- Bug Detection (bug-detector)

Analyze the diff for potential bugs including: null/undefined dereferences, off-by-one errors, race conditions, unchecked error returns, resource leaks, incorrect boundary conditions, type mismatches, and security vulnerabilities (injection, XSS, SSRF, path traversal).

#### Agent 3 -- Historical Context

Use `git log` and `git blame` on changed files to understand:
- Why the code being modified was originally written
- Whether this change reverts or conflicts with recent intentional changes
- Whether the same area has been a source of repeated bugs (churn analysis)

Report any historically relevant context the PR author and reviewers should be aware of.

#### Agent 4 -- PR Description Quality

Evaluate the PR title, body, and commit messages for:
- Clear summary of *what* changed and *why*
- Links to related issues or tickets
- Testing instructions or test plan
- Breaking change callouts
- Completeness relative to the actual diff (does the description match the code?)

Provide a quality score (0-100) and specific suggestions to improve the description.

#### Agent 5 -- Readability & Documentation (readability-reviewer)

Review code for:
- Function/variable naming clarity
- Appropriate use of comments (not too few, not too many)
- Complex logic that lacks explanation
- Missing or outdated docstrings
- Overly long functions that should be decomposed
- Magic numbers or unclear constants

### Step 3: Aggregate and filter

Collect findings from all 5 agents. Each finding must have:

```json
{
  "agent": "<agent_name>",
  "file": "<file_path>",
  "line": <line_number_or_null>,
  "severity": "critical" | "warning" | "suggestion",
  "confidence": <0-100>,
  "title": "<short_title>",
  "detail": "<explanation>",
  "suggestion": "<suggested_fix_or_action>"
}
```

Filter out findings with `confidence < 80` to reduce noise.

Sort the remaining findings by severity (critical first, then warning, then suggestion), and within each severity by confidence descending.

### Step 4: Output the review report

Print the report in the following format:

```
## Code Review Report

**Target:** PR #<number> | branch `<name>`
**Files reviewed:** <count>
**Findings:** <count_critical> critical, <count_warning> warnings, <count_suggestion> suggestions

---

### Critical

#### [<agent>] <title>
**File:** `<file>` line <line>
**Confidence:** <confidence>%

<detail>

**Suggested fix:**
<suggestion>

---

### Warnings

...

### Suggestions

...

---

### PR Description Assessment
**Score:** <score>/100
<summary_of_pr_description_feedback>

### Historical Notes
<summary_of_historical_context_findings>
```

If there are no critical findings, congratulate the author and note that the review found no blocking issues.

## Notes

- If a CLAUDE.md file exists in the repo root, the convention-checker agent must read it and use it as the primary source of coding conventions.
- If linter or formatter configs exist, the convention-checker should reference them but not re-run the tools (the author is expected to have run them).
- The bug-detector should focus on logic errors that static analysis tools typically miss -- it should not duplicate linter output.
- Keep the report actionable: every finding must include a concrete suggestion.
