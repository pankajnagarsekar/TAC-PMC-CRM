"""
Dependency string parser — handles legacy import formats like '4FF-2d'.

The spec mentions '4FF-2d' as an example predecessor string format that
the engine must parse. These strings appear in MS Project .mpp exports
and Excel schedule imports. Our Pydantic models use structured fields,
but the import pipeline may receive raw strings.

Format spec (MS Project compatible):
    [task_id][type][+/-][lag][unit]
    Examples:
        "3FS"      → task_id=3, type=FS, lag=0
        "4FF-2d"   → task_id=4, type=FF, lag=-2 days
        "5SS+3d"   → task_id=5, type=SS, lag=+3 days
        "6FS+1w"   → task_id=6, type=FS, lag=+5 days (1 working week = 5 days... or 6 on Goa calendar)
        "7"        → task_id=7, type=FS (default), lag=0
        "8FS"      → task_id=8, type=FS, lag=0

Lag units supported: d (days), w (weeks — 6 working days for Goa calendar)
Default: FS with 0 lag when only task_id provided.
"""
import re
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# Parsed result
# =============================================================================

@dataclass
class ParsedPredecessor:
    task_id: str
    dependency_type: str    # FS | SS | FF | SF
    lag_days: int           # working days. Negative = lead.


# =============================================================================
# Constants
# =============================================================================

VALID_TYPES = {"FS", "SS", "FF", "SF"}
DEFAULT_TYPE = "FS"

# Days per working week for Goa construction (Mon-Sat = 6 days)
# When parsing 'w' unit in a Goa calendar context
GOA_WORK_WEEK_DAYS = 6
# Standard MS Project week (Mon-Fri = 5 days) — used as fallback
STANDARD_WORK_WEEK_DAYS = 5

# Regex: captures task_id, optional type, optional sign+number+unit
# Groups: (task_id)(type?)(sign?)(number?)(unit?)
_PRED_PATTERN = re.compile(
    r'^([A-Za-z0-9_\-]+?)'        # task_id (non-greedy, letters/digits/underscores/hyphens)
    r'(FS|SS|FF|SF)?'              # dependency type (optional, defaults to FS)
    r'([+\-]?\d+)?'               # lag value with optional sign (optional)
    r'([dDwW])?$',                 # unit: d=days, w=weeks (optional)
    re.IGNORECASE,
)


# =============================================================================
# Parser
# =============================================================================

def parse_predecessor_string(
    pred_str: str,
    work_week_days: int = GOA_WORK_WEEK_DAYS,
) -> ParsedPredecessor:
    """
    Parses a predecessor string in MS Project format to structured fields.

    Args:
        pred_str: Raw predecessor string, e.g. "4FF-2d", "3FS", "7"
        work_week_days: Number of working days in a week (6 for Goa, 5 for standard).
                        Used to convert 'w' unit to days.

    Returns:
        ParsedPredecessor with task_id, dependency_type, lag_days

    Raises:
        ValueError: If the string cannot be parsed or task_id is empty.

    Examples:
        parse_predecessor_string("4FF-2d") → ParsedPredecessor("4", "FF", -2)
        parse_predecessor_string("3FS+1w") → ParsedPredecessor("3", "FS", 6)
        parse_predecessor_string("7")      → ParsedPredecessor("7", "FS", 0)
    """
    pred_str = pred_str.strip()
    if not pred_str:
        raise ValueError("Empty predecessor string")

    match = _PRED_PATTERN.match(pred_str)
    if not match:
        raise ValueError(
            f"Cannot parse predecessor string '{pred_str}'. "
            f"Expected format: [task_id][FS|SS|FF|SF][+/-][N][d|w] "
            f"e.g. '4FF-2d', '3FS', '7'"
        )

    raw_task_id = match.group(1) or ""
    raw_type    = match.group(2)
    raw_lag     = match.group(3)
    raw_unit    = match.group(4)

    if not raw_task_id:
        raise ValueError(f"No task_id found in predecessor string '{pred_str}'")

    # Dependency type — default FS
    dep_type = raw_type.upper() if raw_type else DEFAULT_TYPE
    if dep_type not in VALID_TYPES:
        raise ValueError(f"Invalid dependency type '{dep_type}' in '{pred_str}'")

    # Lag
    lag_days = 0
    if raw_lag is not None:
        lag_value = int(raw_lag)
        unit = raw_unit.lower() if raw_unit else "d"
        if unit == "w":
            lag_days = lag_value * work_week_days
        else:  # "d" or no unit
            lag_days = lag_value

    return ParsedPredecessor(
        task_id=raw_task_id,
        dependency_type=dep_type,
        lag_days=lag_days,
    )


def parse_predecessor_list(
    pred_strings: list,
    work_week_days: int = GOA_WORK_WEEK_DAYS,
) -> list:
    """
    Parses a list of predecessor strings.
    Returns list of ParsedPredecessor objects.
    Raises ValueError on first parse failure.
    """
    return [parse_predecessor_string(s, work_week_days) for s in pred_strings]


# =============================================================================
# Structured predecessor → string (for export / debugging)
# =============================================================================

def format_predecessor_string(task_id: str, dep_type: str, lag_days: int) -> str:
    """
    Formats a structured predecessor back to MS Project string format.
    Inverse of parse_predecessor_string.

    Examples:
        format_predecessor_string("4", "FF", -2) → "4FF-2d"
        format_predecessor_string("3", "FS", 0)  → "3FS"
        format_predecessor_string("7", "FS", 3)  → "7FS+3d"
    """
    base = f"{task_id}{dep_type}"
    if lag_days == 0:
        return base
    sign = "+" if lag_days > 0 else ""
    return f"{base}{sign}{lag_days}d"
