---
name: slack-gif-creator
description: Create animated GIFs for Slack and messaging. TRIGGER when the user asks to create GIFs, animated images for Slack, reaction GIFs, or animated stickers.
---
# Slack GIF Creator Skill

Create animated GIFs suitable for Slack and messaging platforms.

## Using Pillow

```python
from PIL import Image, ImageDraw, ImageFont

frames = []
for i in range(30):
    img = Image.new('RGB', (400, 200), color=(30, 30, 60))
    draw = ImageDraw.Draw(img)
    # Animate text or shapes
    x = int(i / 30 * 300)
    draw.text((x, 80), "Hello!", fill=(255, 255, 255))
    frames.append(img)

frames[0].save(
    'output.gif',
    save_all=True,
    append_images=frames[1:],
    duration=50,
    loop=0,
    optimize=True
)
```

## Guidelines
- Keep file size under 5MB for Slack
- Use 256 colors or fewer for smaller files
- Frame rate: 10-20 fps is usually sufficient
- Dimensions: 400-600px wide for Slack
- Add text with clear, readable fonts
- Loop smoothly for reaction GIFs
