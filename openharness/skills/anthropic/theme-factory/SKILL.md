---
name: theme-factory
description: Generate UI themes and color schemes. TRIGGER when the user asks to create a color theme, design a UI theme, generate a color palette, or build a design system theme.
---
# Theme Factory Skill

Generate complete UI themes with color palettes, typography, and component styles.

## Theme Generation

1. **Base color** - Start with a primary brand color
2. **Palette expansion** - Generate complementary, analogous, triadic colors
3. **Semantic colors** - Map to success, warning, error, info
4. **Light/Dark variants** - Generate both modes
5. **Component tokens** - Map colors to UI components

## CSS Custom Properties Output

```css
:root {
  /* Primary */
  --color-primary-50: #eff6ff;
  --color-primary-500: #3b82f6;
  --color-primary-900: #1e3a5f;
  
  /* Neutral */
  --color-gray-50: #f9fafb;
  --color-gray-900: #111827;
  
  /* Semantic */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  
  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Spacing */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-4: 1rem;
  --space-8: 2rem;
}
```

## Guidelines
- Ensure WCAG 2.1 AA contrast ratios (4.5:1 for text)
- Generate 10 shades per color (50-900)
- Include both light and dark mode tokens
- Output in CSS, Tailwind, or JSON format as requested
