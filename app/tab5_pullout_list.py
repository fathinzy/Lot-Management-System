import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from . import database as db
from . import label_payload as lp
from . import excel_export as xlx
from .pdf_generator import generate_qa_acceptance_pdf
from .scan_utils import ScanEntry
from . import app_paths
from . import lot_number_generator as lng

# Sits next to the .exe when packaged (persistent), or next to main.py in dev.
DEFAULT_LABEL_EXPORT_PATH = app_paths.data_path("label_export.xlsx")


class PullOutListTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app = app
        self.label_export_path = DEFAULT_LABEL_EXPORT_PATH

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Search Part No:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=16)
        search_entry.pack(side="left", padx=6)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        # Unticked (default) hides lots that already had a QA Acceptance Lot
        # PDF generated; tick "Show All" to see every lot including those.
        self.show_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Show All", variable=self.show_all_var,
                         command=self.refresh).pack(side="left", padx=(12, 0))

        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="left", padx=(12, 0))
        ttk.Button(top, text="Regenerate Lot No.",
                   command=self._regenerate_lot_no).pack(side="left", padx=(12, 0))
        ttk.Button(top, text="Generate QA Acceptance Lot (PDF)",
                   command=self._generate_qa_acceptance_pdf).pack(side="left", padx=6)
        ttk.Button(top, text="Export to Label Excel", command=self._export_excel).pack(
            side="left", padx=6)

        cols = ("status", "customer", "part_no", "rev", "packaging_lot_no", "heat_no",
                 "source_lots", "qty", "packaging_date", "po_number", "prepared_by")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        headers = [
            ("status", "Status", 80), ("customer", "Customer", 100), ("part_no", "Part No (Customer)", 110),
            ("rev", "Rev", 40), ("packaging_lot_no", "Packaging Lot No", 140),
            ("heat_no", "Heat No", 85),
            ("source_lots", "Source Lot Numbers", 200), ("qty", "Qty", 55),
            ("packaging_date", "Packaging Date", 95), ("po_number", "PO Number", 85),
            ("prepared_by", "Prepared By", 90),
        ]
        for c, t, w in headers:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.tree.tag_configure("complete", foreground="#999999")

        scan_frame = ttk.LabelFrame(
            self, text="Label Scan Station - scan a printed barcode from any Lot List / QA "
                       "Acceptance Lot PDF to log its full details straight into the Excel "
                       "export (no retyping)",
            padding=10)
        scan_frame.pack(fill="x", pady=(12, 0))
        self.scan_entry = ScanEntry(scan_frame, self._on_label_scan, label="Scan Barcode:")
        self.scan_entry.pack(fill="x")
        path_row = ttk.Frame(scan_frame)
        path_row.pack(fill="x", pady=(6, 0))
        self.path_var = tk.StringVar(value=self.label_export_path)
        ttk.Label(path_row, text="Excel file:").pack(side="left")
        ttk.Label(path_row, textvariable=self.path_var, foreground="#31708f").pack(
            side="left", padx=6)
        ttk.Button(path_row, text="Change...", command=self._change_export_path).pack(side="left")
        self.scan_status = ttk.Label(scan_frame, text="", foreground="#3c763d")
        self.scan_status.pack(anchor="w", pady=(4, 0))

        self.refresh()

    def _change_export_path(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile=os.path.basename(self.label_export_path),
            filetypes=[("Excel files", "*.xlsx")])
        if path:
            self.label_export_path = path
            self.path_var.set(path)

    def _on_label_scan(self, payload):
        try:
            data = xlx.append_scanned_payload(self.label_export_path, payload)
        except Exception as e:
            self.scan_status.config(text=f"Could not log scan: {e}", foreground="#a94442")
            return
        self.scan_status.config(
            text=f"Logged to Excel: {data.get('source_lot_no', '')} "
                 f"(Qty {data.get('qty_taken', '')}) for Packaging Lot "
                 f"{data.get('packaging_lot_no', '')}.",
            foreground="#3c763d")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = db.list_pullouts(part_no_search=self.search_var.get().strip() or None,
                                 hide_qa_generated=not self.show_all_var.get())
        for p in rows:
            source_lots = db.get_pullout_lots(p["id"])
            source_str = ", ".join(sl["route_card_lot_no"] or "" for sl in source_lots)
            qa_done = bool(p["qa_generated"]) if "qa_generated" in p.keys() else False
            status = "QA GENERATED" if qa_done else "OPEN"
            tag = "complete" if qa_done else ""
            heat_no = p["heat_no"] or (source_lots[-1]["heat_no"] if source_lots else "")
            # Packing List shows the Print Part Number (falls back appropriately).
            display_part_no = (
                (p["print_part_no"] if "print_part_no" in p.keys() else None)
                or p["customer_part_no"] or p["part_no"])
            self.tree.insert("", "end", iid=str(p["id"]), tags=(tag,), values=(
                status, p["customer_name"], display_part_no, p["rev"] or "", p["packaging_lot_no"],
                heat_no or "", source_str, p["packaging_qty"], p["packaging_date"],
                p["po_number"], p["prepared_by"]))

    def _get_selected_pullout(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a row", "Select a pull-out record first.")
            return None, None
        pullout_id = int(sel[0])
        pullout = db.get_pullout(pullout_id)
        pullout_lots = db.get_pullout_lots(pullout_id)
        return pullout, pullout_lots

    def _regenerate_lot_no(self):
        """Rebuild the stored Packaging Lot Number for the selected pull-out
        using the part's CURRENT default rule (Option A). Use this after you
        corrected a rule and want an existing pull-out to pick up the fix.
        New pull-outs already use the latest rule automatically."""
        pullout, pullout_lots = self._get_selected_pullout()
        if not pullout:
            return
        part = db.get_part_by_id(pullout["part_id"])
        if not part:
            messagebox.showerror("Regenerate", "Could not find the part for this pull-out.")
            return
        rule_id = part["default_rule_id"] if "default_rule_id" in part.keys() else None
        rule = db.get_rule_by_id(rule_id) if rule_id else None
        if not rule:
            messagebox.showwarning(
                "No rule set",
                "This part has no default Lot No. Rule set in the Part Register, "
                "so there's nothing to regenerate from. Set the part's Lot No. Rule "
                "first, then try again.")
            return

        # code_value falls back to the part's assigned code (may be blank now
        # that Code lives in the rule); the rule's own Code component wins.
        code_value = ""
        if "code_value" in part.keys() and part["code_value"]:
            code_value = part["code_value"]

        components = lng.components_from_json(rule["components_json"])
        new_lot_no = lng.generate(
            components, pullout_lots, po_number=pullout["po_number"] or "",
            code_value=code_value, separator=rule["separator"] or "")
        if not new_lot_no:
            messagebox.showwarning("Regenerate", "The rule produced an empty lot number.")
            return

        old_lot_no = pullout["packaging_lot_no"] or "(none)"
        if not messagebox.askyesno(
            "Confirm Regenerate",
            f"Rule: {rule['rule_name']}\n\n"
            f"Old Packaging Lot No:\n    {old_lot_no}\n\n"
            f"New Packaging Lot No:\n    {new_lot_no}\n\n"
            "Update this pull-out to the new number? This also clears its "
            "'QA GENERATED' status so you can re-issue a corrected QA "
            "Acceptance Lot PDF."):
            return

        db.update_pullout_lot_no(pullout["id"], new_lot_no)
        self.refresh()
        messagebox.showinfo(
            "Regenerated",
            f"Packaging Lot No updated to:\n{new_lot_no}\n\n"
            "You can now generate the corrected QA Acceptance Lot PDF.")

    def _generate_qa_acceptance_pdf(self):
        pullout, pullout_lots = self._get_selected_pullout()
        if not pullout:
            return
        copies = simpledialog.askinteger(
            "Number of QA Acceptance Lot cards",
            "How many QA Acceptance Lot cards do you need?\n\n"
            "3 cards fit on one page; extras continue on the next page.",
            parent=self, initialvalue=1, minvalue=1, maxvalue=300)
        if copies is None:
            return
        default_name = f"QAAcceptanceLot_{pullout['packaging_lot_no']}.pdf".replace("/", "-")
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf", initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")],
        )
        if not out_path:
            return
        try:
            generate_qa_acceptance_pdf(out_path, pullout, pullout_lots, copies=copies)
        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate PDF:\n{e}")
            return
        # Generating the QA Acceptance Lot marks this pull-out as done, so it
        # drops out of the default (Show All unticked) Packing List view.
        db.set_pullout_qa_generated(pullout["id"], True)
        self.refresh()
        messagebox.showinfo("Done", f"QA Acceptance Lot saved to:\n{out_path}")

    def _export_excel(self):
        pullout, pullout_lots = self._get_selected_pullout()
        if not pullout:
            return
        try:
            count = xlx.export_pullout_rows(self.label_export_path, pullout, pullout_lots)
        except Exception as e:
            messagebox.showerror("Excel Error", f"Failed to export:\n{e}")
            return
        messagebox.showinfo(
            "Exported", f"{count} row(s) written to:\n{self.label_export_path}")
