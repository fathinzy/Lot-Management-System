import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import database as db
from . import excel_export as xlx


class LotListTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app

        filt = ttk.Frame(self)
        filt.pack(fill="x")
        ttk.Label(filt, text="Filter Customer:").pack(side="left")
        self.customer_var = tk.StringVar(value="All")
        self.customer_combo = ttk.Combobox(filt, textvariable=self.customer_var,
                                            state="readonly", width=20)
        self.customer_combo.pack(side="left", padx=6)
        self.customer_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filt, text="Search Part No:").pack(side="left", padx=(12, 0))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filt, textvariable=self.search_var, width=18)
        search_entry.pack(side="left", padx=6)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        self.hide_finished_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filt, text="Hide Finished Lots (balance = 0)",
                         variable=self.hide_finished_var,
                         command=self.refresh).pack(side="left", padx=(12, 0))

        ttk.Button(filt, text="Refresh", command=self.refresh).pack(side="left", padx=(12, 0))
        ttk.Button(filt, text="Export to Excel (Backup)", command=self._export_backup).pack(
            side="left", padx=6)

        cols = ("customer", "part_no", "part_name", "rev", "heat_no", "mc_no", "lot_no",
                 "lot_qty", "date_of_oqc", "rtv", "balance_qty", "lot_date", "last_pullout")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=22)
        headers = [
            ("customer", "Customer", 105), ("part_no", "Part No", 90),
            ("part_name", "Part Name", 105), ("rev", "Rev", 40),
            ("heat_no", "Heat No", 80), ("mc_no", "M/C No", 75), ("lot_no", "Lot No", 100),
            ("lot_qty", "Lot Qty", 65), ("date_of_oqc", "Date of OQC", 90),
            ("rtv", "RTV", 50), ("balance_qty", "Balance Lot Qty", 105),
            ("lot_date", "Lot Date", 90), ("last_pullout", "Latest Pull-Out Date", 125),
        ]
        for c, t, w in headers:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.tree.tag_configure("depleted", foreground="#999999")
        self.tree.tag_configure("rtv", foreground="#a94442")

        self.refresh_customers()
        self.refresh()

    def refresh_customers(self):
        names = ["All"] + [c["name"] for c in db.list_customers()]
        self.customer_combo["values"] = names

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        customer = None
        if self.customer_var.get() and self.customer_var.get() != "All":
            customer = db.get_customer_by_name(self.customer_var.get())
        rows = db.list_lots(
            customer_id=customer["id"] if customer else None,
            part_no_search=self.search_var.get().strip() or None,
        )
        for r in rows:
            if self.hide_finished_var.get() and (r["balance_lot_qty"] or 0) <= 0:
                continue
            is_rtv = bool(r["is_rtv"])
            tag = "rtv" if is_rtv else ("depleted" if (r["balance_lot_qty"] or 0) <= 0 else "")
            self.tree.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["customer_name"], r["part_no"], r["part_name"] or "", r["rev"] or "",
                r["heat_no"] or "", r["mc_no"] or "", r["route_card_lot_no"] or "",
                r["input_lot_qty"], r["date_of_oqc"] or "", "RTV" if is_rtv else "",
                r["balance_lot_qty"], r["scan_date"], r["last_pullout_date"] or ""))

    def _export_backup(self):
        out_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile="lot_list_backup.xlsx",
            filetypes=[("Excel files", "*.xlsx")])
        if not out_path:
            return
        try:
            count = xlx.export_lot_list_backup(out_path)
        except Exception as e:
            messagebox.showerror("Excel Error", f"Failed to export backup:\n{e}")
            return
        messagebox.showinfo("Exported", f"{count} lot(s) written to:\n{out_path}")
