"""
pdf_generator.py
Generates PDF documents for a pull-out record, in two variants:

- generate_lot_list_pdf(): the full internal-use document. Title
  "Lot List". Includes the Packaging Lot Barcode, the full Source Lot
  Detail table (each source lot with its own full-detail barcode), and
  a master QR that includes which source lots were combined.

- generate_qa_acceptance_pdf(): the customer-facing document. Title
  "QA Acceptance Lot". Leaves out the Packaging Lot Barcode section and
  the Source Lot Detail table, and the master QR omits the source-lot
  breakdown too - so a customer can't tell that multiple internal WIP
  lots were combined into this shipment.

Both still carry a master QR (top-right) summarizing the shipment, and
the Lot List variant also gives every source lot its own Code128
barcode, encoding that specific line's full detail set (same fields the
Excel Label Scan Station expects) so packaging staff can scan straight
off the printed sheet with no manual retyping.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from . import label_payload as lp


def _code128_flowable(value, height=11 * mm, target_width=48 * mm):
    """Code128 width grows with payload length (barWidth is a fixed
    per-module size), and our payloads now carry every field, not just a
    short lot number - so the module width is auto-scaled down to fit
    target_width regardless of how long the encoded string is."""
    value = value or "N/A"
    probe = code128.Code128(value, barHeight=height - 4 * mm, barWidth=0.30,
                             humanReadable=False)
    probe_width, _ = probe.wrap(0, 0)
    bar_width = 0.30
    if probe_width > 0:
        bar_width = max(0.045, 0.30 * (target_width / probe_width))
    return code128.Code128(value, barHeight=height - 4 * mm, barWidth=bar_width,
                            humanReadable=False)


def _qr_drawing(value, size=32 * mm):
    qr = QrCodeWidget(value or "N/A")
    b = qr.getBounds()
    w, h = b[2] - b[0], b[3] - b[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(qr)
    return d


class _QrOnCanvas:
    """A zero-height flowable that paints a QR code at a fixed position on
    the current page when the doc is built (used for the top-right master
    QR so it doesn't disturb normal document flow)."""

    def __init__(self, value, x, y, size):
        self.value = value
        self.x, self.y, self.size = x, y, size

    def __call__(self, canvas, doc):
        drawing = _qr_drawing(self.value, self.size)
        renderPDF.draw(drawing, canvas, self.x, self.y)
        canvas.setFont("Helvetica", 6)
        canvas.drawCentredString(self.x + self.size / 2, self.y - 3 * mm,
                                  "Scan for full details")


def _build_pdf(output_path, pullout, pullout_lots, title, include_details):
    """Shared builder for both document variants.

    title: the document heading ("Lot List" or "QA Acceptance Lot").
    include_details: when True, adds the Packaging Lot Barcode section
        and the full Source Lot Detail table, and the master QR includes
        the source-lot breakdown. When False (QA Acceptance Lot), both
        sections are omitted and the QR leaves out which source lots
        were combined.
    """
    page_w, page_h = A4
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Title"], fontSize=16, spaceAfter=2 * mm,
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 3 * mm))

    try:
        heat_no = pullout["heat_no"]
    except (KeyError, IndexError):
        heat_no = None
    display_part_no = lp._effective_part_no(pullout)

    header_data = [
        ["Customer:", pullout["customer_name"], "PO Number:", pullout["po_number"]],
        ["Part No:", display_part_no, "Rev:", pullout["rev"]],
        ["Packaging Date:", pullout["packaging_date"], "Prepared By:", pullout["prepared_by"]],
        ["Packaging Qty:", str(pullout["packaging_qty"]), "Packaging Lot No:", pullout["packaging_lot_no"]],
        ["Heat No:", heat_no or "", "", ""],
    ]
    header_table = Table(header_data, colWidths=[32 * mm, 55 * mm, 33 * mm, 40 * mm])
    header_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    if include_details:
        # Packaging lot barcode (Code128) representing the whole shipment.
        story.append(Paragraph("Packaging Lot Barcode", styles["Heading3"]))
        story.append(_code128_flowable(pullout["packaging_lot_no"], height=16 * mm, target_width=70 * mm))
        story.append(Spacer(1, 6 * mm))

        # Line items table: each source lot is its own row with its own
        # full-detail Code128 barcode.
        story.append(Paragraph("Source Lot Detail (each barcode scans to that "
                                "line's full data - customer, part, packaging "
                                "lot no, PO, this source lot, qty, etc.)",
                                styles["Normal"]))
        story.append(Spacer(1, 2 * mm))
        table_data = [["#", "Route Card Lot No", "Heat No", "M/C No", "Mfg Date", "Qty", "Barcode"]]
        for idx, pl in enumerate(pullout_lots, start=1):
            payload = lp.build_line_payload(pullout, pl)
            table_data.append([
                str(idx),
                pl["route_card_lot_no"] or "",
                pl["heat_no"] or "",
                pl["mc_no"] or "",
                pl["mfg_date"] or "",
                str(pl["qty_taken"]),
                _code128_flowable(payload, height=11 * mm, target_width=48 * mm),
            ])

        col_widths = [8 * mm, 28 * mm, 18 * mm, 18 * mm, 20 * mm, 14 * mm, 54 * mm]
        line_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        line_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ]))
        story.append(line_table)

    # Master QR (top-right corner) - painted directly onto the canvas so it
    # sits in a fixed spot regardless of how the flowables above wrap.
    master_payload = lp.build_master_payload(pullout, pullout_lots,
                                              include_source_lots=include_details)
    qr_size = 30 * mm
    qr_x = page_w - doc.rightMargin - qr_size
    qr_y = page_h - doc.topMargin - qr_size + 2 * mm
    on_first_page = _QrOnCanvas(master_payload, qr_x, qr_y, qr_size)

    doc.build(story, onFirstPage=on_first_page)
    return output_path


def generate_lot_list_pdf(output_path, pullout, pullout_lots):
    """Full internal-use document - title 'Lot List'. Includes the
    Packaging Lot Barcode, the full Source Lot Detail table, and a
    master QR that includes which source lots were combined.

    pullout: sqlite3.Row / dict with keys: customer_name, part_no, rev,
             po_number, packaging_qty, packaging_date, prepared_by,
             packaging_lot_no
    pullout_lots: list of sqlite3.Row / dict, each with keys:
             route_card_lot_no, heat_no, mc_no, mfg_date, qty_taken, part_name
    """
    return _build_pdf(output_path, pullout, pullout_lots, title="Lot List", include_details=True)


def generate_qa_acceptance_pdf(output_path, pullout, pullout_lots):
    """Customer-facing document - title 'QA Acceptance Lot'. Leaves out
    the Packaging Lot Barcode section and the Source Lot Detail table,
    and the master QR omits the source-lot breakdown, so a customer
    can't tell that multiple internal WIP lots were combined."""
    return _build_pdf(output_path, pullout, pullout_lots, title="QA Acceptance Lot", include_details=False)
