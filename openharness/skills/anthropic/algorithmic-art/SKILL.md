---
name: algorithmic-art
description: Create algorithmic and generative art. TRIGGER when the user asks to create generative art, algorithmic visuals, SVG art, mathematical patterns, or creative coding art.
---
# Algorithmic Art Skill

Create beautiful algorithmic and generative art using code.

## Techniques
- **SVG Generation**: Create scalable vector graphics programmatically
- **Mathematical Patterns**: Spirals, fractals, Lissajous curves, Voronoi diagrams
- **Particle Systems**: Simulate particle movement and interactions
- **Color Theory**: Harmonious palettes, gradients, color interpolation
- **Noise Functions**: Perlin noise, simplex noise for organic textures

## SVG Example

```python
import math

def create_spiral_svg(n_points=500, width=800, height=800):
    cx, cy = width/2, height/2
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
    svg += f'<rect width="{width}" height="{height}" fill="#1a1a2e"/>'
    for i in range(n_points):
        t = i / n_points * math.pi * 20
        r = t * 8
        x = cx + r * math.cos(t)
        y = cy + r * math.sin(t)
        hue = int(i / n_points * 360)
        size = max(1, 5 - t/50)
        svg += f'<circle cx="{x}" cy="{y}" r="{size}" fill="hsl({hue},80%,60%)" opacity="0.8"/>'
    svg += '</svg>'
    return svg
```

## Guidelines
- Prefer SVG for resolution-independent output
- Use mathematical functions for organic patterns
- Apply color theory for aesthetic results
- Make parameters configurable for exploration
