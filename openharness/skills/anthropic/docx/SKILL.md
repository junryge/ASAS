---
name: docx
description: Create, read, and edit Word documents (.docx). TRIGGER when the user asks to generate Word files, edit documents, add tables/images to documents, or convert content to Word format.
---
# Word Document Skill

Create, read, and manipulate Word documents using `python-docx`.

## Creating Documents

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Title
title = doc.add_heading("Report Title", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

# Paragraph with formatting
p = doc.add_paragraph()
run = p.add_run("Bold and colored text")
run.bold = True
run.font.color.rgb = RGBColor(0, 0, 255)

# Table
table = doc.add_table(rows=3, cols=3, style="Table Grid")
table.cell(0, 0).text = "Header 1"

# Image
doc.add_picture("image.png", width=Inches(4))

doc.save("output.docx")
```

## Reading Documents

```python
doc = Document("input.docx")
for para in doc.paragraphs:
    print(para.text)
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)
```

## Guidelines
- Use proper heading levels (1-6) for document structure
- Apply consistent styles throughout the document
- Handle images with appropriate sizing
- Support Korean text natively (docx handles Unicode)
