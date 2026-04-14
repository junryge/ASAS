---
name: debugging
description: Systematic debugging methodology with defense-in-depth, root-cause tracing, and verification
---

# Debugging Skills

Comprehensive debugging methodology combining multiple approaches.

## defense-in-depth
name: Defense-in-Depth Validation
description: Validate at every layer data passes through to make bugs impossible
when_to_use: when invalid data causes failures deep in execution, requiring validation at multiple system layers
version: 1.1.0
languages: all

## root-cause-tracing
name: Root Cause Tracing
description: Systematically trace bugs backward through call stack to find original trigger
when_to_use: when errors occur deep in execution and you need to trace back to find the original trigger
version: 1.1.0
languages: all

## systematic-debugging
name: Systematic Debugging
description: Four-phase debugging framework that ensures root cause investigation before attempting fixes. Never jump to solutions.
when_to_use: when encountering any bug, test failure, or unexpected behavior, before proposing fixes
version: 2.1.0
languages: all

## verification-before-completion
name: Verification Before Completion
description: Run verification commands and confirm output before claiming success
when_to_use: when about to claim work is complete, fixed, or passing, before committing or creating PRs
version: 1.1.0
languages: all
