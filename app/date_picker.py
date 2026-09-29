"""
date_picker.py
A small click-to-pick calendar field for date entry, wrapping
tkcalendar.DateEntry.

Why a wrapper instead of using DateEntry directly:
  * The rest of the app stores/reads dates as plain "YYYY-MM-DD" text via
    tk.StringVars. This widget keeps a StringVar in sync in that exact
    format, so nothing downstream (scan auto-fill, Confirm, the CSR lot
    number generator) has to change.
  * Some dates are optional and must be allowed to be BLANK - e.g. Date of
    OQC isn't known until OQC actually inspects the lot. A bare DateEntry
    always holds a date, so this adds a small "x" button to clear it back
    to empty, and treats an empty box as "no date".
  * A scan can push a value into the linked StringVar; this widget mirrors
    that back into the calendar so the two never disagree.

Usage:
    var = tk.StringVar()
    field = DatePickerField(parent, textvariable=var)
    field.grid(...)            # or .pack(...)
    var.get()                  # -> "2026-07-30" or "" if blank
"""
import datetime
import tkinter as tk
from tkinter import ttk

from tkcalendar import DateEntry

DATE_FMT = "%Y-%m-%d"


def _parse(text):
    if not text:
        return None
    for fmt in (DATE_FMT, "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


class DatePickerField(ttk.Frame):
    """A DateEntry calendar + a clear (x) button, kept in sync with a
    StringVar holding YYYY-MM-DD (or "" when blank)."""

    def __init__(self, parent, textvariable=None, width=12, **kwargs):
        super().__init__(parent)
        self.var = textvariable or tk.StringVar()
        self._syncing = False

        # date_pattern controls both what the popup writes and how it's shown.
        self.entry = DateEntry(
            self, width=width, date_pattern="yyyy-mm-dd",
            showweeknumbers=False, firstweekday="monday", **kwargs)
        self.entry.pack(side="left")

        self.clear_btn = ttk.Button(self, text="\u2715", width=2,
                                     command=self.clear)
        self.clear_btn.pack(side="left", padx=(2, 0))

        # Start blank unless the linked var already had a value.
        initial = self.var.get()
        if initial:
            self._set_from_text(initial)
        else:
            self.clear()

        # When the user picks a date in the calendar, push it to the var.
        self.entry.bind("<<DateEntrySelected>>", self._on_pick)
        # When something else changes the var (e.g. a scan), mirror it.
        self.var.trace_add("write", self._on_var_change)

    # ---- calendar -> var ----
    def _on_pick(self, _event=None):
        if self._syncing:
            return
        d = self.entry.get_date()
        self._syncing = True
        try:
            self.var.set(d.strftime(DATE_FMT))
        finally:
            self._syncing = False

    # ---- var -> calendar ----
    def _on_var_change(self, *_args):
        if self._syncing:
            return
        self._set_from_text(self.var.get())

    def _set_from_text(self, text):
        d = _parse(text)
        self._syncing = True
        try:
            if d:
                self.entry.set_date(d)
                # normalize the var to canonical format
                self.var.set(d.strftime(DATE_FMT))
            else:
                # blank / unparseable -> show empty box
                self.entry.delete(0, "end")
                if self.var.get():
                    self.var.set("")
        finally:
            self._syncing = False

    def clear(self):
        """Blank the field (no date)."""
        self._syncing = True
        try:
            self.entry.delete(0, "end")
            self.var.set("")
        finally:
            self._syncing = False
