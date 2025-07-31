import os
import io
import re
from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

FONT_PATH = os.path.join("fonts", "Amiri-Regular.ttf")  # Adjust this as needed

def contains_arabic(text):
    # Check if string contains any Arabic (Unicode block 0600–06FF)
    return bool(re.search(r'[\u0600-\u06FF]', str(text)))

def reshape_arabic_if_needed(text):
    # If the text contains Arabic, reshape and display correctly
    if contains_arabic(text):
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except Exception:
            return str(text)
    return str(text)

def auto_col_widths(data, font_name, font_size, padding=18, min_w=60, max_w=250):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    col_count = len(data[0])
    result = []
    for i in range(col_count):
        max_len = max(stringWidth(str(row[i]), font_name, font_size) for row in data)
        result.append(min(max(max_len + padding, min_w), max_w))
    return result

def export_pdf(title, headers, row_data, filename="data.pdf", is_arabic=False):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=32,
        leftMargin=32,
        topMargin=28,
        bottomMargin=22
    )
    elements = []
    font_name = 'Amiri'  # Should match your Arabic-friendly font file
    font_size = 10
    title_size = 18

    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, FONT_PATH))

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=title_size,
        alignment=1,
        leading=22,
    )

    # Prepare data: reshape every cell that includes Arabic
    processed_headers = [reshape_arabic_if_needed(h) for h in headers]
    processed_rows = []
    for row in row_data:
        processed_rows.append([reshape_arabic_if_needed(cell) for cell in row])
    data = [processed_headers] + processed_rows

    elements.append(Paragraph(title, style_title))
    elements.append(Spacer(1, 16))

    col_widths = auto_col_widths(data, font_name, font_size)

    table = Table(data, repeatRows=1, colWidths=col_widths, hAlign='LEFT')
    style = [
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 11),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#e0f7fa')))
    table.setStyle(TableStyle(style))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
