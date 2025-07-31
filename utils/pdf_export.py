import os
import io
from bidi.algorithm import get_display
import arabic_reshaper
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

FONT_PATH = os.path.join("fonts", "Amiri-Regular.ttf")  # Adjust as needed

def reshape_arabic(text):
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)

def auto_col_widths(data, font_name, font_size, padding=18, min_w=60, max_w=250):
    # Use ReportLab stringWidth to compute pixel width
    from reportlab.pdfbase.pdfmetrics import stringWidth
    col_count = len(data[0])
    result = []
    for i in range(col_count):
        max_len = max(stringWidth(str(row[i]), font_name, font_size) for row in data)
        result.append(min(max(max_len + padding, min_w), max_w))
    return result

def export_pdf(title, headers, row_data, filename="data.pdf", is_arabic=False):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=32, leftMargin=32, topMargin=28, bottomMargin=22)
    elements = []
    font_name = 'Cairo'
    font_size = 10
    title_size = 18

    if not pdfmetrics.getRegisteredFontNames() or font_name not in pdfmetrics.getRegisteredFontNames():
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
    style_cell = ParagraphStyle(
        'Cell',
        fontName=font_name,
        fontSize=font_size,
        alignment=2 if is_arabic else 0,
    )

    # Reshape for Arabic and LTR/RTL titles
    if is_arabic:
        title = reshape_arabic(title)
        headers = [reshape_arabic(h) for h in headers]
        data = [headers] + [[reshape_arabic(cell) for cell in row] for row in row_data]
    else:
        data = [headers] + row_data

    elements.append(Paragraph(title, style_title))
    elements.append(Spacer(1, 16))

    # Calculate column widths based on real content
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
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#e0f7fa')))

    table.setStyle(TableStyle(style))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
