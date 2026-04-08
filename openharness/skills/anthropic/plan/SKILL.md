---
name: plan
description: Design implementation plans for complex tasks. TRIGGER when the user asks to plan, architect, design, or break down a complex feature, project, or task.
---
# Plan

Create structured implementation plans that break complex tasks into clear, actionable steps.

## Steps

1. **Understand the goal** - Clarify what the user wants to achieve. Ask questions if the requirements are ambiguous.
2. **Assess the current state** - Explore the existing codebase to understand:
   - Project structure and conventions
   - Existing patterns and abstractions
   - Related code that will be affected
   - Available dependencies and tools
3. **Identify constraints** - Note technical constraints, backward compatibility requirements, deadlines, or other limitations.
4. **Break down the work** - Decompose into small, independently testable steps. Each step should:
   - Have a clear deliverable
   - Be completable in a single focused session
   - Build on previous steps
5. **Identify risks** - Call out unknowns, potential blockers, and areas needing research.
6. **Present the plan** - Use the output format below.

## Output Format

```markdown
## Goal
{One sentence summary of what we are building}

## Current State
{Brief assessment of relevant existing code and infrastructure}

## Plan

### Step 1: {Title}
- **What**: {Description of what to do}
- **Files**: {Files to create or modify}
- **Tests**: {How to verify this step works}

### Step 2: {Title}
...

## Risks & Open Questions
- {Risk or question 1}
- {Risk or question 2}

## Out of Scope
- {Things explicitly not included in this plan}
```

## Rules

- Plans should be specific to the codebase, not generic advice
- Reference actual files, functions, and patterns from the project
- Keep steps small enough to be reviewable -- no "implement the entire feature" steps
- Include testing strategy for each step
- Call out what is NOT in scope to prevent scope creep
- If the user asks to execute the plan, work through it step by step, confirming after each step
