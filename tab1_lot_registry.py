import tkinter as tk
from tkinter import ttk, messagebox
from . import database as db
from .scan_utils import ScanEntry, parse_scan_payload, split_part_no_and_rev


class LotRegistryTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app = app
        self._build()
        self.refresh_customers()

    def _build(self):
        scan_row = ttk.Frame(self)
        scan_row.pack(fill="x", pady=(0, 12))
        self.scan_entry = ScanEntry(scan_row, self._on_scan)
        self.scan_entry.pack(fill="x")

        form = ttk.LabelFrame(self, text="Lot Details", padding=10)
        form.pack(fill="x")

        self.vars = {
            "customer": tk.StringVar(),
            "part_no": tk.StringVar(),
            "part_name": tk.StringVar(),
            "rev": tk.StringVar(),
            "route_card_lot_no": tk.StringVar(),
            "heat_no": tk.StringVar(),
            "mc_no": tk.StringVar(),
            "mfg_date": tk.StringVar(),
            "input_lot_qty": tk.StringVar(),
            "date_of_oqc": tk.StringVar(),
        }
        self.is_rtv_var = tk.BooleanVar(value=False)

        r = 0
        ttk.Label(form, text="Customer *").grid(row=r, column=0, sticky="w", pady=4)
        self.customer_combo = ttk.Combobox(form, textvariable=self.vars["customer"],
                                            state="readonly", width=28)
        self.customer_combo.grid(row=r, column=1, sticky="w", padx=(6, 20))
        self.customer_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_part_lookup())

        ttk.Label(form, text="Part No *").grid(row=r, column=2, sticky="w")
        self.part_combo = ttk.Combobox(form, textvariable=self.vars["part_no"], width=28)
        self.part_combo.grid(row=r, column=3, sticky="w", padx=6)
        self.part_combo.bind("<<ComboboxSelected>>", lambda e: self._autofill_from_part())
        self.part_combo.bind("<FocusOut>", lambda e: self._autofill_from_part())

        r += 1
        ttk.Label(form, text="Route Card Lot No").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.vars["route_card_lot_no"], width=30).grid(
            row=r, column=1, sticky="w", padx=(6, 20))
        ttk.Label(form, text="Heat Number").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.vars["heat_no"], width=30).grid(
            row=r, column=3, sticky="w", padx=6)

        r += 1
        ttk.Label(form, text="M/C Number").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.vars["mc_no"], width=30).grid(
            row=r, column=1, sticky="w", padx=(6, 20))
        ttk.Label(form, text="Mfg Date (YYYY-MM-DD)").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.vars["mfg_date"], width=30).grid(
            row=r, column=3, sticky="w", padx=6)

        r += 1
        ttk.Label(form, text="Input Lot Qty *").grid(row=r, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.vars["input_lot_qty"], width=30).grid(
            row=r, column=1, sticky="w", padx=(6, 20))
        ttk.Label(form, text="Date of OQC (YYYY-MM-DD)").grid(row=r, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.vars["date_of_oqc"], width=30).grid(
            row=r, column=3, sticky="w", padx=6)

        r += 1
        ttk.Checkbutton(form, text="RTV Lot (tick if this lot is Return-to-Vendor)",
                         variable=self.is_rtv_var).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))

        r += 1
        btn_row = ttk.Frame(form)
        btn_row.grid(row=r, column=0, columnspan=4, pady=(10, 0), sticky="w")
        ttk.Button(btn_row, text="Confirm", command=self._confirm).pack(side="left")
        ttk.Button(btn_row, text="Clear", command=self._clear).pack(side="left", padx=8)

        self.status_label = ttk.Label(self, text="", foreground="#a94442")
        self.status_label.pack(anchor="w", pady=(8, 0))

    def refresh_customers(self):
        customers = db.list_customers()
        self.customer_combo["values"] = [c["name"] for c in customers]

    def _refresh_part_lookup(self):
        customer = db.get_customer_by_name(self.vars["customer"].get())
        if not customer:
            self.part_combo["values"] = []
            return
        parts = db.list_parts(customer["id"])
        # Offer both the internal Part Number and the Customer Part Number
        # in the dropdown/autocomplete - the operator may know either one.
        values = []
        for p in parts:
            if p["part_no"] and p["part_no"] not in values:
                values.append(p["part_no"])
            if p["customer_part_no"] and p["customer_part_no"] not in values:
                values.append(p["customer_part_no"])
        self.part_combo["values"] = values

    def _autofill_from_part(self):
        customer = db.get_customer_by_name(self.vars["customer"].get())
        if not customer:
            return False
        typed_value = self.vars["part_no"].get().strip()
        if not typed_value:
            return False
        # Some route cards combine Part No and Rev into one field (e.g.
        # "R1000 Rev.A" or "SEN-T-605064-007 REV.C-1") instead of keeping
        # them separate - split that apart first so both the lookup and
        # the Rev field itself get clean values regardless of which
        # format arrived. Part Name and Rev are tracked internally (used
        # for validation and saved with the lot) but are not shown as
        # separate fields on this form - the confirmation below is the
        # only place they surface, to keep the scan-and-go flow fast.
        clean_value, embedded_rev = split_part_no_and_rev(typed_value)
        if embedded_rev:
            typed_value = clean_value
            self.vars["part_no"].set(clean_value)
            self.vars["rev"].set(embedded_rev)

        # The operator may have typed either the internal Part Number or the
        # Customer Part Number (from the Part Register) - detect whichever
        # matches and normalize the field to the canonical internal number,
        # since that's what Lot Registry / route cards track by. Passing the
        # already-known Rev (if any) avoids silently matching the wrong
        # revision when multiple revs of the same part are registered.
        known_rev = self.vars["rev"].get().strip() or None
        row = db.find_part_by_any_no(customer["id"], typed_value, rev=known_rev)
        if row:
            self.vars["part_no"].set(row["part_no"] or "")
            self.vars["part_name"].set(row["part_name"] or "")
            self.vars["rev"].set(row["rev"] or "")

            via_customer_pn = row["customer_part_no"] and typed_value == row["customer_part_no"]
            detail = row["part_name"] or ""
            if row["rev"]:
                detail = f"{detail} (Rev {row['rev']})" if detail else f"Rev {row['rev']}"
            prefix = f"Matched via Customer Part Number -> Part No {row['part_no']}. " if via_customer_pn else ""
            self.status_label.config(text=f"{prefix}{detail}".strip(), foreground="#31708f")
            return True
        return False

    def _on_scan(self, payload):
        data = parse_scan_payload(payload)
        # Clear every field first - otherwise a value left over from a
        # previous manual entry or scan (e.g. Part Name resolved last
        # time) can silently persist if this scan's payload doesn't
        # happen to include that field.
        for v in self.vars.values():
            v.set("")
        if data.get("customer"):
            self.vars["customer"].set(data["customer"])
            self._refresh_part_lookup()
        for key in ("part_no", "part_name", "rev", "route_card_lot_no",
                    "heat_no", "mc_no", "mfg_date", "input_lot_qty", "date_of_oqc"):
            if data.get(key):
                self.vars[key].set(data[key])
        matched = self._autofill_from_part()
        if not matched:
            self.status_label.config(
                text="Barcode scanned - part not found in Part Register yet. "
                     "Check Part No / Rev, or register it first.",
                foreground="#a94442")

    def _clear_fields(self):
        for v in self.vars.values():
            v.set("")
        self.is_rtv_var.set(False)

    def _clear(self):
        self._clear_fields()
        self.status_label.config(text="")

    def _confirm(self):
        self._autofill_from_part()  # normalize in case Customer Part Number was typed
        customer = db.get_customer_by_name(self.vars["customer"].get())
        part_no = self.vars["part_no"].get().strip()
        rev = self.vars["rev"].get().strip()
        qty_raw = self.vars["input_lot_qty"].get().strip()

        if not customer:
            self._error("Please select a valid Customer.")
            return
        if not part_no:
            self._error("Part No is required.")
            return
        try:
            qty = float(qty_raw)
            if qty <= 0:
                raise ValueError
        except ValueError:
            self._error("Input Lot Qty must be a positive number.")
            return

        part = db.get_part(customer["id"], part_no, rev)
        if not part:
            self._error(
                f"'{part_no}' (Rev {rev or '-'}) is not registered in the Part Register. "
                "Register it under System Registrations > Part Register first."
            )
            return

        db.insert_lot(
            customer_id=customer["id"], part_id=part["id"], part_no=part_no,
            part_name=self.vars["part_name"].get(), rev=rev,
            route_card_lot_no=self.vars["route_card_lot_no"].get(),
            heat_no=self.vars["heat_no"].get(), mc_no=self.vars["mc_no"].get(),
            mfg_date=self.vars["mfg_date"].get(), input_lot_qty=qty,
            date_of_oqc=self.vars["date_of_oqc"].get(), is_rtv=self.is_rtv_var.get(),
        )
        rtv_note = " [RTV]" if self.is_rtv_var.get() else ""
        self._clear_fields()
        self.status_label.config(text=f"Lot saved for {part_no} (Qty {qty}).{rtv_note}",
                                  foreground="#3c763d")
        self.app.refresh_all()

    def _error(self, msg):
        self.status_label.config(text=msg, foreground="#a94442")
