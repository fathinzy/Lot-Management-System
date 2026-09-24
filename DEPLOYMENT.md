# Deploying the Lot Management System to an OQC Laptop

This explains how to turn the app into a single double-clickable program and
put it on a laptop for a non-technical user. There are two roles here:

- **You (the builder)** — do the one-time build on any PC that has Python.
- **The OQC user** — just double-clicks the app. No Python, no setup.

---

## Part 1 — Build the .exe (you, once)

Do this on any Windows PC that has **Python 3.9+** installed (it can be your
own machine — it does **not** have to be an OQC laptop).

1. Open the project folder (`Lot-Management-System`).
2. Double-click **`build.bat`**.
   - It installs what it needs and builds the app. Takes a couple of minutes.
   - If it says Python wasn't found, install Python from
     <https://www.python.org/downloads/> (tick **"Add python.exe to PATH"**),
     then run `build.bat` again.
3. When it finishes, you'll have a new folder:

   ```
   dist\LotManagementSystem\
       LotManagementSystem.exe      <- the program
       _internal\                   <- supporting files (don't touch)
   ```

That `LotManagementSystem` folder **is** the app.

---

## Part 2 — Install it on an OQC laptop (you)

1. Copy the **whole `LotManagementSystem` folder** (from `dist\`) onto the
   OQC laptop — e.g. to `C:\LotManagementSystem`.
   - Copy the *entire folder*, not just the .exe. The .exe needs the
     `_internal` folder next to it.
2. (Optional, nice for the user) Right-click `LotManagementSystem.exe` →
   **Send to → Desktop (create shortcut)**. Rename the shortcut to something
   like "Lot Management System". Now they have an icon on the desktop.

That's it. Nothing else needs installing on the laptop — no Python.

---

## Part 3 — Using it (the OQC user)

- Double-click **LotManagementSystem.exe** (or the desktop shortcut).
- The first time it runs, it creates its database file, **`lot_management.db`**,
  right inside the `LotManagementSystem` folder, next to the .exe. All the
  lots, parts, customers, and pull-outs live in that one file.
- Close and reopen any time — the data stays.

---

## Where the data lives (important)

Everything the user enters is saved in:

```
C:\LotManagementSystem\lot_management.db
```

(next to the .exe — wherever you copied the folder). The label export file,
`label_export.xlsx`, is created in the same folder the first time it's used.

**Because all the data is in that one `.db` file, back it up.** If the laptop
dies, the data dies with it unless you have a copy.

- There's a `backup_db.bat` in the source project you can adapt to copy
  `lot_management.db` to a network drive or the NAS on a schedule.
- Even a manual weekly copy of `lot_management.db` to a shared folder is a
  big safety net.

---

## Updating the app later

When you make code changes and want to push a new version:

1. Run `build.bat` again on the build PC.
2. On the OQC laptop, replace the program files **but keep their data**:
   - Copy the **new** `LotManagementSystem.exe` and the **new** `_internal`
     folder over the old ones.
   - **Do NOT delete `lot_management.db`** — that's their data. Leave it in
     place and it'll be picked up by the new version automatically (the app
     upgrades the database format safely on first run).

A safe habit: copy `lot_management.db` somewhere first, then update.

---

## Troubleshooting

- **Windows SmartScreen warning ("Windows protected your PC")** — because the
  .exe isn't code-signed, Windows may warn on first launch. Click **More info
  → Run anyway**. This is expected for an in-house tool. (Code-signing removes
  the warning but needs a paid certificate — optional, not required.)
- **Antivirus flags it** — PyInstaller apps sometimes trigger a false
  positive. Add an exclusion for the `LotManagementSystem` folder, or have IT
  whitelist it.
- **"Missing DLL" / won't start** — make sure the *whole* folder was copied,
  including `_internal`. The .exe can't run by itself.
- **Data seems to reset** — check they're always launching the same copy of
  the app (same folder). Two copies in two places = two separate databases.
