"""
scan_utils.py
USB barcode scanners behave like a keyboard: they "type" the barcode
payload very fast and finish with an Enter keystroke. ScanEntry just
listens for that Enter and hands the full scanned string to a callback,
so it works for both real scans and manual typing + Enter.

Expected barcode payload format (configurable at the customer/site level
in real deployments): pipe-delimited fields in a fixed order, e.g.

    CUSTOMER|PARTNO|PARTNAME|REV|ROUTECARDLOT|HEATNO|MCNO|MFGDATE|QTY

Fields that are missing are simply left blank.
"""
import re
import tkinter as tk
from tkinter import ttk

SCAN_FIELD_ORDER = [
    "customer", "part_no", "route_card_lot_no",
    "heat_no", "mc_no", "mfg_date", "input_lot_qty", "date_of_oqc",
]

# Some route cards store Part No and Rev combined in one field, e.g.
# "R1000 Rev.A" or "SEN-T-605064-007 REV.C-1" instead of a bare part
# number. Matches "Rev" / "Rev." / "REV" (with or without a period),
# optional space before it, case insensitive. The revision itself can
# include letters, digits, and hyphens (e.g. "A", "C-1", "B2") - it
# must start with a letter/digit so a trailing hyphen in the part
# number itself (e.g. "SEN-T-605064-007") is never mistaken for part
# of the revision.
_REV_SUFFIX_PATTERN = re.compile(
    r"^(.*?)\s*Rev\.?\s*([A-Za-z0-9][A-Za-z0-9\-]*)\s*$", re.IGNORECASE
)


def split_part_no_and_rev(raw_part_no):
    """Route cards sometimes combine Part No and Rev into one field
    (e.g. 'R1000 Rev.A') instead of keeping them as separate fields.
    This splits that back apart. Returns (part_no, rev); rev is '' if
    no embedded revision was found (the value was already a bare part
    number, nothing to split)."""
    if not raw_part_no:
        return raw_part_no, ""
    match = _REV_SUFFIX_PATTERN.match(raw_part_no.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip().upper()
    return raw_part_no.strip(), ""


def parse_scan_payload(payload, delimiter="|"):
    fields = payload.split(delimiter)
    result = {}
    for i, key in enumerate(SCAN_FIELD_ORDER):
        result[key] = fields[i].strip() if i < len(fields) else ""

    # If Part No arrives combined with Rev (e.g. "R1000 Rev.A"), split
    # it so downstream fields get a clean part number and the revision
    # lands in its own field - regardless of whether the route card
    # also sent a separate Rev field.
    clean_part_no, embedded_rev = split_part_no_and_rev(result.get("part_no", ""))
    result["part_no"] = clean_part_no
    if embedded_rev:
        result["rev"] = embedded_rev

    return result


class ScanEntry(ttk.Frame):
    """A labeled entry that triggers on_scan(payload_str) when Enter is hit."""

    def __init__(self, parent, on_scan, label="Scan Barcode:"):
        super().__init__(parent)
        self.on_scan = on_scan
        ttk.Label(self, text=label).pack(side="left", padx=(0, 6))
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=60)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self._handle_return)
        ttk.Label(self, text="(scan here, or type and press Enter)",
                  foreground="#777777").pack(side="left", padx=(6, 0))

    def _handle_return(self, event):
        payload = self.var.get().strip()
        if payload:
            self.on_scan(payload)
        self.var.set("")

    def focus_entry(self):
        self.entry.focus_set()
