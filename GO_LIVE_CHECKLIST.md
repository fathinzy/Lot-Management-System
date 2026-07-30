# Lot Management System — Go-Live Checklist
Target completion: end of August 2026 (~5 weeks from July 27)

This covers everything beyond the software itself: infrastructure, data,
process decisions, testing, training, and rollout. Items marked
**[DECIDE THIS WEEK]** block other work if left open — resolve those first.

---

## 1. Infrastructure & Technical Setup

- [ ] **[DECIDE THIS WEEK] Single-PC or multi-PC?** Right now the system is
      one local SQLite file on one machine. If OQC and Packaging need to
      use it from *different* PCs at the same time, that's a real
      architecture change (shared network file has locking risks; a
      proper client-server DB is the correct fix) — decide this before
      anything else, it affects the whole timeline.
- [ ] Identify the actual workstation(s) this will run on (spec check:
      any Windows PC with Python 3.9+ works, but confirm what's available
      on the floor).
- [ ] Package the app as a standalone `.exe` (e.g. via PyInstaller)
      instead of "run `python main.py`" — much friendlier for shop-floor
      staff and avoids needing Python installed on every machine.
- [ ] Confirm/procure USB barcode & QR scanners, and test them against
      the actual Lot Registry scan field and the Packing List Label Scan
      Station — this has only been tested with simulated scan input so far.
- [ ] **[DECIDE THIS WEEK] Which label-printing software** (BarTender,
      NiceLabel, or other) will read `label_export.xlsx`? Get a real
      integration test done early — this has only been validated as a
      correctly-formatted Excel file, not against real label software.
- [ ] Set up a backup routine for `lot_management.db` (e.g. scheduled
      copy to a network drive or shared folder, daily at minimum).
- [ ] Decide where `label_export.xlsx` physically lives if multiple
      people need to read/write it (shared drive vs. local).
- [ ] Confirm a printer is available for the QA Acceptance Lot PDF and
      test an actual print + scan of the QR/barcode off paper (not just
      on-screen) — printer DPI and toner quality affect barcode scan
      reliability.

## 2. Master Data Setup

- [ ] Full list of **Customers** to register.
- [ ] Full list of **Parts** per customer — internal Part Number,
      Customer Part Number, Rev, Material Supplier/Type, Default Lot Qty.
- [ ] Full **Code Register** entries (every customer/supplier code, with
      descriptions) — required before parts can reference them.
- [ ] **[DECIDE THIS WEEK] Real Lot No. (CSR) formats per customer.**
      Everything we've built and tested so far uses placeholder examples.
      Get the *actual* format each customer requires, written down and
      confirmed (ideally with a sample they've approved) before building
      the rule in the system — a wrong lot number on a real shipment is
      a quality escape, not just a bug.
- [ ] Assign the correct **default Lot No. Rule** to every part in Part
      Register.
- [ ] Confirm the exact barcode payload format printed on your real
      incoming-material / route-card labels, and update
      `app/scan_utils.py`'s field order to match if it differs from the
      current assumed pipe-delimited layout.
- [ ] Prepare the bulk-upload Excel (using the built-in template) for
      all parts at once, rather than typing each one in by hand.
- [ ] Opening balances: does existing WIP inventory need to be entered
      as day-one lots, or does the system only track lots from go-live
      forward? Decide and, if needed, prepare that data too.

## 3. Process & Role Decisions

- [ ] Confirm who holds each role in practice: who registers parts
      (Engineer), who scans lots and pulls out (OQC), who scans the
      final QR (Packaging).
- [ ] **Change the Lot No. Rule lock password** from the placeholder
      `12345` to something real, and decide who is authorized to know it.
- [ ] Decide the RTV process *after* a lot is flagged RTV — the system
      records the flag and shows it in Lot List, but doesn't yet drive
      any follow-up workflow (e.g. does it need to notify someone, or
      block that lot from Pull Out?).
- [ ] Decide the fallback process for scanner downtime (manual typing
      into the same fields is already supported — just confirm staff
      know it's an option, not a blocker).
- [ ] Get Quality/Customer Quality sign-off that the QA Acceptance Lot
      PDF format is acceptable as the official packing list document.
- [ ] Confirm each customer's Lot No. Rule with that customer (or your
      internal customer quality contact) before the first real shipment
      using it.

## 4. Testing & Validation

- [ ] User Acceptance Testing (UAT) with the actual people who'll use
      it daily — not just spec-driven testing.
- [ ] Real scanner + real printer end-to-end test: print a QA
      Acceptance Lot PDF, scan the QR/barcode off the physical paper,
      confirm it logs correctly to Excel.
- [ ] Real label-software integration test: confirm your label printer
      software can actually read `label_export.xlsx` and populate a label
      correctly.
- [ ] Volume/realistic-load check: process a full day's worth of lots
      and pull-outs to confirm nothing feels slow or clunky in practice.
- [ ] Dry-run at least one full cycle per customer: Part Register → Lot
      Registry → Pull Out → Packing List → scan, for every distinct Lot
      No. Rule, to catch formatting mistakes before go-live.

## 5. Training & Documentation

- [ ] Train OQC staff: Lot Registry + Pull Out (including what the
      auto-lock and auto-adjust behavior means in practice).
- [ ] Train Packaging staff: Packing List tab, generating the PDF, and
      using the Label Scan Station.
- [ ] Train whoever owns System Registrations: adding
      customers/parts/codes, and building a new Lot No. Rule.
- [ ] Write short, role-specific one-page SOPs (separate from the
      technical README) — one for OQC, one for Packaging, one for the
      System Registrations owner.
- [ ] Designate a system "owner" internally who can answer day-to-day
      questions and handle data fixes without needing a developer.

## 6. Rollout Plan

- [ ] Pick one customer/part combination to pilot first, rather than
      switching everything over at once.
- [ ] Run a parallel period (old process + new system side by side) for
      that pilot before trusting it fully.
- [ ] Set a hard cutover date once the pilot is clean.
- [ ] Have a rollback plan (i.e. keep the old manual process documented
      and ready) in case something needs to be paused post-go-live.

## 7. Support & Maintenance (post go-live)

- [ ] Decide who fixes bugs or handles change requests after go-live —
      you, an internal IT contact, or an ongoing arrangement with me/another
      developer.
- [ ] Set the DB backup schedule as a standing routine, not a one-time
      setup step.
- [ ] Keep a running list of "nice to have next" items (e.g. multi-user
      networked version, additional report types) separate from what's
      needed for go-live, so scope doesn't creep before end of August.

---

## Suggested Week-by-Week Plan (July 27 → Aug 31)

**Week 1 (now – Aug 3):** Resolve the three "decide this week" items
(single/multi-PC architecture, label software choice, real CSR formats
per customer). Package as `.exe`. Confirm hardware on hand.

**Week 2 (Aug 4–10):** Master data entry — customers, parts (bulk
upload), codes, Lot No. Rules built and cross-checked against each
customer's actual required format.

**Week 3 (Aug 11–17):** Full UAT — real scanners, real printer, real
label software integration test, one full cycle per customer's rule.

**Week 4 (Aug 18–24):** Training + SOPs + pilot run with one customer/part.

**Week 5 (Aug 25–31):** Parallel run, fix anything the pilot surfaced,
hard cutover, go live.

**Honest flag:** this is an aggressive but workable timeline *if* the
three Week-1 decisions get made fast and the real CSR formats are
available quickly — that data-gathering step (getting every customer's
correct lot number format confirmed) is usually the slowest part of a
plan like this, not the software itself. Worth starting those
conversations with customer quality contacts this week if you haven't
already.
