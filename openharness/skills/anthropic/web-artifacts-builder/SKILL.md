---
name: web-artifacts-builder
description: Build interactive web artifacts and single-page applications. TRIGGER when the user asks to create interactive HTML pages, build web tools, create dashboards, or make self-contained web applications.
---
# Web Artifacts Builder Skill

Create self-contained, interactive web applications as single HTML files.

## Architecture

Build complete applications in a single HTML file with:
- HTML structure
- Embedded CSS (in `<style>` tags)
- Embedded JavaScript (in `<script>` tags)
- No external dependencies (or use CDN links)

## Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Title</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Custom styles */
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div id="app" class="max-w-4xl mx-auto p-6">
        <!-- Application UI -->
    </div>
    <script>
        // Application logic
    </script>
</body>
</html>
```

## Common Patterns
- **Calculators & Tools** - Unit converters, formatters, generators
- **Dashboards** - Charts, metrics, real-time data
- **Games** - Puzzles, quizzes, interactive simulations
- **Editors** - Text editors, image editors, diagram tools

## Guidelines
- Make it fully self-contained (no server required)
- Use Tailwind CSS via CDN for styling
- Add responsive design for mobile
- Include error handling and input validation
- Use localStorage for persistence when needed
