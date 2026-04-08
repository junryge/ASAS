---
name: pdf
description: Create, read, and manipulate PDF documents. TRIGGER when the user asks to generate a PDF, extract text from a PDF, merge/split PDFs, or convert content to PDF format.
---
# PDF Document Skill

You can create, read, and manipulate PDF files using Python libraries.

## Creating PDFs

Use `reportlab` for creating PDFs from scratch:

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

c = canvas.Canvas("output.pdf", pagesize=A4)
c.drawString(72, 800, "Hello, World!")
c.save()
```

For more complex layouts, use `reportlab.platypus` with Paragraph, Table, Image, and Spacer elements.

## Reading PDFs

Use `PyPDF2` or `pdfplumber` for text extraction:

```python
import pdfplumber
with pdfplumber.open("input.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
```

## Merging / Splitting

```python
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
merger = PdfMerger()
merger.append("file1.pdf")
merger.append("file2.pdf")
merger.write("merged.pdf")
```

## Guidelines
- Always confirm the output path before writing
- For tables, use reportlab.platypus.Table with proper styling
- Support Korean text with CJK fonts (e.g., NanumGothic)
- Handle encoding issues gracefully
