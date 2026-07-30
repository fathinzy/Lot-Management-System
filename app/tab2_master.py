import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from . import database as db
from . import lot_number_generator as lng
from . import part_bulk_upload


class MasterRegistrationsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True)

        self.customer_tab = CustomerRegisterTab(sub, app)
        self.code_tab = CodeRegisterTab(sub, app)
        self.part_tab = PartRegisterTab(sub, app)
        self.csr_tab = CsrRuleTab(sub, app)

        sub.add(self.part_tab, text="Part Register")
        sub.add(self.customer_tab, text="Customer Register")
        sub.add(self.code_tab, text="Code Register")
        sub.add(self.csr_tab, text="Customer Lot No. (CSR) Register")

    def refresh_customers(self):
        self.customer_tab.refresh()
        self.code_tab.refresh_customers()
        self.part_tab.refresh_customers()
        self.csr_tab.refresh_customers()


# ------------------------------------------------------------- Customer Register
class CustomerRegisterTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Customer Name:").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.name_var, width=30).pack(side="left", padx=6)
        ttk.Button(row, text="Save", command=self._save).pack(side="left")
        ttk.Button(row, text="Remove Selected", command=self._remove).pack(side="left", padx=8)

        self.tree = ttk.Treeview(self, columns=("name",), show="headings", height=15)
        self.tree.heading("name", text="Customer Name")
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.refresh()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Customer name is required.")
            return
        db.add_customer(name)
        self.name_var.set("")
        self.refresh()
        self.app.refresh_all()

    def _remove(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a row", "Select a customer to remove first.")
            return
        customer_id = int(sel[0])
        if not messagebox.askyesno(
            "Confirm Remove",
            "Remove this customer? This also removes its Codes and Parts. "
            "It will be blocked if lots or pull-outs already reference it."):
            return
        try:
            db.delete_customer(customer_id)
        except Exception as e:
            messagebox.showerror(
                "Cannot Remove",
                "This customer still has lots or pull-out history and cannot be removed.\n"
                f"({e})")
            return
        self.refresh()
        self.app.refresh_all()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for c in db.list_customers():
            self.tree.insert("", "end", iid=str(c["id"]), values=(c["name"],))


# ------------------------------------------------------------- Code Register
class CodeRegisterTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Customer:").grid(row=0, column=0, sticky="w")
        self.customer_var = tk.StringVar()
        self.customer_combo = ttk.Combobox(row, textvariable=self.customer_var,
                                            state="readonly", width=25)
        self.customer_combo.grid(row=0, column=1, padx=6)

        ttk.Label(row, text="Code:").grid(row=0, column=2, sticky="w")
        self.code_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.code_var, width=15).grid(row=0, column=3, padx=6)

        ttk.Label(row, text="Description:").grid(row=0, column=4, sticky="w")
        self.desc_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.desc_var, width=30).grid(row=0, column=5, padx=6)

        ttk.Button(row, text="Save", command=self._save).grid(row=0, column=6, padx=6)
        ttk.Button(row, text="Remove Selected", command=self._remove).grid(row=0, column=7, padx=6)

        self.tree = ttk.Treeview(self, columns=("customer", "code", "description"),
                                  show="headings", height=15)
        for c, t, w in [("customer", "Customer", 160), ("code", "Code", 100),
                        ("description", "Description", 300)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.refresh_customers()
        self.refresh_list()

    def refresh_customers(self):
        self.customer_combo["values"] = [c["name"] for c in db.list_customers()]

    def _save(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        code = self.code_var.get().strip()
        if not customer or not code:
            messagebox.showwarning("Validation", "Customer and Code are required.")
            return
        db.add_code(customer["id"], code, self.desc_var.get())
        self.code_var.set("")
        self.desc_var.set("")
        self.refresh_list()
        self.app.refresh_all()

    def _remove(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a row", "Select a code to remove first.")
            return
        if not messagebox.askyesno("Confirm Remove", "Remove this code?"):
            return
        try:
            db.delete_code(int(sel[0]))
        except Exception as e:
            messagebox.showerror(
                "Cannot Remove",
                f"This code is still assigned to a part and cannot be removed.\n({e})")
            return
        self.refresh_list()
        self.app.refresh_all()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for row in db.list_codes():
            self.tree.insert("", "end", iid=str(row["id"]), values=(
                row["customer_name"], row["code"], row["description"] or ""))


# ------------------------------------------------------------- Part Register
class PartRegisterTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self._editing_id = None
        form = ttk.Frame(self)
        form.pack(fill="x")

        self.customer_var = tk.StringVar()
        self.part_no_var = tk.StringVar()
        self.customer_part_no_var = tk.StringVar()
        self.part_name_var = tk.StringVar()
        self.rev_var = tk.StringVar()
        self.code_var = tk.StringVar()
        self.code_desc_var = tk.StringVar(value="")
        self.rule_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.material_var = tk.StringVar()
        self.default_qty_var = tk.StringVar()

        r = 0
        ttk.Label(form, text="Customer *").grid(row=r, column=0, sticky="w", pady=3)
        self.customer_combo = ttk.Combobox(form, textvariable=self.customer_var,
                                            state="readonly", width=25)
        self.customer_combo.grid(row=r, column=1, padx=6)
        self.customer_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_customer_scoped())

        ttk.Label(form, text="Part Number *").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.part_no_var, width=25).grid(row=r, column=3, padx=6)

        r += 1
        ttk.Label(form, text="Customer Part Number").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.customer_part_no_var, width=25).grid(
            row=r, column=1, padx=6)
        ttk.Label(form, text="(route card uses Part Number; Packing List uses this instead)",
                  foreground="#777777").grid(row=r, column=2, columnspan=2, sticky="w")

        r += 1
        ttk.Label(form, text="Part Name").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.part_name_var, width=25).grid(row=r, column=1, padx=6)
        ttk.Label(form, text="Rev").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.rev_var, width=25).grid(row=r, column=3, padx=6)

        r += 1
        ttk.Label(form, text="Code").grid(row=r, column=0, sticky="w", pady=3)
        self.code_combo = ttk.Combobox(form, textvariable=self.code_var, state="readonly", width=25)
        self.code_combo.grid(row=r, column=1, padx=6)
        self.code_combo.bind("<<ComboboxSelected>>", lambda e: self._preview_code_desc())
        ttk.Label(form, textvariable=self.code_desc_var, foreground="#777777").grid(
            row=r, column=2, columnspan=2, sticky="w")

        r += 1
        ttk.Label(form, text="Lot No. Rule").grid(row=r, column=0, sticky="w", pady=3)
        self.rule_combo = ttk.Combobox(form, textvariable=self.rule_var, state="readonly", width=25)
        self.rule_combo.grid(row=r, column=1, padx=6)
        ttk.Label(form, text="(default rule used at Pull Out)", foreground="#777777").grid(
            row=r, column=2, columnspan=2, sticky="w")

        r += 1
        ttk.Label(form, text="Material Supplier").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.supplier_var, width=25).grid(row=r, column=1, padx=6)
        ttk.Label(form, text="Material Type").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.material_var, width=25).grid(row=r, column=3, padx=6)

        r += 1
        ttk.Label(form, text="Default Lot Qty").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.default_qty_var, width=25).grid(row=r, column=1, padx=6)

        r += 1
        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=4, pady=(8, 0), sticky="w")
        self.save_btn = ttk.Button(btns, text="Save Part", command=self._save)
        self.save_btn.pack(side="left")
        ttk.Button(btns, text="New / Clear", command=self._clear_form).pack(side="left", padx=6)
        ttk.Button(btns, text="Remove Selected", command=self._remove).pack(side="left", padx=6)

        r += 1
        bulk_btns = ttk.Frame(form)
        bulk_btns.grid(row=r, column=0, columnspan=4, pady=(6, 0), sticky="w")
        ttk.Button(bulk_btns, text="Upload Parts (Excel)", command=self._bulk_upload).pack(
            side="left")
        ttk.Button(bulk_btns, text="Download Template", command=self._download_template).pack(
            side="left", padx=6)
        ttk.Label(bulk_btns, text="Only rows whose Customer and Code are already registered "
                                    "get imported - others are skipped and reported.",
                  foreground="#777777").pack(side="left", padx=(6, 0))

        self.edit_hint = ttk.Label(self, text="", foreground="#31708f")
        self.edit_hint.pack(anchor="w", pady=(4, 0))

        self.tree = ttk.Treeview(
            self, columns=("customer", "part_no", "cust_part_no", "part_name", "rev", "code",
                           "rule", "supplier", "material", "default_qty"),
            show="headings", height=13)
        headers = [("customer", "Customer", 100), ("part_no", "Part No", 90),
                   ("cust_part_no", "Customer Part No", 110),
                   ("part_name", "Part Name", 110), ("rev", "Rev", 40),
                   ("code", "Code", 65), ("rule", "Lot No. Rule", 100),
                   ("supplier", "Supplier", 90), ("material", "Material", 80),
                   ("default_qty", "Default Qty", 75)]
        for c, t, w in headers:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        self.refresh_customers()
        self.refresh_list()

    def refresh_customers(self):
        self.customer_combo["values"] = [c["name"] for c in db.list_customers()]

    def _refresh_customer_scoped(self):
        self._refresh_codes()
        self._refresh_rules()

    def _refresh_codes(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        if not customer:
            self.code_combo["values"] = []
            return
        codes = db.list_codes(customer["id"])
        self.code_combo["values"] = [c["code"] for c in codes]
        self._codes_cache = {c["code"]: c for c in codes}

    def _refresh_rules(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        if not customer:
            self.rule_combo["values"] = []
            return
        rules = db.list_rules(customer["id"])
        self.rule_combo["values"] = [r["rule_name"] for r in rules]
        self._rules_cache = {r["rule_name"]: r for r in rules}

    def _preview_code_desc(self):
        code = getattr(self, "_codes_cache", {}).get(self.code_var.get())
        self.code_desc_var.set(f"({code['description']})" if code and code["description"] else "")

    def _save(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        part_no = self.part_no_var.get().strip()
        if not customer or not part_no:
            messagebox.showwarning("Validation", "Customer and Part Number are required.")
            return
        code_row = getattr(self, "_codes_cache", {}).get(self.code_var.get())
        code_id = code_row["id"] if code_row else None
        rule_row = getattr(self, "_rules_cache", {}).get(self.rule_var.get())
        rule_id = rule_row["id"] if rule_row else None
        try:
            default_qty = float(self.default_qty_var.get()) if self.default_qty_var.get() else None
        except ValueError:
            messagebox.showwarning("Validation", "Default Lot Qty must be numeric.")
            return

        if self._editing_id:
            db.update_part_by_id(
                self._editing_id, customer_id=customer["id"], part_no=part_no,
                part_name=self.part_name_var.get(), rev=self.rev_var.get(),
                code_id=code_id, material_supplier=self.supplier_var.get(),
                material_type=self.material_var.get(), default_lot_qty=default_qty,
                default_rule_id=rule_id, customer_part_no=self.customer_part_no_var.get().strip() or None,
            )
            messagebox.showinfo("Updated", f"Part {part_no} updated.")
        else:
            db.upsert_part(
                customer_id=customer["id"], part_no=part_no,
                part_name=self.part_name_var.get(), rev=self.rev_var.get(),
                code_id=code_id, material_supplier=self.supplier_var.get(),
                material_type=self.material_var.get(), default_lot_qty=default_qty,
                default_rule_id=rule_id, customer_part_no=self.customer_part_no_var.get().strip() or None,
            )
            messagebox.showinfo("Saved", f"Part {part_no} saved.")
        self._clear_form()
        self.refresh_list()
        self.app.refresh_all()

    def _on_row_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        part = db.get_part_by_id(int(sel[0]))
        if not part:
            return
        self._editing_id = part["id"]
        customer_row = None
        for c in db.list_customers():
            if c["id"] == part["customer_id"]:
                customer_row = c
                break
        self.customer_var.set(customer_row["name"] if customer_row else "")
        self._refresh_customer_scoped()
        self.part_no_var.set(part["part_no"] or "")
        self.customer_part_no_var.set(part["customer_part_no"] or "")
        self.part_name_var.set(part["part_name"] or "")
        self.rev_var.set(part["rev"] or "")
        code_name = ""
        for code_str, row in getattr(self, "_codes_cache", {}).items():
            if row["id"] == part["code_id"]:
                code_name = code_str
                break
        self.code_var.set(code_name)
        self._preview_code_desc()
        rule_name = ""
        for rname, row in getattr(self, "_rules_cache", {}).items():
            if row["id"] == part["default_rule_id"]:
                rule_name = rname
                break
        self.rule_var.set(rule_name)
        self.supplier_var.set(part["material_supplier"] or "")
        self.material_var.set(part["material_type"] or "")
        self.default_qty_var.set(str(part["default_lot_qty"]) if part["default_lot_qty"] else "")
        self.save_btn.config(text="Update Part")
        self.edit_hint.config(
            text=f"Editing existing part #{part['id']} ({part['part_no']}) - "
                 "Save Part will update it. Click 'New / Clear' to register a new part instead.")

    def _clear_form(self):
        self._editing_id = None
        self.customer_var.set("")
        self.part_no_var.set("")
        self.customer_part_no_var.set("")
        self.part_name_var.set("")
        self.rev_var.set("")
        self.code_var.set("")
        self.code_desc_var.set("")
        self.rule_var.set("")
        self.supplier_var.set("")
        self.material_var.set("")
        self.default_qty_var.set("")
        self.save_btn.config(text="Save Part")
        self.edit_hint.config(text="")
        self.tree.selection_remove(self.tree.selection())

    def _remove(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a row", "Select a part to remove first.")
            return
        if not messagebox.askyesno(
            "Confirm Remove",
            "Remove this part? It will be blocked if lots already reference it."):
            return
        try:
            db.delete_part(int(sel[0]))
        except Exception as e:
            messagebox.showerror(
                "Cannot Remove",
                f"This part still has lots referencing it and cannot be removed.\n({e})")
            return
        self._clear_form()
        self.refresh_list()
        self.app.refresh_all()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for p in db.list_parts():
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p["customer_name"], p["part_no"], p["customer_part_no"] or "",
                p["part_name"] or "", p["rev"] or "", p["code_value"] or "",
                p["default_rule_name"] or "", p["material_supplier"] or "",
                p["material_type"] or "", p["default_lot_qty"] or ""))

    def _download_template(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile="part_upload_template.xlsx",
            filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        part_bulk_upload.create_template(path)
        messagebox.showinfo("Template Saved", f"Template saved to:\n{path}")

    def _bulk_upload(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xlsm")])
        if not path:
            return
        try:
            uploaded, skipped = part_bulk_upload.bulk_upload_parts(path)
        except ValueError as e:
            messagebox.showerror("Upload Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Upload Error", f"Could not read that file:\n{e}")
            return

        self.refresh_list()
        self.app.refresh_all()

        summary = f"Uploaded {len(uploaded)} part(s)."
        if skipped:
            summary += f"\nSkipped {len(skipped)} row(s):\n"
            summary += "\n".join(
                f"  Row {row}: {part or '(no part no)'} - {reason}"
                for row, part, reason in skipped[:15]
            )
            if len(skipped) > 15:
                summary += f"\n  ...and {len(skipped) - 15} more."
        messagebox.showinfo("Upload Complete", summary)


# ------------------------------------------------------------- CSR Rule Builder
LABEL_BY_TYPE = lng.TYPE_LABELS
TYPE_BY_LABEL = {v: k for k, v in lng.TYPE_LABELS.items()}
LABEL_VALUES = list(lng.TYPE_LABELS.values())

FORMAT_OPTIONS = {
    "mfg_date": lng.DATE_FORMAT_OPTIONS,
    "oqc_date": lng.DATE_FORMAT_OPTIONS,
    "week_no": ["W12", "12"],
    "year": ["2025", "25", "Y25", "Y2025"],
}

SOURCE_OPTIONS = ["last", "first"]
# Types whose 2nd dropdown ("Options") is lot-derived, so the Source
# selector (first/last selected lot) is meaningful for them.
LOT_DERIVED_TYPES = {"mfg_date", "route_card_lot_no", "mc_no", "week_no", "year",
                      "month_code", "oqc_date", "oqc_date2"}


class ComponentRow(ttk.Frame):
    def __init__(self, parent, on_change, on_remove, get_codes, get_code_description=None):
        super().__init__(parent)
        self.on_change = on_change
        self.get_codes = get_codes  # callable -> list[str] of registered codes for current customer
        self.get_code_description = get_code_description or (lambda code: "")
        self.type_var = tk.StringVar(value=LABEL_BY_TYPE["code"])
        self.options_var = tk.StringVar(value="")
        self.source_var = tk.StringVar(value="last")
        self.keep_n_var = tk.StringVar(value="")
        self.literal_var = tk.StringVar(value="")
        self.code_desc_var = tk.StringVar(value="")

        ttk.Combobox(self, textvariable=self.type_var, values=LABEL_VALUES,
                     state="readonly", width=30).grid(row=0, column=0, padx=3)
        self.options_combo = ttk.Combobox(self, textvariable=self.options_var, width=16)
        self.options_combo.grid(row=0, column=1, padx=3)
        self.code_desc_label = ttk.Label(self, textvariable=self.code_desc_var,
                                          foreground="#777777")
        self.code_desc_label.grid(row=0, column=2, padx=(2, 6), sticky="w")
        self.source_combo = ttk.Combobox(self, textvariable=self.source_var,
                                          values=SOURCE_OPTIONS, state="readonly", width=8)
        self.source_combo.grid(row=0, column=3, padx=3)
        ttk.Label(self, text="Keep last N:").grid(row=0, column=4, padx=(6, 2))
        self.keep_n_entry = ttk.Entry(self, textvariable=self.keep_n_var, width=4)
        self.keep_n_entry.grid(row=0, column=5)
        self.literal_label = ttk.Label(self, text="Text:")
        self.literal_label.grid(row=0, column=6, padx=(6, 2))
        self.literal_entry = ttk.Entry(self, textvariable=self.literal_var, width=10)
        self.literal_entry.grid(row=0, column=7)
        ttk.Button(self, text="Remove", command=lambda: on_remove(self)).grid(
            row=0, column=8, padx=(8, 0))

        for var in (self.type_var, self.options_var, self.source_var,
                    self.keep_n_var, self.literal_var):
            var.trace_add("write", lambda *a: self._on_type_change_and_notify())
        self._on_type_change_and_notify()

    def _current_type(self):
        return TYPE_BY_LABEL.get(self.type_var.get(), "code")

    def _on_type_change_and_notify(self):
        t = self._current_type()

        # Options dropdown (2nd combo): meaning changes per type.
        if t == "code":
            self.options_combo.config(state="readonly")
            self.options_combo["values"] = self.get_codes()
            desc = self.get_code_description(self.options_var.get())
            self.code_desc_var.set(f"= {desc}" if desc else "")
        elif t == "country":
            self.options_combo.config(state="readonly")
            self.options_combo["values"] = lng.COUNTRY_DISPLAY_OPTIONS
            self.code_desc_var.set("")
        elif t in FORMAT_OPTIONS:
            self.options_combo.config(state="readonly")
            self.options_combo["values"] = FORMAT_OPTIONS[t]
            self.code_desc_var.set("")
        else:
            self.options_combo.config(state="disabled")
            self.options_combo["values"] = []
            self.code_desc_var.set("")

        # Source (first/last selected lot) only matters for lot-derived types.
        self.source_combo.config(state="readonly" if t in LOT_DERIVED_TYPES else "disabled")

        # Keep-last-N only applies to route_card_lot_no.
        self.keep_n_entry.config(state="normal" if t == "route_card_lot_no" else "disabled")

        # Free-text box only applies to "literal" (Custom / Separator).
        self.literal_entry.config(state="normal" if t == "literal" else "disabled")

        self.on_change()

    def refresh_code_options(self):
        if self._current_type() == "code":
            self.options_combo["values"] = self.get_codes()
            desc = self.get_code_description(self.options_var.get())
            self.code_desc_var.set(f"= {desc}" if desc else "")

    def to_dict(self):
        t = self._current_type()
        comp = {
            "type": t,
            "format": self.options_var.get() if t in FORMAT_OPTIONS else "",
            "source": self.source_var.get(),
            "keep_last_n": self.keep_n_var.get() or None,
            "value": "",
        }
        if t == "code":
            comp["value"] = self.options_var.get()
        elif t == "country":
            # options_var shows "Malaysia (M)" -> store just the letter code
            display = self.options_var.get()
            code_letter = ""
            for name, letter in lng.COUNTRY_CODE_MAP.items():
                if display.startswith(name):
                    code_letter = letter
                    break
            comp["value"] = code_letter
        elif t == "literal":
            comp["value"] = self.literal_var.get()
        return comp

    def load(self, comp):
        t = comp.get("type", "code")
        self.type_var.set(LABEL_BY_TYPE.get(t, LABEL_BY_TYPE["code"]))
        self.source_var.set(comp.get("source", "last"))
        self.keep_n_var.set(str(comp.get("keep_last_n") or ""))
        if t == "code":
            self.options_var.set(comp.get("value", ""))
        elif t == "country":
            letter = comp.get("value", "")
            display = ""
            for name, code_letter in lng.COUNTRY_CODE_MAP.items():
                if code_letter == letter:
                    display = f"{name} ({code_letter})"
                    break
            self.options_var.set(display)
        elif t == "literal":
            self.literal_var.set(comp.get("value", ""))
        else:
            self.options_var.set(comp.get("format", ""))
        self._on_type_change_and_notify()


class CsrRuleTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.rows = []

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Customer *").grid(row=0, column=0, sticky="w")
        self.customer_var = tk.StringVar()
        self.customer_combo = ttk.Combobox(top, textvariable=self.customer_var,
                                            state="readonly", width=22)
        self.customer_combo.grid(row=0, column=1, padx=6)
        self.customer_combo.bind("<<ComboboxSelected>>", lambda e: self._on_customer_change())

        ttk.Label(top, text="Rule Name *").grid(row=0, column=2, sticky="w")
        self.rule_name_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.rule_name_var, width=20).grid(row=0, column=3, padx=6)

        ttk.Label(top, text="Existing Rules:").grid(row=0, column=4, sticky="w")
        self.existing_var = tk.StringVar()
        self.existing_combo = ttk.Combobox(top, textvariable=self.existing_var,
                                            state="readonly", width=18)
        self.existing_combo.grid(row=0, column=5, padx=6)
        self.existing_combo.bind("<<ComboboxSelected>>", lambda e: self._load_selected_rule())

        ttk.Button(top, text="Refresh", command=self._refresh_all).grid(row=0, column=6, padx=6)

        ttk.Label(top, text=("Build the lot number by adding components below, in the exact order "
                              "they should appear. Use 'Custom / Separator' components to insert "
                              "'-', '/', or any text wherever you want."),
                  foreground="#777777", wraplength=760, justify="left").grid(
            row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

        comp_frame = ttk.LabelFrame(self, text="Lot Number Components (in order)", padding=8)
        comp_frame.pack(fill="x", pady=10)
        self.comp_container = ttk.Frame(comp_frame)
        self.comp_container.pack(fill="x")
        btn_row = ttk.Frame(comp_frame)
        btn_row.pack(anchor="w", pady=(6, 0))
        ttk.Button(btn_row, text="+ Add Component", command=self._add_component).pack(side="left")
        ttk.Button(btn_row, text="Delete This Rule", command=self._delete_rule).pack(
            side="left", padx=8)

        ttk.Label(self, text="Live Preview:").pack(anchor="w")
        self.preview_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.preview_var, font=("Consolas", 13, "bold"),
                  foreground="#2c5a8c").pack(anchor="w", pady=(0, 8))

        ttk.Button(self, text="Save Rule", command=self._save_rule).pack(anchor="w")

        self._add_component()  # start with one row
        self.refresh_customers()

    def refresh_customers(self):
        self.customer_combo["values"] = [c["name"] for c in db.list_customers()]

    def _refresh_all(self):
        """Refresh button: re-pull customers, this customer's existing rules,
        and each component row's Code dropdown - handy if codes/customers
        were added elsewhere while this tab was already open."""
        self.refresh_customers()
        self._load_rules()
        for row in self.rows:
            row.refresh_code_options()
        self._update_preview()

    def _on_customer_change(self):
        self._load_rules()
        for row in self.rows:
            row.refresh_code_options()
        self._update_preview()

    def _current_codes(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        if not customer:
            return []
        return [c["code"] for c in db.list_codes(customer["id"])]

    def _current_code_description(self, code_value):
        if not code_value:
            return ""
        customer = db.get_customer_by_name(self.customer_var.get())
        if not customer:
            return ""
        for c in db.list_codes(customer["id"]):
            if c["code"] == code_value:
                return c["description"] or ""
        return ""

    def _add_component(self, comp=None):
        row = ComponentRow(self.comp_container, self._update_preview, self._remove_component,
                            get_codes=self._current_codes,
                            get_code_description=self._current_code_description)
        row.pack(fill="x", pady=2)
        if comp:
            row.load(comp)
        self.rows.append(row)
        self._update_preview()

    def _remove_component(self, row):
        row.destroy()
        self.rows.remove(row)
        self._update_preview()

    def _sample_lots(self):
        return [
            {"route_card_lot_no": "RC1023445", "mc_no": "MC07", "mfg_date": "2026-07-18"},
            {"route_card_lot_no": "RC1023491", "mc_no": "MC03", "mfg_date": "2026-07-20"},
        ]

    def _update_preview(self):
        components = [row.to_dict() for row in self.rows]
        customer = db.get_customer_by_name(self.customer_var.get())
        code_value = "ABC123"
        if customer:
            codes = db.list_codes(customer["id"])
            if codes:
                code_value = codes[0]["code"]
        preview = lng.generate(
            components, self._sample_lots(), po_number="PO-0001",
            code_value=code_value, separator="",
        )
        self.preview_var.set(preview or "(configure components above)")

    def _load_rules(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        if not customer:
            self.existing_combo["values"] = []
            return
        rules = db.list_rules(customer["id"])
        self._rules_cache = {r["rule_name"]: r for r in rules}
        self.existing_combo["values"] = list(self._rules_cache.keys())

    def _load_selected_rule(self):
        rule = getattr(self, "_rules_cache", {}).get(self.existing_var.get())
        if not rule:
            return
        self.rule_name_var.set(rule["rule_name"])
        for row in list(self.rows):
            row.destroy()
        self.rows = []
        for comp in lng.components_from_json(rule["components_json"]):
            self._add_component(comp)
        if not self.rows:
            self._add_component()
        self._update_preview()

    def _save_rule(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        rule_name = self.rule_name_var.get().strip()
        if not customer or not rule_name:
            messagebox.showwarning("Validation", "Customer and Rule Name are required.")
            return
        if not self.rows:
            messagebox.showwarning("Validation", "Add at least one component.")
            return
        components = [row.to_dict() for row in self.rows]
        db.upsert_rule(customer["id"], rule_name, lng.components_to_json(components), "")
        self._load_rules()
        self.app.refresh_all()
        messagebox.showinfo("Saved", f"Rule '{rule_name}' saved for {customer['name']}.")

    def _delete_rule(self):
        rule = getattr(self, "_rules_cache", {}).get(self.existing_var.get())
        if not rule:
            messagebox.showwarning("Select a rule", "Pick an existing rule from the dropdown first.")
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete rule '{rule['rule_name']}'?"):
            return
        db.delete_rule(rule["id"])
        self.existing_var.set("")
        self.rule_name_var.set("")
        for row in list(self.rows):
            row.destroy()
        self.rows = []
        self._add_component()
        self._load_rules()
        self.app.refresh_all()
