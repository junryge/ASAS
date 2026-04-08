---
name: accessibility
description: Audit and fix web accessibility (WCAG). TRIGGER when the user asks to check accessibility, fix a11y issues, audit WCAG compliance, add ARIA labels, or make a site more accessible.
---
# Accessibility

Audit and fix web accessibility issues following WCAG 2.1 guidelines.

## Steps

1. **Run automated checks** - Use tools to catch common issues first.
2. **Manual audit** - Check the categories below that automated tools miss.
3. **Prioritize findings** - Rank by impact (WCAG level A > AA > AAA) and number of affected users.
4. **Fix issues** - Apply fixes with correct ARIA attributes, semantic HTML, and keyboard support.
5. **Verify** - Retest with screen reader and keyboard navigation.

## Automated Testing

```bash
# axe-core via CLI
npx @axe-core/cli http://localhost:3000

# Lighthouse accessibility audit
npx lighthouse http://localhost:3000 --only-categories=accessibility --output=json

# pa11y
npx pa11y http://localhost:3000
```

### In-code testing (jest-axe)
```javascript
import { axe, toHaveNoViolations } from 'jest-axe';
import { render } from '@testing-library/react';

expect.extend(toHaveNoViolations);

test('form should have no accessibility violations', async () => {
  const { container } = render(<LoginForm />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

## WCAG Audit Checklist

### Perceivable

**Images and media:**
```html
<!-- BAD: missing alt text -->
<img src="chart.png">

<!-- GOOD: descriptive alt text -->
<img src="chart.png" alt="Bar chart showing monthly revenue increasing from $10k to $50k over 2024">

<!-- Decorative images: empty alt -->
<img src="divider.png" alt="" role="presentation">
```

**Color contrast:**
```css
/* WCAG AA requires 4.5:1 for normal text, 3:1 for large text */
/* BAD: low contrast */
.text { color: #999; background: #fff; }  /* 2.85:1 ratio */

/* GOOD: sufficient contrast */
.text { color: #595959; background: #fff; }  /* 7:1 ratio */
```

**Do not rely on color alone:**
```html
<!-- BAD: only color indicates error -->
<input style="border-color: red;">

<!-- GOOD: icon + text + color -->
<input style="border-color: red;" aria-describedby="email-error">
<span id="email-error" role="alert">
  <svg aria-hidden="true"><!-- error icon --></svg>
  Please enter a valid email address
</span>
```

### Operable

**Keyboard navigation:**
```html
<!-- All interactive elements must be keyboard accessible -->
<!-- BAD: clickable div with no keyboard support -->
<div onclick="handleClick()">Click me</div>

<!-- GOOD: use a button -->
<button onclick="handleClick()">Click me</button>

<!-- If you must use a div, add role and keyboard handling -->
<div role="button" tabindex="0" onclick="handleClick()" onkeydown="if(event.key==='Enter'||event.key===' ') handleClick()">
  Click me
</div>
```

**Skip navigation:**
```html
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <nav><!-- long navigation --></nav>
  <main id="main-content">
    <!-- page content -->
  </main>
</body>

<style>
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  z-index: 100;
}
.skip-link:focus {
  top: 0;
}
</style>
```

**Focus management:**
```css
/* NEVER remove focus outlines without providing an alternative */
/* BAD */
*:focus { outline: none; }

/* GOOD: custom focus styles */
*:focus-visible {
  outline: 2px solid #4A90D9;
  outline-offset: 2px;
}
```

### Understandable

**Forms:**
```html
<!-- BAD: input without label -->
<input type="email" placeholder="Email">

<!-- GOOD: visible label associated with input -->
<label for="email">Email address</label>
<input type="email" id="email" aria-required="true" autocomplete="email">

<!-- Error messages -->
<label for="password">Password</label>
<input type="password" id="password" aria-describedby="pw-req" aria-invalid="true">
<p id="pw-req">Password must be at least 8 characters</p>
```

### Robust

**Semantic HTML:**
```html
<!-- Use semantic elements instead of divs -->
<header>...</header>
<nav aria-label="Main navigation">...</nav>
<main>
  <article>
    <h1>Page Title</h1>
    <section aria-labelledby="section-heading">
      <h2 id="section-heading">Section</h2>
    </section>
  </article>
</main>
<footer>...</footer>
```

**ARIA landmarks and live regions:**
```html
<!-- Live region for dynamic content -->
<div aria-live="polite" aria-atomic="true">
  <!-- Screen reader announces changes here -->
  Items in cart: 3
</div>

<!-- Assertive for urgent messages -->
<div role="alert" aria-live="assertive">
  Your session will expire in 2 minutes.
</div>
```

## Rules

- Use semantic HTML first; only add ARIA when HTML semantics are insufficient
- Every interactive element must be keyboard accessible
- Every image must have alt text (empty `alt=""` for decorative images)
- Color must never be the only means of conveying information
- Form inputs must have associated labels
- Test with a real screen reader (VoiceOver, NVDA) not just automated tools
- Automated tools catch only ~30% of accessibility issues -- manual testing is essential
- Maintain a logical heading hierarchy (h1 -> h2 -> h3, no skipping levels)
