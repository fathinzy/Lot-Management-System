"""
app_paths.py
Works out WHERE the app should read/write its persistent data
(lot_management.db, label_export.xlsx, backups, etc.).

Why this exists
---------------
When the app runs normally as `python main.py`, "next to main.py" is a fine,
stable place to keep the database. But once it's packaged into a one-file
PyInstaller .exe, the code is unpacked into a TEMPORARY folder (sys._MEIPASS)
that Windows DELETES when the app closes. If the database were written there,
every lot the OQC user entered would silently vanish on exit.

So this module decides the data location based on how the app is running:

  * Frozen (running as the packaged .exe): use the folder that CONTAINS the
    .exe. That folder is permanent - it's wherever the user copied the app -
    so the .db sits right next to LotManagementSystem.exe and survives
    restarts and updates.

  * Not frozen (plain `python main.py`): use the project root (the folder that
    contains main.py), exactly like before, so nothing changes for developers.

Everything that needs a data file should build its path from data_dir().
"""
import os
import sys


def is_frozen():
    """True when running inside a PyInstaller-built .exe."""
    return getattr(sys, "frozen", False)


def data_dir():
    """The persistent folder where the app keeps its data files."""
    if is_frozen():
        # sys.executable is the actual .exe path; its folder is permanent.
        return os.path.dirname(os.path.abspath(sys.executable))
    # Dev mode: project root = parent of the app/ package folder.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_path(filename):
    """Absolute path to a data file inside the persistent data folder."""
    return os.path.join(data_dir(), filename)
