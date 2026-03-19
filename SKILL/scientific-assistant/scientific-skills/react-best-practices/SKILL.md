---
name: vercel-react-best-practices
description: >
  React and Next.js performance optimization guidelines from Vercel Engineering.
  Use this skill when writing, reviewing, or refactoring React/Next.js code to ensure
  optimal performance patterns. Triggers on tasks involving React components, Next.js pages,
  data fetching, bundle optimization, or performance improvements.
metadata:
  author: vercel
  version: "1.0.0"
license: MIT
---

# React Best Practices

React and Next.js performance optimization guidelines from Vercel Engineering. Contains 64 rules across 8 categories, prioritized by impact to guide automated refactoring and code generation.

## When to Use

Reference these guidelines when:

- Writing new React components or Next.js pages
- Implementing data fetching
- Reviewing code for performance issues
- Refactoring existing code
- Optimizing bundle size or load times

## Rules Overview

Rules are prioritized by impact from critical (eliminating waterfalls, reducing bundle size) to incremental (advanced patterns). Each rule includes detailed explanations, real-world examples comparing incorrect vs. correct implementations, and specific impact metrics.

### Categories (by impact level)

1. **Async Patterns** (CRITICAL) — Eliminate waterfalls, the #1 performance killer. Each sequential `await` adds full network latency. Eliminating them yields the largest gains.
2. **Bundle Size** (CRITICAL) — Reduce bundle size through proper imports and tree-shaking.
3. **Server-Side Caching** (HIGH) — Optimize server-side data caching strategies.
4. **Client-Side Data Fetching** (HIGH) — Efficient client-side data management.
5. **Re-render Optimization** (MEDIUM) — Minimize unnecessary component re-renders.
6. **Rendering Performance** (MEDIUM) — Improve rendering efficiency.
7. **Advanced Patterns** (LOW) — Sophisticated optimization techniques.
8. **JavaScript Efficiency** (LOW) — Micro-optimizations for JavaScript execution.

## Key Rules

### Waterfalls

Waterfalls are the #1 performance killer. Each sequential `await` adds full network latency, and eliminating them yields the largest gains.

### Caching

`React.cache()` only works within one request. For data shared across sequential requests, use an LRU cache.

### Server/Client Boundary

The React Server/Client boundary serializes all object properties into strings and embeds them in the HTML response. This serialized data directly impacts page weight and load time — only pass fields the client actually uses.

### Library Optimization

Libraries commonly affected by bundle bloat include:

- `lucide-react`
- `@mui/material`
- `@mui/icons-material`
- `@tabler/icons-react`
- `react-icons`
- `@headlessui/react`
- `@radix-ui/react-*`
- `lodash`
- `ramda`
- `date-fns`
- `rxjs`
- `react-use`

## Full Guidelines

For the complete set of 64 rules with code examples, refer to the companion `AGENTS.md` file which contains the full compiled ruleset organized by category and impact level.
