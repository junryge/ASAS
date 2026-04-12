---
name: skill-creator
description: >
  Create high-quality skills for Claude Code. Use when users want to create a skill
  from scratch, update or optimize an existing skill, run evals to test a skill,
  or benchmark skill performance with variance analysis. Make sure to use this skill
  whenever the user mentions creating, building, developing, or improving a skill,
  even if they don't explicitly say "skill-creator".
license: Complete terms in LICENSE.txt
---

# Skill Creator

Guide the full skill development lifecycle: intent capture, drafting, test case creation, evaluation, and iteration based on user feedback.

## Skill Structure

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/   - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/    - Files used in output (templates, icons, fonts)
```

## Creating a New Skill

When creating a new skill from scratch, always run the `init_skill.py` script:

```bash
python -m scripts.init_skill <skill-name> --path <output-directory>
```

This generates a new template skill directory that automatically includes everything a skill requires. Skip this step only if the skill being developed already exists and iteration or packaging is needed.

## SKILL.md Format

### YAML Frontmatter

The YAML frontmatter must appear at the very beginning of SKILL.md, delimited by `---` markers.

**Required fields:**
- **`name`**: Lowercase letters, digits, hyphens only (regex: `^[a-z0-9-]+$`). Cannot start or end with a hyphen. Cannot contain consecutive hyphens. Maximum length: 64 characters.
- **`description`**: The primary mechanism that determines whether Claude invokes a skill. Include both what the skill does AND specific triggers/contexts for when to use it.

**Optional fields:**
- `license`
- `allowed-tools`
- `metadata` (arbitrary string-to-string key-value mappings)
- `compatibility` (max 500 characters)

### Markdown Content

The body contains instructions Claude follows when the skill is invoked. Keep SKILL.md under 500 lines. Move detailed reference material to separate files in `references/`.

## Bundled Resource Types

- **scripts/**: Python scripts, shell scripts, or any executable code for automation, data processing, or specific operations. Scripts may be executed without loading into context.
- **references/**: Documentation and reference material loaded into context to inform Claude's process. Appropriate for in-depth documentation, API references, database schemas, comprehensive guides. For large reference files (>300 lines), include a table of contents.
- **assets/**: Files not loaded into context but used within output. Appropriate for templates, boilerplate code, document templates, images, icons, fonts.

## Writing Guidelines

- Use the imperative form in instructions.
- Reference files clearly from SKILL.md with guidance on when to read them.
- Descriptions should be "pushy" — explicitly list trigger contexts so Claude reliably invokes the skill.
- Remember that the skill is being created for another instance of Claude to use.

## Description Optimization

After creating or improving a skill, offer to optimize the description for better triggering accuracy. Create 20 eval queries — a mix of should-trigger and should-not-trigger.

## Evaluation & Benchmarking

### Running Evals

Run parallel test cases with and without the skill to measure impact, capturing timing and token usage for quantitative comparison.

### Grading

Grade each run by spawning a grader subagent that reads `agents/grader.md` and evaluates each assertion against the outputs. Save results to `grading.json` in each run directory. The expectations array must use the fields `text`, `passed`, and `evidence`.

### Aggregation

Aggregate into benchmark by running:

```bash
python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <n>
```

This produces `benchmark.json` and `benchmark.md` with pass_rate, time, and tokens for each configuration, with mean +/- stddev and the delta.

## Packaging

Once the skill is ready, package it into a distributable zip file. The packaging process automatically validates the skill first and creates a zip file named after the skill that includes all files and maintains the proper directory structure for distribution.

## Security

Skills must not contain malware, exploit code, or any content that could compromise system security. Do not create misleading skills or skills designed to facilitate unauthorized access, data exfiltration, or other malicious activities.

## Audience Awareness

The skill creator may be used by people across a wide range of familiarity with coding jargon, from beginners opening terminals for the first time to experienced developers. Pay attention to context cues to understand how to phrase your communication.
