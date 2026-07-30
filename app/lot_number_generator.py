"""
lot_number_generator.py
Dynamic, rule-based Customer Lot Number generator (Tab 2 / Sub-tab 4).

A "rule" is an ordered list of component dicts, each shaped like:
    {
        "type": "code" | "mfg_date" | "route_card_lot_no" | "mc_no"
                | "week_no" | "year" | "po_number" | "literal"
                | "month_code" | "country",
        "format": <string, meaning depends on type>,
        "source": "last" | "first" | <int index into selected lots>,
        "keep_last_n": <int, only used by route_card_lot_no>,
        "value": <the specific registered code for "code", the letter code
                  for "country", or free text for "literal">,
    }

"literal" doubles as the free-text / separator component: put "-", "/",
a fixed word, or anything else in its value and place it anywhere in the
component order to control exactly how the final lot number is punctuated.

`generate()` combines these components (in order, back to back - any
separator must be its own "literal" component) using the list of lots
that were selected for a pull-out, plus the PO number captured at
pull-out time.
"""
import datetime
import json

VALID_TYPES = [
    "code", "mfg_date", "route_card_lot_no", "mc_no",
    "week_no", "year", "po_number", "literal", "month_code", "country",
    "oqc_date", "oqc_date2",
]

# Human-friendly labels shown in the UI dropdown, keyed by internal type.
TYPE_LABELS = {
    "code": "Code (from Code Register)",
    "mfg_date": "Mfg Date",
    "route_card_lot_no": "Route Card Lot No",
    "mc_no": "M/C Number",
    "week_no": "Week No",
    "year": "Year",
    "po_number": "PO Number",
    "month_code": "Month Code (A-M)",
    "country": "Country Code (M/S/T)",
    "oqc_date": "Date of OQC",
    "oqc_date2": "Date of OQC 2 (Day Code)",
    "literal": "Custom / Separator (type anything)",
}

# Date of OQC 2: day-of-week letter code. A=Mon, B=Tue, C=Wed, D=Thu,
# E=Fri, F=Sat or Sun. G is used when there's no usable OQC date on the
# lot (i.e. it hasn't been through normal OQC yet) to flag it as Rework.
OQC_DAY_CODE_MAP = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "F"}
OQC_DAY_CODE_REWORK = "G"

# Shared format options for any full-date component (Mfg Date, Date of OQC).
DATE_FORMAT_OPTIONS = [
    "YYYYMMDD", "DDMMYYYY", "YYMMDD", "YYYY-MM-DD",
    "D", "DD", "M", "MM", "MMM", "YY", "YYYY",
]

# Manufacturing month letter code: A-H then J,K,L,M (I is skipped, as is
# common practice in date/lot coding to avoid confusion with the digit 1).
MONTH_CODE_MAP = {
    1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F",
    7: "G", 8: "H", 9: "J", 10: "K", 11: "L", 12: "M",
}

COUNTRY_CODE_MAP = {
    "Malaysia": "M",
    "Singapore": "S",
    "Thailand": "T",
}
COUNTRY_DISPLAY_OPTIONS = [f"{name} ({code})" for name, code in COUNTRY_CODE_MAP.items()]

DEFAULT_COMPONENT = {
    "type": "code",
    "format": "",
    "source": "last",
    "keep_last_n": None,
    "value": "",
}


def _parse_date(date_str):
    """Dates are stored as YYYY-MM-DD text; be lenient about other formats."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


# Kept as an alias since earlier versions of this module called it this way.
_parse_mfg_date = _parse_date


def _format_date(d, fmt):
    if not d:
        return ""
    mapping = {
        "YYYYMMDD": d.strftime("%Y%m%d"),
        "DDMMYYYY": d.strftime("%d%m%Y"),
        "YYMMDD": d.strftime("%y%m%d"),
        "YYYY-MM-DD": d.strftime("%Y-%m-%d"),
        "D": str(d.day),
        "DD": f"{d.day:02d}",
        "M": str(d.month),
        "MM": f"{d.month:02d}",
        "MMM": d.strftime("%b"),
        "YY": d.strftime("%y"),
        "YYYY": d.strftime("%Y"),
    }
    return mapping.get(fmt, d.strftime("%Y%m%d"))


def _pick_source_lot(component, lots):
    """lots: ordered list of dict-like lot rows (order = selection order)."""
    if not lots:
        return None
    source = component.get("source", "last")
    if source == "last":
        return lots[-1]
    if source == "first":
        return lots[0]
    try:
        idx = int(source)
        return lots[idx]
    except (ValueError, TypeError, IndexError):
        return lots[-1]


def _render_component(component, lots, po_number, code_value):
    ctype = component.get("type")

    if ctype == "literal":
        return component.get("value", "") or ""

    if ctype == "code":
        # A rule can pin a specific registered code (component["value"]);
        # if the operator left it unset, fall back to whatever code is
        # tied to the part being pulled out.
        return component.get("value") or code_value or ""

    if ctype == "po_number":
        return po_number or ""

    if ctype == "country":
        return component.get("value") or ""

    if ctype == "mfg_date":
        lot = _pick_source_lot(component, lots)
        d = _parse_date(lot["mfg_date"]) if lot else None
        if not d:
            return ""
        fmt = component.get("format") or "YYYYMMDD"
        return _format_date(d, fmt)

    if ctype == "oqc_date":
        lot = _pick_source_lot(component, lots)
        raw = None
        if lot is not None:
            try:
                raw = lot["date_of_oqc"]
            except (KeyError, IndexError):
                raw = None
        d = _parse_date(raw) if raw else None
        if not d:
            return ""
        fmt = component.get("format") or "YYYYMMDD"
        return _format_date(d, fmt)

    if ctype == "oqc_date2":
        lot = _pick_source_lot(component, lots)
        raw = None
        if lot is not None:
            try:
                raw = lot["date_of_oqc"]
            except (KeyError, IndexError):
                raw = None
        d = _parse_date(raw) if raw else None
        if not d:
            # No usable OQC date on this lot - treat as Rework.
            return OQC_DAY_CODE_REWORK
        return OQC_DAY_CODE_MAP.get(d.weekday(), OQC_DAY_CODE_REWORK)

    if ctype == "route_card_lot_no":
        lot = _pick_source_lot(component, lots)
        val = (lot["route_card_lot_no"] or "") if lot else ""
        keep_n = component.get("keep_last_n")
        if keep_n:
            try:
                keep_n = int(keep_n)
                if keep_n > 0:
                    val = val[-keep_n:]
            except (ValueError, TypeError):
                pass
        return val

    if ctype == "mc_no":
        lot = _pick_source_lot(component, lots)
        return (lot["mc_no"] or "") if lot else ""

    if ctype == "week_no":
        lot = _pick_source_lot(component, lots)
        d = _parse_mfg_date(lot["mfg_date"]) if lot else None
        if not d:
            return ""
        week = d.isocalendar()[1]
        fmt = component.get("format") or "W12"
        return f"W{week:02d}" if fmt == "W12" else f"{week:02d}"

    if ctype == "year":
        lot = _pick_source_lot(component, lots)
        d = _parse_mfg_date(lot["mfg_date"]) if lot else None
        if not d:
            return ""
        fmt = component.get("format") or "2025"
        yr_full = d.strftime("%Y")
        yr_short = d.strftime("%y")
        return {
            "2025": yr_full,
            "25": yr_short,
            "Y25": f"Y{yr_short}",
            "Y2025": f"Y{yr_full}",
        }.get(fmt, yr_full)

    if ctype == "month_code":
        lot = _pick_source_lot(component, lots)
        d = _parse_mfg_date(lot["mfg_date"]) if lot else None
        if not d:
            return ""
        return MONTH_CODE_MAP.get(d.month, "")

    return ""


def generate(components, lots, po_number="", code_value="", separator=""):
    """
    components: list of component dicts (see module docstring)
    lots: ordered list of sqlite3.Row / dict lot records that were selected
          for this pull-out, in the order they were picked
    po_number: string captured during pull-out
    code_value: resolved customer/part code string (fallback for a "code"
                component that doesn't pin its own value)
    separator: optional string inserted between every rendered component.
               Leave this "" and use "literal" components instead if you
               want separators only in specific spots (e.g. only after the
               code, not after the date).
    """
    parts = [_render_component(c, lots, po_number, code_value) for c in components]
    parts = [p for p in parts if p != ""]
    return (separator or "").join(parts)


def components_to_json(components):
    return json.dumps(components)


def components_from_json(s):
    if not s:
        return []
    return json.loads(s)
