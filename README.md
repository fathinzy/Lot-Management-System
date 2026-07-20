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
other file.

## 2. How the barcode scanner works

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
type into the same box and press Enter instead of scanning - useful
for testing or manual fallback. If your factory's barcodes use a
different layout, edit `SCAN_FIELD_ORDER` / `parse_scan_payload()` in
`app/scan_utils.py`.

## 3. Recommended setup order

1. **Master Registrations > Customer Register** - add each customer.
2. **Master Registrations > Code Register** - add customer/supplier
   codes with descriptions.
3. **Master Registrations > Part Register** - register every part
   (Customer + Part No + Rev must be unique). A lot **cannot** be
   registered in Tab 1 until its part exists here.
4. **Master Registrations > Customer Lot No. (CSR) Register** -
   build the packaging lot-number format per customer:
   - Add components in the order they should appear in the final
     number (Code, Mfg Date, Route Card Lot No, M/C Number, Week No,
     Year, PO Number, or a fixed Literal string).
   - Each component can pull from the `first` or `last` selected lot
     (multi-lot merges default to the *last* lot, per spec).
   - `Route Card Lot No` supports "Keep last N" to truncate to the
     last N characters.
   - Watch the **Live Preview** update as you configure it, then
     **Save Rule**.
5. **Lot Registry (Tab 1)** - scan or key in daily incoming/WIP lots.
6. **Lot List (Tab 3)** - live inventory view; balances update
   automatically after pull-outs.
7. **Pull Out (Tab 4)**:
   - Fill in Customer / Part / PO / Packaging Qty / Rule, click
     **OK - Find Available Lots**.
   - In the lot picker, tick lots (oldest first / FIFO order). Once
     the running total meets your target quantity, the remaining
     unticked rows **auto-lock** so you can't over-select - e.g. a
     650 pc target against 100 pc lots locks you to exactly 7 lots.
   - Confirm the selection, review the generated **Packaging Lot
     Number** preview, then **Confirm Pull-Out**. Lot balances are
     deducted automatically (the last lot only takes what's needed).
8. **Pull Out List (Tab 5)** - full history. Select a row and click
   **Generate Packing List (PDF)** to produce a PDF where every line
   item (each source lot) carries its own scannable Code128 barcode,
   plus one barcode for the overall packaging lot number.

## 4. Project layout

```
lot_management/
├── main.py                     # app entry point, wires the 5 tabs together
├── requirements.txt
├── lot_management.db           # created on first run
└── app/
    ├── database.py              # SQLite schema + all CRUD helpers
    ├── lot_number_generator.py  # rule-based packaging lot-number engine
    ├── pdf_generator.py         # packing list PDF + Code128 barcodes
    ├── scan_utils.py            # barcode-scan entry widget & payload parser
    ├── tab1_lot_registry.py
    ├── tab2_master.py           # Part / Customer / Code / CSR sub-tabs
    ├── tab3_lot_list.py
    ├── tab4_pullout.py          # includes the lot-selection auto-lock window
    └── tab5_pullout_list.py
```

## 5. Notes & things you may want to extend

- The database file is local SQLite; for multi-user/networked use
  you'd want to swap it for a client-server database and add a login
  layer - the `database.py` module isolates all SQL so that's a
  contained change.
- Pull-out lot selection currently orders lots FIFO by scan date; if
  you need a different picking strategy (e.g. by heat number), adjust
  `list_lots()` in `database.py`.
- The barcode scan payload format is a reasonable default - update it
  in `app/scan_utils.py` to match whatever your route-card/box labels
  actually encode.
