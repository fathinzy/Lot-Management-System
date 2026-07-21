# Lot Management System

A local desktop application for manufacturing lot traceability and
packaging workflows. Built with **Python + Tkinter** (UI) and
**SQLite** (storage) - no server, no internet connection required.

## 1. Setup

Requires Python 3.9+ (Tkinter ships with standard Python on
Windows/macOS; on Linux install `python3-tk` via your package manager
if it's missing).

```bash
pip install -r requirements.txt
python main.py
```

On first run, `lot_management.db` is created automatically next to
`main.py`. All data lives in that single file - back it up like any
other file. If you're upgrading from an earlier copy of this app, your
existing `lot_management.db` is upgraded automatically and safely the
first time you run the new version (new columns are added without
touching your existing data).

## 2. How the barcode scanner works (Lot Registry, Tab 1)

A USB barcode scanner types like a keyboard and finishes with Enter.
Every scan box in the app ("Scan Barcode:") is a plain text field that
listens for Enter. Point the scanner at a barcode encoding pipe (`|`)
delimited fields in this order and it will auto-fill the form:

```
CUSTOMER|PARTNO|PARTNAME|REV|ROUTECARDLOTNO|HEATNO|MCNO|MFGDATE|QTY
```

Example: `Globex Inc|PN-7|Gear Housing|B|RC5001|H10|MC1|2026-07-10|50`

Any missing trailing fields are simply left blank so you can also
encode shorter barcodes and finish manually. You can just as easily
type into the same box and press Enter instead of scanning. If your
factory's barcodes use a different layout, edit `SCAN_FIELD_ORDER` /
`parse_scan_payload()` in `app/scan_utils.py`.

(This is separate from the Packing List barcode format used in Tab 5 -
see section 4/5 below.)

## 3. Recommended setup order

1. **Master Registrations > Customer Register** - add each customer.
   Select a row and use **Remove Selected** to delete one (blocked if
   it still has codes/parts/lots referencing it).
2. **Master Registrations > Code Register** - add customer/supplier
   codes with descriptions. Removable the same way (blocked if a part
   still uses that code).
3. **Master Registrations > Part Register** - register every part
   (Customer + Part No + Rev must be unique). A lot **cannot** be
   registered in Tab 1 until its part exists here.
   - **Editing**: click a row in the table to load it into the form
     (even the Part Number itself becomes editable); click **Save
     Part** / **Update Part** to save the change, or **New / Clear**
     to go back to registering a brand new part.
   - **Lot No. Rule**: pick the customer's default CSR rule here - Tab
     4 (Pull Out) pre-selects it automatically for that part.
   - **Remove Selected** deletes a part (blocked if lots exist for it).
4. **Master Registrations > Customer Lot No. (CSR) Register** -
   build the packaging lot-number format per customer by adding
   components **in the exact order they should appear**:
   - **Code (from Code Register)** - pick one of that customer's
     registered codes from the dropdown (this was previously blank
     even when codes existed - now fixed and populated live).
   - **Mfg Date**, **Week No**, **Year** - pull from the first/last
     selected lot, with a choice of formats.
   - **Route Card Lot No** - pull from the first/last selected lot;
     "Keep last N" truncates to the last N characters.
   - **M/C Number** - pull from the first/last selected lot.
   - **Month Code (A-M)** - A=Jan ... M=Dec (I is skipped), based on
     the first/last selected lot's Mfg Date.
   - **Country Code (M/S/T)** - Malaysia/Singapore/Thailand, picked
     once when you configure the rule.
   - **Custom / Separator** - free-text component. This is how you add
     `-`, `/`, or any fixed word, exactly where you want it in the
     sequence - there's no separate global "separator" field anymore;
     just drop a Custom component between any two others.
   - Watch the **Live Preview** update as you configure it, then
     **Save Rule**. **Delete This Rule** removes whichever rule is
     selected in "Existing Rules".
5. **Lot Registry (Tab 1)** - scan or key in daily incoming/WIP lots.
6. **Lot List (Tab 3)** - live inventory view.
   - **Search Part No** filters as you type.
   - **Hide Finished Lots** hides any lot with balance = 0.
   - **Hide Selected Lot / Unhide Selected Lot** manually hides a
     specific lot regardless of balance (e.g. scrap), independent of
     the "finished" filter.
7. **Pull Out (Tab 4)**:
   - Selecting a Part auto-fills its default **Lot No. Rule** from the
     Part Register (you can still override it).
   - Fill in PO / Packaging Qty, click **OK - Find Available Lots**.
   - In the lot picker, tick lots (oldest first / FIFO order). Once
     the running total meets your target quantity, the remaining
     unticked rows **auto-lock**.
   - If total available stock is *less* than your target quantity, you
     can still tick every available lot and confirm - the **Packaging
     Qty auto-adjusts down** to whatever was actually achievable, so
     the record matches reality instead of overstating it.
   - Confirm, review the generated **Packaging Lot Number** preview,
     then **Confirm Pull-Out**.
8. **Pull Out List (Tab 5)**:
   - **Search Part No** and **Hide Completed Lots** filter the table.
   - **Mark Complete / Reopen** closes or reopens a packaging lot.
   - **Generate Packing List (PDF)** - see section 4.
   - **Export to Excel** - writes every source-lot line item of the
     selected pull-out straight into a spreadsheet (see section 5).
   - **Label Scan Station** - scan a barcode straight off a printed
     Packing List and its full details are appended to the same Excel
     file automatically, no retyping.

## 4. Packing List PDF

Each generated PDF has:
- A **master QR code** (top-right) encoding a full summary of the
  packaging lot: customer, part, rev, packaging lot no, PO, packaging
  qty, date, prepared by, and every source lot + qty taken.
- A **Code128 barcode** for the overall packaging lot number.
- One **Code128 barcode per source-lot line item**, each encoding that
  line's *complete* detail set (same fields as the QR, but scoped to
  that specific source lot) - scanning any single row's barcode gives
  packaging staff everything needed for that carton's label with no
  manual lookups.

Because the per-line barcodes now carry many fields instead of just a
lot number, the module width auto-shrinks so the barcode still fits on
the page regardless of payload length. For very data-heavy lines this
makes for a denser barcode - Code128 is generally best kept to short
values, so if handheld scanners struggle with the dense per-line
codes, the QR is the more robust option for a full-detail scan (happy
to switch the per-line codes to short IDs with the QR carrying all the
detail instead, if that works better on your floor).

## 5. Excel export / Label Scan Station (for label-printing software)

Every "Export to Excel" click or physical barcode scan appends a row
to `label_export.xlsx` (or wherever you point it via **Change...**) in
a fixed column layout: Customer, Part No, Part Name, Rev, Packaging
Lot No, PO Number, Packaging Qty, Packaging Date, Prepared By, Source
Lot No, Heat No, M/C No, Mfg Date, Qty Taken.

Point your label software (BarTender, NiceLabel, or similar) at this
file as its data source, and it can pull whichever fields it needs for
the label template - no copy/paste. The payload format is defined once
in `app/label_payload.py` and shared by the PDF barcode/QR generator
and the Excel writer, so what gets printed and what gets logged can
never drift out of sync.

## 6. Project layout

```
lot_management/
├── main.py                     # app entry point, wires the 5 tabs together
├── requirements.txt
├── lot_management.db           # created on first run
├── label_export.xlsx           # created on first Excel export / scan
└── app/
    ├── database.py              # SQLite schema + all CRUD helpers (+ migrations)
    ├── lot_number_generator.py  # rule-based packaging lot-number engine
    ├── label_payload.py         # shared barcode/QR/Excel payload format
    ├── excel_export.py          # Excel append/export for label software
    ├── pdf_generator.py         # packing list PDF, Code128 barcodes + QR
    ├── scan_utils.py            # barcode-scan entry widget & payload parser
    ├── tab1_lot_registry.py
    ├── tab2_master.py           # Part / Customer / Code / CSR sub-tabs
    ├── tab3_lot_list.py
    ├── tab4_pullout.py          # includes the lot-selection auto-lock window
    └── tab5_pullout_list.py
```

## 7. Notes & things you may want to extend

- The database file is local SQLite; for multi-user/networked use
  you'd want to swap it for a client-server database and add a login
  layer - the `database.py` module isolates all SQL so that's a
  contained change.
- Pull-out lot selection currently orders lots FIFO by scan date; if
  you need a different picking strategy (e.g. by heat number), adjust
  `list_lots()` in `database.py`.
