"""
Lot Management System
Local manufacturing traceability & packaging tool.

Run with:  python main.py
Requires:  Python 3.9+, reportlab  (see requirements.txt)

Tabs:
  Lot Registry          - scan/enter incoming WIP lots
  Lot List               - live inventory view
  Pull Out                - consume lots into a packaging lot
  Packing List             - pull-out history + Packing List PDF w/ barcodes
  System Registrations      - Part / Customer / Code / CSR Lot-No Rule registers
"""
import tkinter as tk
from tkinter import ttk

from app import database as db
from app.tab1_lot_registry import LotRegistryTab
from app.tab2_master import MasterRegistrationsTab
from app.tab3_lot_list import LotListTab
from app.tab4_pullout import PullOutTab
from app.tab5_pullout_list import PullOutListTab


class LotManagementApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lot Management System")
        self.geometry("1200x760")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        db.init_db()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.tab1 = LotRegistryTab(notebook, self)
        self.tab3 = LotListTab(notebook, self)
        self.tab4 = PullOutTab(notebook, self)
        self.tab5 = PullOutListTab(notebook, self)
        self.tab2 = MasterRegistrationsTab(notebook, self)

        notebook.add(self.tab1, text="Lot Registry")
        notebook.add(self.tab3, text="Lot List")
        notebook.add(self.tab4, text="Pull Out")
        notebook.add(self.tab5, text="Packing List")
        notebook.add(self.tab2, text="System Registrations")

        self.notebook = notebook

    def refresh_all(self):
        """Called after any write so every tab's dropdowns/tables stay in sync."""
        self.tab1.refresh_customers()
        self.tab2.refresh_customers()
        self.tab3.refresh_customers()
        self.tab3.refresh()
        self.tab4.refresh_customers()
        self.tab5.refresh()


if __name__ == "__main__":
    app = LotManagementApp()
    app.mainloop()
