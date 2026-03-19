---
name: React Best Practices
description: React and Next.js performance optimization guidelines from Vercel Engineering
version: 1.0.0
tags: [react, nextjs, frontend, performance, vercel]
---

# React & Next.js Best Practices

## Component Design

### 1. Server Components First
- Default to React Server Components (RSC) for all new components
- Only add `'use client'` when you need interactivity, browser APIs, or React hooks
- Keep client components as leaf nodes in the component tree
- Never import server-only modules in client components

### 2. Component Composition
- Prefer composition over prop drilling: use `children` and render props
- Extract shared logic into custom hooks, not wrapper components
- Keep components under 200 lines; split into smaller pieces if larger
- Use compound component pattern for related UI elements

### 3. State Management
- Use `useState` for local UI state only
- Use `useReducer` for complex state logic with multiple sub-values
- Avoid global state for server-fetchable data — use RSC or React Query
- Colocate state as close to where it's used as possible

## Performance Rules

### 4. Rendering Optimization
- Memoize expensive computations with `useMemo`
- Memoize callback functions passed to children with `useCallback`
- Use `React.memo()` only when profiling shows re-render issues
- Never create components inside render functions

### 5. Code Splitting
- Use `next/dynamic` for heavy components not needed on initial load
- Lazy load below-the-fold content
- Use `Suspense` boundaries around lazy-loaded components
- Split route-level code with Next.js App Router layouts

### 6. Image & Media
- Always use `next/image` instead of `<img>`
- Set explicit `width` and `height` to prevent layout shift
- Use `priority` for above-the-fold hero images
- Use `loading="lazy"` for below-the-fold images

### 7. Data Fetching
- Fetch data in Server Components, not in `useEffect`
- Use `fetch()` with proper `cache` and `revalidate` options
- Implement optimistic updates for mutations
- Use `Suspense` for streaming and progressive rendering

## Next.js Specific

### 8. Routing & Layouts
- Use App Router (`app/`) for all new projects
- Place shared UI in `layout.tsx`, not duplicated across pages
- Use `loading.tsx` for route-level loading states
- Use `error.tsx` for route-level error boundaries
- Use `not-found.tsx` for 404 pages

### 9. Metadata & SEO
- Export `metadata` object or `generateMetadata()` from pages
- Include `title`, `description`, `openGraph`, and `twitter` metadata
- Use `robots.txt` and `sitemap.xml` via App Router conventions
- Add structured data (JSON-LD) for rich search results

### 10. API Routes
- Use Route Handlers (`route.ts`) in App Router
- Validate request bodies with Zod
- Return proper HTTP status codes
- Use Edge Runtime for low-latency endpoints

## Styling

### 11. CSS Best Practices
- Use CSS Modules or Tailwind CSS (avoid CSS-in-JS in RSC)
- Define design tokens as CSS custom properties
- Use `clsx` or `cn()` for conditional class names
- Keep responsive breakpoints consistent

## TypeScript

### 12. Type Safety
- Enable `strict: true` in `tsconfig.json`
- Type component props with interfaces, not `type` aliases for objects
- Use `satisfies` operator for type-safe constants
- Avoid `any` — use `unknown` and narrow with type guards

## Testing

### 13. Testing Strategy
- Write integration tests for user flows with Testing Library
- Test Server Components with their data dependencies
- Use Playwright for critical E2E paths
- Mock external services, not internal modules

## Accessibility

### 14. A11y Requirements
- Use semantic HTML elements (`button`, `nav`, `main`, `article`)
- Add `aria-label` to icon-only buttons
- Ensure keyboard navigation works for all interactive elements
- Maintain 4.5:1 contrast ratio for text
- Test with screen readers (VoiceOver, NVDA)
