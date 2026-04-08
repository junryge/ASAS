---
name: webapp-testing
description: Test web applications using Playwright. TRIGGER when the user asks to write browser tests, automate web testing, test UI interactions, or create end-to-end tests for web apps.
---
# Web App Testing Skill (Playwright)

Write and run automated browser tests using Playwright.

## Setup

```bash
pip install playwright
playwright install chromium
```

## Writing Tests

```python
from playwright.sync_api import sync_playwright

def test_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("http://localhost:3000/login")
        page.fill("#email", "user@example.com")
        page.fill("#password", "password123")
        page.click("button[type=submit]")
        
        assert page.url == "http://localhost:3000/dashboard"
        assert page.text_content("h1") == "Welcome"
        
        browser.close()
```

## Common Actions
- `page.goto(url)` - Navigate to URL
- `page.fill(selector, value)` - Fill input field
- `page.click(selector)` - Click element
- `page.wait_for_selector(selector)` - Wait for element
- `page.screenshot(path="screenshot.png")` - Take screenshot
- `page.expect_navigation()` - Wait for navigation

## Guidelines
- Use data-testid attributes for selectors when possible
- Add proper waits instead of arbitrary sleeps
- Take screenshots on failure for debugging
- Test both happy path and error cases
