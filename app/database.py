"""
database.py
Central SQLite access layer for the Lot Management System.
All tables, schema creation, and CRUD helpers live here so the UI
layer never has to write raw SQL.
"""
import sqlite3
import datetime

from . import app_paths

# Data file lives next to the .exe when packaged (persistent), or next to
# main.py in dev mode - see app_paths.py. Never inside the temp unpack folder.
DB_PATH = app_paths.data_path("lot_management.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    description TEXT,
    UNIQUE(customer_id, code)
);

CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    part_no TEXT NOT NULL,
    customer_part_no TEXT,
    part_name TEXT,
    rev TEXT,
    code_id INTEGER REFERENCES codes(id),
    material_supplier TEXT,
    material_type TEXT,
    default_lot_qty REAL,
    UNIQUE(customer_id, part_no, rev)
);

CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    part_id INTEGER NOT NULL REFERENCES parts(id),
    part_no TEXT,
    part_name TEXT,
    rev TEXT,
    route_card_lot_no TEXT,
    heat_no TEXT,
    mc_no TEXT,
    mfg_date TEXT,
    input_lot_qty REAL,
    date_of_oqc TEXT,
    is_rtv INTEGER DEFAULT 0,
    balance_lot_qty REAL,
    scan_date TEXT,
    last_pullout_date TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS lot_number_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER REFERENCES customers(id),
    rule_name TEXT NOT NULL,
    components_json TEXT NOT NULL,
    separator TEXT DEFAULT '',
    created_at TEXT,
    UNIQUE(customer_id, rule_name)
);

CREATE TABLE IF NOT EXISTS pullouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER REFERENCES customers(id),
    part_id INTEGER REFERENCES parts(id),
    po_number TEXT,
    packaging_qty REAL,
    packaging_date TEXT,
    prepared_by TEXT,
    packaging_lot_no TEXT,
    heat_no TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS pullout_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pullout_id INTEGER REFERENCES pullouts(id) ON DELETE CASCADE,
    lot_id INTEGER REFERENCES lots(id),
    qty_taken REAL
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
    conn.close()


def _migrate(conn):
    """Add columns that were introduced after the original schema, without
    breaking any existing lot_management.db files already in the field."""
    def has_column(table, col):
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return col in cols

    if not has_column("parts", "default_rule_id"):
        conn.execute("ALTER TABLE parts ADD COLUMN default_rule_id INTEGER")
    if not has_column("pullouts", "status"):
        conn.execute("ALTER TABLE pullouts ADD COLUMN status TEXT DEFAULT 'OPEN'")
    if not has_column("lots", "hidden"):
        conn.execute("ALTER TABLE lots ADD COLUMN hidden INTEGER DEFAULT 0")
    if not has_column("lots", "date_of_oqc"):
        conn.execute("ALTER TABLE lots ADD COLUMN date_of_oqc TEXT")
    if not has_column("lots", "is_rtv"):
        conn.execute("ALTER TABLE lots ADD COLUMN is_rtv INTEGER DEFAULT 0")
    if not has_column("pullouts", "heat_no"):
        conn.execute("ALTER TABLE pullouts ADD COLUMN heat_no TEXT")
    if not has_column("parts", "customer_part_no"):
        conn.execute("ALTER TABLE parts ADD COLUMN customer_part_no TEXT")
    conn.commit()


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------- customers
def list_customers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return rows


def add_customer(name):
    conn = get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO customers(name) VALUES (?)", (name,))
        conn.commit()
    finally:
        conn.close()


def get_customer_by_name(name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM customers WHERE name=?", (name,)).fetchone()
    conn.close()
    return row


def delete_customer(customer_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- codes
def list_codes(customer_id=None):
    conn = get_conn()
    if customer_id:
        rows = conn.execute(
            "SELECT * FROM codes WHERE customer_id=? ORDER BY code", (customer_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT codes.*, customers.name as customer_name FROM codes "
            "JOIN customers ON customers.id = codes.customer_id ORDER BY customers.name, code"
        ).fetchall()
    conn.close()
    return rows


def add_code(customer_id, code, description):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO codes(id, customer_id, code, description) "
            "VALUES ((SELECT id FROM codes WHERE customer_id=? AND code=?), ?, ?, ?)",
            (customer_id, code, customer_id, code, description),
        )
        conn.commit()
    finally:
        conn.close()


def delete_code(code_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM codes WHERE id=?", (code_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- parts
def list_parts(customer_id=None):
    conn = get_conn()
    base = ("SELECT parts.*, customers.name as customer_name, codes.code as code_value, "
            "rules.rule_name as default_rule_name "
            "FROM parts JOIN customers ON customers.id = parts.customer_id "
            "LEFT JOIN codes ON codes.id = parts.code_id "
            "LEFT JOIN lot_number_rules rules ON rules.id = parts.default_rule_id ")
    if customer_id:
        rows = conn.execute(base + "WHERE parts.customer_id=? ORDER BY parts.part_no",
                             (customer_id,)).fetchall()
    else:
        rows = conn.execute(base + "ORDER BY customers.name, parts.part_no").fetchall()
    conn.close()
    return rows


def get_part(customer_id, part_no, rev):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM parts WHERE customer_id=? AND part_no=? AND rev=?",
        (customer_id, part_no, rev),
    ).fetchone()
    conn.close()
    return row


def get_part_by_id(part_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM parts WHERE id=?", (part_id,)).fetchone()
    conn.close()
    return row


def find_part_by_any_no(customer_id, typed_value, rev=None):
    """Lot Registry lets the operator type either the internal Part Number
    or the Customer Part Number - this resolves whichever was typed back
    to the canonical part record (and its internal part_no).

    If `rev` is given (e.g. already known from a scanned Route Card QR),
    ONLY an exact part_no+rev match is returned - if that specific
    revision isn't registered, this returns None rather than silently
    falling back to a different revision of the same part (that would
    defeat the entire point of capturing Rev from the scan in the first
    place - a wrong/mistyped Rev must be rejected, not quietly swapped
    for whichever revision happens to be registered).

    The "most recent match, ignoring rev" fallback only applies when no
    rev is known at all (rev=None) - e.g. before any embedded revision
    has been parsed out of a scan."""
    if not typed_value:
        return None
    conn = get_conn()
    if rev:
        row = conn.execute(
            "SELECT * FROM parts WHERE customer_id=? AND (part_no=? OR customer_part_no=?) "
            "AND rev=? ORDER BY id DESC LIMIT 1",
            (customer_id, typed_value, typed_value, rev),
        ).fetchone()
        conn.close()
        return row
    row = conn.execute(
        "SELECT * FROM parts WHERE customer_id=? AND (part_no=? OR customer_part_no=?) "
        "ORDER BY id DESC LIMIT 1",
        (customer_id, typed_value, typed_value),
    ).fetchone()
    conn.close()
    return row


def upsert_part(customer_id, part_no, part_name, rev, code_id, material_supplier,
                 material_type, default_lot_qty, default_rule_id=None, customer_part_no=None):
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM parts WHERE customer_id=? AND part_no=? AND rev=?",
            (customer_id, part_no, rev),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE parts SET part_name=?, code_id=?, material_supplier=?, "
                "material_type=?, default_lot_qty=?, default_rule_id=?, customer_part_no=? "
                "WHERE id=?",
                (part_name, code_id, material_supplier, material_type, default_lot_qty,
                 default_rule_id, customer_part_no, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO parts(customer_id, part_no, customer_part_no, part_name, rev, "
                "code_id, material_supplier, material_type, default_lot_qty, default_rule_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (customer_id, part_no, customer_part_no, part_name, rev, code_id,
                 material_supplier, material_type, default_lot_qty, default_rule_id),
            )
        conn.commit()
    finally:
        conn.close()


def update_part_by_id(part_id, customer_id, part_no, part_name, rev, code_id,
                       material_supplier, material_type, default_lot_qty, default_rule_id,
                       customer_part_no=None):
    """Used by the Part Register edit flow, where the part number/rev itself
    may be changed on an already-registered part."""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE parts SET customer_id=?, part_no=?, customer_part_no=?, part_name=?, "
            "rev=?, code_id=?, material_supplier=?, material_type=?, default_lot_qty=?, "
            "default_rule_id=? WHERE id=?",
            (customer_id, part_no, customer_part_no, part_name, rev, code_id,
             material_supplier, material_type, default_lot_qty, default_rule_id, part_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_part(part_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM parts WHERE id=?", (part_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- lots
def insert_lot(customer_id, part_id, part_no, part_name, rev, route_card_lot_no,
               heat_no, mc_no, mfg_date, input_lot_qty, date_of_oqc=None, is_rtv=False):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO lots(customer_id, part_id, part_no, part_name, rev, "
            "route_card_lot_no, heat_no, mc_no, mfg_date, input_lot_qty, date_of_oqc, "
            "is_rtv, balance_lot_qty, scan_date, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (customer_id, part_id, part_no, part_name, rev, route_card_lot_no, heat_no,
             mc_no, mfg_date, input_lot_qty, date_of_oqc, 1 if is_rtv else 0,
             input_lot_qty, today_str(), "ACTIVE", now_str()),
        )
        conn.commit()
    finally:
        conn.close()


def list_lots(customer_id=None, part_no=None, rev=None, only_available=False,
              include_hidden=True, part_no_search=None):
    conn = get_conn()
    q = ("SELECT lots.*, customers.name as customer_name FROM lots "
         "JOIN customers ON customers.id = lots.customer_id WHERE 1=1")
    params = []
    if customer_id:
        q += " AND lots.customer_id=?"
        params.append(customer_id)
    if part_no:
        q += " AND lots.part_no=?"
        params.append(part_no)
    if part_no_search:
        q += " AND lots.part_no LIKE ?"
        params.append(f"%{part_no_search}%")
    if rev:
        q += " AND lots.rev=?"
        params.append(rev)
    if only_available:
        q += " AND lots.balance_lot_qty > 0"
    if not include_hidden:
        q += " AND (lots.hidden IS NULL OR lots.hidden=0)"
    q += " ORDER BY lots.scan_date ASC, lots.id ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def set_lot_hidden(lot_id, hidden):
    conn = get_conn()
    try:
        conn.execute("UPDATE lots SET hidden=? WHERE id=?", (1 if hidden else 0, lot_id))
        conn.commit()
    finally:
        conn.close()


def deduct_lot_qty(lot_id, qty, pullout_date):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE lots SET balance_lot_qty = balance_lot_qty - ?, last_pullout_date=? "
            "WHERE id=?", (qty, pullout_date, lot_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- lot number rules
def list_rules(customer_id=None):
    conn = get_conn()
    if customer_id:
        rows = conn.execute(
            "SELECT * FROM lot_number_rules WHERE customer_id=? ORDER BY rule_name",
            (customer_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM lot_number_rules ORDER BY rule_name").fetchall()
    conn.close()
    return rows


def upsert_rule(customer_id, rule_name, components_json, separator):
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM lot_number_rules WHERE customer_id=? AND rule_name=?",
            (customer_id, rule_name),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE lot_number_rules SET components_json=?, separator=? WHERE id=?",
                (components_json, separator, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO lot_number_rules(customer_id, rule_name, components_json, "
                "separator, created_at) VALUES (?,?,?,?,?)",
                (customer_id, rule_name, components_json, separator, now_str()),
            )
        conn.commit()
    finally:
        conn.close()


def delete_rule(rule_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM lot_number_rules WHERE id=?", (rule_id,))
        conn.commit()
    finally:
        conn.close()


def get_rule_by_id(rule_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM lot_number_rules WHERE id=?", (rule_id,)).fetchone()
    conn.close()
    return row


# ---------------------------------------------------------------- pullouts
def create_pullout(customer_id, part_id, po_number, packaging_qty, packaging_date,
                    prepared_by, packaging_lot_no, lot_allocations, heat_no=None):
    """lot_allocations: list of (lot_id, qty_taken)"""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO pullouts(customer_id, part_id, po_number, packaging_qty, "
            "packaging_date, prepared_by, packaging_lot_no, heat_no, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (customer_id, part_id, po_number, packaging_qty, packaging_date, prepared_by,
             packaging_lot_no, heat_no, now_str()),
        )
        pullout_id = cur.lastrowid
        for lot_id, qty in lot_allocations:
            conn.execute(
                "INSERT INTO pullout_lots(pullout_id, lot_id, qty_taken) VALUES (?,?,?)",
                (pullout_id, lot_id, qty),
            )
            conn.execute(
                "UPDATE lots SET balance_lot_qty = balance_lot_qty - ?, last_pullout_date=? "
                "WHERE id=?", (qty, packaging_date, lot_id),
            )
        conn.commit()
    finally:
        conn.close()
    return pullout_id


def list_pullouts(part_no_search=None, hide_completed=False):
    conn = get_conn()
    q = ("SELECT pullouts.*, customers.name as customer_name, parts.part_no, parts.rev, "
         "parts.customer_part_no "
         "FROM pullouts JOIN customers ON customers.id = pullouts.customer_id "
         "JOIN parts ON parts.id = pullouts.part_id WHERE 1=1")
    params = []
    if part_no_search:
        q += " AND (parts.part_no LIKE ? OR parts.customer_part_no LIKE ?)"
        params.append(f"%{part_no_search}%")
        params.append(f"%{part_no_search}%")
    if hide_completed:
        q += " AND (pullouts.status IS NULL OR pullouts.status != 'COMPLETE')"
    q += " ORDER BY pullouts.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def set_pullout_status(pullout_id, status):
    conn = get_conn()
    try:
        conn.execute("UPDATE pullouts SET status=? WHERE id=?", (status, pullout_id))
        conn.commit()
    finally:
        conn.close()


def get_pullout_lots(pullout_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT pullout_lots.*, lots.route_card_lot_no, lots.heat_no, lots.mc_no, "
        "lots.mfg_date, lots.part_no, lots.part_name, lots.rev "
        "FROM pullout_lots JOIN lots ON lots.id = pullout_lots.lot_id "
        "WHERE pullout_id=?", (pullout_id,),
    ).fetchall()
    conn.close()
    return rows


def get_pullout(pullout_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT pullouts.*, customers.name as customer_name, parts.part_no, parts.rev, "
        "parts.customer_part_no "
        "FROM pullouts JOIN customers ON customers.id = pullouts.customer_id "
        "JOIN parts ON parts.id = pullouts.part_id WHERE pullouts.id=?", (pullout_id,)
    ).fetchone()
    conn.close()
    return row
