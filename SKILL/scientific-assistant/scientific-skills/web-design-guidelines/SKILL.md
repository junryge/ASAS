---
name: Web Design Guidelines
description: Comprehensive web interface design rules covering accessibility, performance, and UX
version: 1.0.0
tags: [design, ui, ux, accessibility, web]
---

# Web Design Guidelines

## Layout & Spacing

### 1. Grid System
- Use CSS Grid for page-level layouts, Flexbox for component-level alignment
- Maintain consistent spacing scale: 4px base unit (4, 8, 12, 16, 24, 32, 48, 64, 96)
- Maximum content width: 1200px for text-heavy pages, 1440px for dashboards
- Minimum touch target: 44x44px for mobile, 32x32px for desktop

### 2. Responsive Design
- Mobile-first approach: design for 320px minimum, scale up
- Breakpoints: 640px (sm), 768px (md), 1024px (lg), 1280px (xl), 1536px (2xl)
- Never use horizontal scroll for primary content
- Stack navigation vertically on mobile, horizontal on desktop

### 3. Visual Hierarchy
- Limit to 3 levels of visual prominence per page section
- Use size, weight, and color to establish hierarchy — not just bold
- Primary actions should be visually dominant; secondary actions subdued
- Maintain consistent alignment: left-align text, center-align CTAs sparingly

## Typography

### 4. Font System
- Use system font stack for body text: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Maximum 2 font families per project (1 preferred)
- Type scale: 12, 14, 16, 18, 20, 24, 30, 36, 48, 60, 72px
- Line height: 1.5 for body text, 1.2-1.3 for headings
- Maximum line length: 65-75 characters for readability

### 5. Text Styling
- Body text minimum 16px on desktop, 14px on mobile
- Use font-weight 400 for body, 500 for emphasis, 600-700 for headings
- Limit ALL CAPS to labels, buttons, and short headings
- Use proper typographic quotes (" ") and em dashes (—)

## Color

### 6. Color System
- Define semantic color tokens: `--color-primary`, `--color-success`, `--color-danger`, `--color-warning`
- Maintain light and dark mode variants for all colors
- Background colors: max 3 levels of depth (surface, elevated, overlay)
- Never rely on color alone to convey information — add icons or text

### 7. Contrast & Accessibility
- Text contrast ratio: 4.5:1 minimum (AA), 7:1 preferred (AAA)
- Large text (18px+ or 14px+ bold): 3:1 minimum
- UI component contrast: 3:1 against adjacent colors
- Focus indicators: 3:1 contrast, 2px+ visible outline

## Components

### 8. Buttons
- Limit to 3 button variants: primary (filled), secondary (outlined), ghost (text)
- Consistent padding: 8px 16px (small), 12px 24px (medium), 16px 32px (large)
- Always show loading state for async actions (spinner + disabled)
- Destructive actions: use red/danger color, require confirmation for irreversible

### 9. Forms
- Label every input (visible label preferred over placeholder-only)
- Show validation errors inline, below the field, in red
- Mark required fields with `*` in label
- Group related fields with `fieldset` and `legend`
- Submit button should describe the action: "Create Account" not "Submit"

### 10. Modals & Dialogs
- Use for confirmations and focused tasks only — not navigation
- Always provide a close mechanism: X button, Escape key, backdrop click
- Trap focus inside modal when open
- Limit to 1 modal at a time (never stack modals)
- Maximum width: 480px for alerts, 640px for forms, 960px for complex content

### 11. Tables & Data
- Use sticky headers for scrollable tables
- Right-align numeric data, left-align text
- Provide sorting and filtering for tables with 10+ rows
- Use pagination or virtual scrolling for 100+ rows
- Zebra striping or border-bottom for row separation

## Interaction

### 12. Feedback & States
- Every interactive element needs: default, hover, active, focus, disabled states
- Show loading indicators for operations > 300ms
- Provide success/error feedback within 100ms of user action
- Use skeleton screens instead of spinners for page loads
- Toast notifications auto-dismiss in 5s; errors persist until dismissed

### 13. Animation & Motion
- Duration: 150ms for micro-interactions, 300ms for transitions, 500ms for page changes
- Easing: ease-out for entering, ease-in for exiting, ease-in-out for moving
- Respect `prefers-reduced-motion`: disable non-essential animations
- Never animate layout properties (width, height, top, left) — use transform

### 14. Navigation
- Primary navigation visible on all pages
- Current page/section clearly indicated
- Breadcrumbs for 3+ level hierarchies
- Back button or clear exit path always available
- Search accessible from every page

## Performance

### 15. Loading Performance
- First Contentful Paint (FCP) < 1.8s
- Largest Contentful Paint (LCP) < 2.5s
- Cumulative Layout Shift (CLS) < 0.1
- Interaction to Next Paint (INP) < 200ms
- Total page weight < 1MB for initial load

## Dark Mode

### 16. Dark Mode Design
- Never use pure black (#000000) — use dark gray (#0a0a0a to #1a1a1a)
- Reduce elevation shadows; use subtle borders instead
- Lower image brightness/saturation slightly
- Swap color luminance: light-on-dark, not inverted
- Test all color combinations in both modes
