"""
label_payload.py
Defines the exact data payload that gets encoded into the Code128
barcode / QR code printed on each Packing List line item, and the
matching parser used by the Excel "Label Scan Station" so that
scanning a printed barcode round-trips into a spreadsheet row with
zero manual retyping.

Keeping this in one shared module guarantees the barcode content,
the QR content, and the Excel columns never drift out of sync.
"""

# Order matters - this is exactly the order fields are packed into the
# per-line barcode/QR payload (and unpacked from a scan).
LINE_FIELD_ORDER = [
    "customer", "part_no", "part_name", "rev", "packaging_lot_no",
    "po_number", "packaging_qty", "packaging_date", "prepared_by",
    "source_lot_no", "heat_no", "mc_no", "mfg_date", "qty_taken",
]

LINE_FIELD_LABELS = {
    "customer": "Customer",
    "part_no": "Part No",
    "part_name": "Part Name",
    "rev": "Rev",
    "packaging_lot_no": "Packaging Lot No",
    "po_number": "PO Number",
    "packaging_qty": "Packaging Qty",
    "packaging_date": "Packaging Date",
    "prepared_by": "Prepared By",
    "source_lot_no": "Source Lot No",
    "heat_no": "Heat No",
    "mc_no": "M/C No",
    "mfg_date": "Mfg Date",
    "qty_taken": "Qty Taken",
}

DELIMITER = "|"


def _get(row, key, default=""):
    """sqlite3.Row supports [] but not .get(), and some callers pass plain
    dicts - this works with either."""
    try:
        value = row[key]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


def _effective_part_no(pullout):
    """Packing List documents use the Customer Part Number (route cards and
    internal WIP tracking use the internal Part Number instead - see
    Part Register). Falls back to the internal number if no customer part
    number was registered."""
    return _get(pullout, "customer_part_no") or _get(pullout, "part_no")


def build_line_payload(pullout, pullout_lot):
    """pullout: row/dict with customer_name, part_no, customer_part_no,
    part_name (via part lookup upstream), rev, packaging_lot_no, po_number,
    packaging_qty, packaging_date, prepared_by.
    pullout_lot: row/dict with route_card_lot_no, heat_no, mc_no,
    mfg_date, qty_taken, part_name."""
    values = [
        str(_get(pullout, "customer_name")),
        str(_effective_part_no(pullout)),
        str(_get(pullout_lot, "part_name") or _get(pullout, "part_name")),
        str(_get(pullout, "rev")),
        str(_get(pullout, "packaging_lot_no")),
        str(_get(pullout, "po_number")),
        str(_get(pullout, "packaging_qty")),
        str(_get(pullout, "packaging_date")),
        str(_get(pullout, "prepared_by")),
        str(_get(pullout_lot, "route_card_lot_no")),
        str(_get(pullout_lot, "heat_no")),
        str(_get(pullout_lot, "mc_no")),
        str(_get(pullout_lot, "mfg_date")),
        str(_get(pullout_lot, "qty_taken")),
    ]
    # Guard against a delimiter accidentally showing up inside a field.
    values = [v.replace(DELIMITER, "/") for v in values]
    return DELIMITER.join(values)


def parse_line_payload(payload):
    fields = payload.split(DELIMITER)
    result = {}
    for i, key in enumerate(LINE_FIELD_ORDER):
        result[key] = fields[i].strip() if i < len(fields) else ""
    return result


def build_master_payload(pullout, pullout_lots, include_source_lots=True):
    """Compact summary of the whole packaging lot - used for the single QR
    code at the top of the Lot List / QA Acceptance Lot PDF.

    include_source_lots=False leaves out which internal WIP lots were
    combined into this shipment (used for the customer-facing QA
    Acceptance Lot document, so a customer scanning the QR can't tell
    that multiple lots were merged)."""
    heat_no = _get(pullout, "heat_no")
    if not heat_no and pullout_lots:
        heat_no = _get(pullout_lots[-1], "heat_no")
    parts = [
        f"Customer={_get(pullout, 'customer_name')}",
        f"PartNo={_effective_part_no(pullout)}",
        f"Rev={_get(pullout, 'rev')}",
        f"PackagingLotNo={_get(pullout, 'packaging_lot_no')}",
        f"HeatNo={heat_no}",
        f"PO={_get(pullout, 'po_number')}",
        f"PackagingQty={_get(pullout, 'packaging_qty')}",
        f"PackagingDate={_get(pullout, 'packaging_date')}",
        f"PreparedBy={_get(pullout, 'prepared_by')}",
    ]
    if include_source_lots:
        lots_str = "; ".join(
            f"{_get(pl, 'route_card_lot_no')}:{_get(pl, 'qty_taken')}"
            for pl in pullout_lots
        )
        parts.append(f"SourceLots=[{lots_str}]")
    return "; ".join(parts)
