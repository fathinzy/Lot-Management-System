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
import tkinter as tk
from tkinter import ttk

SCAN_FIELD_ORDER = [
    "customer", "part_no", "part_name", "rev", "route_card_lot_no",
    "heat_no", "mc_no", "mfg_date", "input_lot_qty", "date_of_oqc",
]


def parse_scan_payload(payload, delimiter="|"):
    fields = payload.split(delimiter)
    result = {}
    for i, key in enumerate(SCAN_FIELD_ORDER):
        result[key] = fields[i].strip() if i < len(fields) else ""
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
