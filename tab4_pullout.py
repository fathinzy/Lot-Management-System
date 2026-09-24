import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from . import database as db
from . import lot_number_generator as lng

RULE_CHANGE_PASSWORD = "12345"

CHECK_ON = "\u2611"
CHECK_OFF = "\u2610"
CHECK_LOCKED = "\u25A0"  # locked/unavailable marker


class LotSelectionWindow(tk.Toplevel):
    """
    Shows FIFO-ordered available lots for the target part and lets the
    operator tick which lots to consume. As soon as the running total of
    ticked lots meets/exceeds the packaging quantity, all remaining
    unticked rows are auto-locked (can't be selected) - this mirrors the
    "system permits choosing exactly N lots" auto-lock requirement.
    """

    def __init__(self, parent, lots, target_qty, on_confirm):
        super().__init__(parent)
        self.title("Select Lots for Pull-Out")
        self.geometry("760x480")
        self.lots = lots  # list of sqlite3.Row, FIFO order
        self.target_qty = target_qty
        self.on_confirm = on_confirm
        self.selected_order = []  # lot ids in the order they were checked
        self.checked = {}  # lot_id -> bool

        info = ttk.Label(
            self, text=f"Target Packaging Qty: {target_qty}   "
                       f"(rows lock automatically once enough lots are selected)",
            foreground="#31708f")
        info.pack(anchor="w", padx=10, pady=(10, 4))

        cols = ("select", "lot_no", "heat_no", "mc_no", "mfg_date", "qty", "balance")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        headers = [("select", "Select", 60), ("lot_no", "Route Card Lot No", 150),
                   ("heat_no", "Heat No", 90), ("mc_no", "M/C No", 80),
                   ("mfg_date", "Mfg Date", 95), ("qty", "Lot Qty", 80),
                   ("balance", "Balance", 80)]
        for c, t, w in headers:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Button-1>", self._on_click)

        self.total_var = tk.StringVar(value="Selected total: 0")
        ttk.Label(self, textvariable=self.total_var, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(6, 0))

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=10)
        ttk.Button(btns, text="Confirm Selection", command=self._confirm).pack(side="left")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=8)

        self._populate()

    def _populate(self):
        for lot in self.lots:
            self.checked[lot["id"]] = False
            self.tree.insert("", "end", iid=str(lot["id"]), values=(
                CHECK_OFF, lot["route_card_lot_no"] or "", lot["heat_no"] or "",
                lot["mc_no"] or "", lot["mfg_date"] or "", lot["input_lot_qty"],
                lot["balance_lot_qty"]))
        self._refresh_lock_state()

    def _selected_total(self):
        total = 0.0
        for lot in self.lots:
            if self.checked[lot["id"]]:
                total += lot["balance_lot_qty"] or 0
        return total

    def _refresh_lock_state(self):
        total = self._selected_total()
        self.total_var.set(f"Selected total: {total} / {self.target_qty}")
        met = total >= self.target_qty
        for lot in self.lots:
            lot_id = lot["id"]
            if self.checked[lot_id]:
                mark = CHECK_ON
            elif met:
                mark = CHECK_LOCKED
            else:
                mark = CHECK_OFF
            vals = list(self.tree.item(str(lot_id), "values"))
            vals[0] = mark
            self.tree.item(str(lot_id), values=vals)

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#1":  # only the Select column toggles
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        lot_id = int(row_id)
        total = self._selected_total()
        is_checked = self.checked[lot_id]
        if not is_checked and total >= self.target_qty:
            # locked - selecting more is blocked until something is unchecked
            return
        self.checked[lot_id] = not is_checked
        if self.checked[lot_id]:
            self.selected_order.append(lot_id)
        else:
            self.selected_order = [i for i in self.selected_order if i != lot_id]
        self._refresh_lock_state()

    def _confirm(self):
        if not self.selected_order:
            messagebox.showwarning("No lots selected", "Please select at least one lot.")
            return
        ordered_lots = [next(l for l in self.lots if l["id"] == lid)
                         for lid in self.selected_order]
        self.on_confirm(ordered_lots)
        self.destroy()


class PullOutTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app = app
        self.selected_lots = []

        form = ttk.LabelFrame(self, text="Pull-Out Request", padding=10)
        form.pack(fill="x")

        self.customer_var = tk.StringVar()
        self.part_no_var = tk.StringVar()
        self.rev_var = tk.StringVar()
        self.po_var = tk.StringVar()
        self.qty_var = tk.StringVar()
        self.date_var = tk.StringVar(value=db.today_str())
        self.prepared_by_var = tk.StringVar()
        self.rule_var = tk.StringVar()

        r = 0
        ttk.Label(form, text="Customer *").grid(row=r, column=0, sticky="w", pady=3)
        self.customer_combo = ttk.Combobox(form, textvariable=self.customer_var,
                                            state="readonly", width=22)
        self.customer_combo.grid(row=r, column=1, padx=6)
        self.customer_combo.bind("<<ComboboxSelected>>", lambda e: self._on_customer_change())

        ttk.Label(form, text="Part Number *").grid(row=r, column=2, sticky="w")
        self.part_combo = ttk.Combobox(form, textvariable=self.part_no_var,
                                        state="readonly", width=22)
        self.part_combo.grid(row=r, column=3, padx=6)
        self.part_combo.bind("<<ComboboxSelected>>", lambda e: self._on_part_change())

        r += 1
        ttk.Label(form, text="Part Rev").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.rev_var, width=24, state="readonly").grid(
            row=r, column=1, padx=6)
        ttk.Label(form, text="PO Number *").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.po_var, width=24).grid(row=r, column=3, padx=6)

        r += 1
        ttk.Label(form, text="Packaging Qty *").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.qty_var, width=24).grid(row=r, column=1, padx=6)
        ttk.Label(form, text="Packaging Date").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.date_var, width=24).grid(row=r, column=3, padx=6)

        r += 1
        ttk.Label(form, text="Prepared By").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.prepared_by_var, width=24).grid(row=r, column=1, padx=6)
        ttk.Label(form, text="Lot No. Rule *").grid(row=r, column=2, sticky="w")
        rule_frame = ttk.Frame(form)
        rule_frame.grid(row=r, column=3, sticky="w", padx=6)
        self.rule_combo = ttk.Combobox(rule_frame, textvariable=self.rule_var,
                                        state="disabled", width=18)
        self.rule_combo.pack(side="left")
        self.rule_lock_btn = ttk.Button(rule_frame, text="\U0001F512 Unlock",
                                         command=self._toggle_rule_lock, width=10)
        self.rule_lock_btn.pack(side="left", padx=(4, 0))
        self._rule_unlocked = False

        r += 1
        ttk.Button(form, text="OK - Find Available Lots", command=self._find_lots).grid(
            row=r, column=0, pady=(10, 0), sticky="w")

        result = ttk.LabelFrame(self, text="Selected Lots for this Pull-Out", padding=10)
        result.pack(fill="both", expand=True, pady=(12, 0))
        cols = ("lot_no", "heat_no", "mc_no", "mfg_date", "qty_taken")
        self.result_tree = ttk.Treeview(result, columns=cols, show="headings", height=8)
        for c, t in [("lot_no", "Route Card Lot No"), ("heat_no", "Heat No"),
                     ("mc_no", "M/C No"), ("mfg_date", "Mfg Date"), ("qty_taken", "Qty Taken")]:
            self.result_tree.heading(c, text=t)
        self.result_tree.pack(fill="both", expand=True)

        self.preview_var = tk.StringVar(value="")
        ttk.Label(result, text="Generated Packaging Lot No. Preview:").pack(anchor="w", pady=(8, 0))
        ttk.Label(result, textvariable=self.preview_var, font=("Consolas", 13, "bold"),
                  foreground="#2c5a8c").pack(anchor="w")

        ttk.Button(self, text="Confirm Pull-Out", command=self._confirm_pullout).pack(
            anchor="w", pady=10)

        self.status_label = ttk.Label(self, text="")
        self.status_label.pack(anchor="w")

        self.refresh_customers()

    def _lock_rule(self):
        self._rule_unlocked = False
        self.rule_combo.config(state="disabled")
        self.rule_lock_btn.config(text="\U0001F512 Unlock")

    def _unlock_rule(self):
        self._rule_unlocked = True
        self.rule_combo.config(state="readonly")
        self.rule_lock_btn.config(text="\U0001F513 Lock")

    def _toggle_rule_lock(self):
        if self._rule_unlocked:
            self._lock_rule()
            return
        pwd = simpledialog.askstring(
            "Authorization Required",
            "Enter password to change the Lot No. Rule for this pull-out:",
            show="*", parent=self)
        if pwd is None:
            return  # cancelled
        if pwd == RULE_CHANGE_PASSWORD:
            self._unlock_rule()
        else:
            messagebox.showerror("Incorrect Password",
                                  "Wrong password - Lot No. Rule stays locked to the "
                                  "part's registered default.")

    def refresh_customers(self):
        self.customer_combo["values"] = [c["name"] for c in db.list_customers()]

    def _on_customer_change(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        if not customer:
            return
        parts = db.list_parts(customer["id"])
        self.part_combo["values"] = [p["part_no"] for p in parts]
        self._parts_cache = {p["part_no"]: p for p in parts}
        rules = db.list_rules(customer["id"])
        self.rule_combo["values"] = [r["rule_name"] for r in rules]
        self._rules_cache = {r["rule_name"]: r for r in rules}
        self._lock_rule()

    def _on_part_change(self):
        part = getattr(self, "_parts_cache", {}).get(self.part_no_var.get())
        # Changing the part always re-locks to that part's own registered
        # default rule - an authorized override on one part should not
        # silently carry over to a different part.
        self._lock_rule()
        if part:
            self.rev_var.set(part["rev"] or "")
            default_rule_name = part["default_rule_name"] if "default_rule_name" in part.keys() else None
            self.rule_var.set(default_rule_name or "")

    def _find_lots(self):
        customer = db.get_customer_by_name(self.customer_var.get())
        part = getattr(self, "_parts_cache", {}).get(self.part_no_var.get())
        if not customer or not part:
            messagebox.showwarning("Validation", "Select a valid Customer and Part Number.")
            return
        if not self.rule_var.get():
            messagebox.showwarning("Validation", "Select a Lot No. Rule.")
            return
        try:
            qty = float(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Packaging Qty must be a positive number.")
            return

        lots = db.list_lots(customer_id=customer["id"], part_no=part["part_no"],
                             rev=part["rev"], only_available=True)
        if not lots:
            messagebox.showinfo("No stock", "No available lots with balance for this part.")
            return

        LotSelectionWindow(self, lots, qty, self._on_lots_selected)

    def _on_lots_selected(self, ordered_lots):
        self.selected_lots = ordered_lots
        self.result_tree.delete(*self.result_tree.get_children())
        target = float(self.qty_var.get())
        achievable_total = sum(lot["balance_lot_qty"] or 0 for lot in ordered_lots)
        actual_target = min(target, achievable_total)
        if achievable_total < target:
            self.qty_var.set(str(round(achievable_total, 4)))
            self.status_label.config(
                text=(f"Only {achievable_total} available across the selected lots "
                      f"(requested {target}). Packaging Qty auto-adjusted to {achievable_total}."),
                foreground="#8a6d3b")
        remaining = actual_target
        self._allocations = []  # (lot_id, qty_taken)
        for lot in ordered_lots:
            take = min(remaining, lot["balance_lot_qty"]) if remaining > 0 else 0
            take = round(take, 4)
            self._allocations.append((lot["id"], take))
            remaining -= take
            self.result_tree.insert("", "end", values=(
                lot["route_card_lot_no"] or "", lot["heat_no"] or "", lot["mc_no"] or "",
                lot["mfg_date"] or "", take))
        self._update_preview()

    def _update_preview(self):
        if not self.selected_lots:
            self.preview_var.set("")
            return
        customer = db.get_customer_by_name(self.customer_var.get())
        part = getattr(self, "_parts_cache", {}).get(self.part_no_var.get())
        rule = getattr(self, "_rules_cache", {}).get(self.rule_var.get())
        if not rule:
            return
        code_value = ""
        if part and part["code_value"]:
            code_value = part["code_value"]
        components = lng.components_from_json(rule["components_json"])
        lot_no = lng.generate(components, self.selected_lots, po_number=self.po_var.get(),
                               code_value=code_value, separator=rule["separator"] or "")
        self.preview_var.set(lot_no)

    def _confirm_pullout(self):
        if not self.selected_lots:
            messagebox.showwarning("Validation", "Find and select lots first.")
            return
        customer = db.get_customer_by_name(self.customer_var.get())
        part = getattr(self, "_parts_cache", {}).get(self.part_no_var.get())
        if not self.po_var.get().strip() or not self.prepared_by_var.get().strip():
            messagebox.showwarning("Validation", "PO Number and Prepared By are required.")
            return
        self._update_preview()
        packaging_lot_no = self.preview_var.get()
        if not packaging_lot_no:
            messagebox.showwarning("Validation", "Could not generate a Packaging Lot Number.")
            return

        # Heat No on the Packing List follows the last selected lot, the
        # same "last wins" convention used elsewhere for multi-lot merges.
        heat_no = self.selected_lots[-1]["heat_no"] if self.selected_lots else None

        db.create_pullout(
            customer_id=customer["id"], part_id=part["id"], po_number=self.po_var.get(),
            packaging_qty=float(self.qty_var.get()), packaging_date=self.date_var.get(),
            prepared_by=self.prepared_by_var.get(), packaging_lot_no=packaging_lot_no,
            lot_allocations=self._allocations, heat_no=heat_no,
        )
        self.status_label.config(
            text=f"Pull-out confirmed. Packaging Lot No: {packaging_lot_no}",
            foreground="#3c763d")
        self.selected_lots = []
        self.result_tree.delete(*self.result_tree.get_children())
        self.qty_var.set("")
        self.po_var.set("")
        self.preview_var.set("")
        self._lock_rule()
        self.app.refresh_all()
