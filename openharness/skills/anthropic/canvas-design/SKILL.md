---
name: canvas-design
description: Create HTML5 Canvas-based designs and visualizations. TRIGGER when the user asks to create canvas graphics, interactive visualizations, data visualizations, or animated web graphics.
---
# Canvas Design Skill

Create interactive HTML5 Canvas graphics and visualizations.

## Basic Canvas Setup

```html
<canvas id="canvas" width="800" height="600"></canvas>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Drawing
ctx.fillStyle = '#4A90D9';
ctx.fillRect(50, 50, 200, 100);

ctx.beginPath();
ctx.arc(400, 300, 80, 0, Math.PI * 2);
ctx.fillStyle = '#E74C3C';
ctx.fill();
</script>
```

## Animation Loop

```javascript
function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // Update and draw objects
    requestAnimationFrame(animate);
}
animate();
```

## Data Visualization
- Bar charts, line charts, pie charts
- Scatter plots, heatmaps
- Network graphs, tree diagrams

## Guidelines
- Use requestAnimationFrame for smooth animations
- Handle high-DPI displays with devicePixelRatio
- Add mouse/touch event handlers for interactivity
- Optimize performance for complex scenes
