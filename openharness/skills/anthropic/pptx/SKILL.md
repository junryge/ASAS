---
name: pptx
description: Create, read, and edit PowerPoint presentations (.pptx). TRIGGER when the user asks to generate slides, create presentations, add charts/images to slides, or modify existing PowerPoint files.
---
# PowerPoint Presentation Skill

Create, read, and manipulate PowerPoint files using `python-pptx`.

## Creating Presentations

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()

# Title slide
slide_layout = prs.slide_layouts[0]  # Title Slide
slide = prs.slides.add_slide(slide_layout)
slide.shapes.title.text = "Presentation Title"
slide.placeholders[1].text = "Subtitle"

# Content slide
slide_layout = prs.slide_layouts[1]  # Title and Content
slide = prs.slides.add_slide(slide_layout)
slide.shapes.title.text = "Key Points"
body = slide.placeholders[1]
tf = body.text_frame
tf.text = "First point"
p = tf.add_paragraph()
p.text = "Second point"
p.level = 1

# Add image
slide.shapes.add_picture("chart.png", Inches(1), Inches(2), width=Inches(5))

prs.save("output.pptx")
```

## Adding Charts and Tables

```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = CategoryChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4"]
chart_data.add_series("Revenue", (100, 150, 200, 180))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(2), Inches(8), Inches(4),
    chart_data
).chart
```

## Guidelines
- Use slide layouts (0-8) for consistent formatting
- Keep text concise on slides
- Use high-quality images and proper sizing
- Apply consistent color themes
