"""Conservative identifier removal; this is not a complete anonymization claim."""
import re
from collections.abc import Iterable

PATTERNS = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?!\d)")),
    ("vin", re.compile(r"\b(?=[A-HJ-NPR-Z0-9*]{17}\b)(?=[A-HJ-NPR-Z0-9*]*\d)[A-HJ-NPR-Z0-9*]{17}\b", re.I)),
    ("vin", re.compile(r"\b(?:VIN|VEHICLE IDENTIFICATION NUMBER)\s*(?:IS|WAS|NUMBER|NO\.?|#|:)?\s*[A-Z0-9*_-]{6,17}\b", re.I)),
    ("address", re.compile(r"\b\d{1,6}\s+(?:[A-Z0-9.'-]+\s+){1,5}(?:STREET|ST|ROAD|RD|AVENUE|AVE|BOULEVARD|BLVD|LANE|LN|DRIVE|DR|COURT|CT|HIGHWAY|HWY)\b[^.;\n]*", re.I)),
    ("name", re.compile(r"\b(?:MY NAME IS|OWNER(?:'S)? NAME\s*:?|CONTACT NAME\s*:?|DRIVER(?:'S)? NAME\s*:?)\s*[A-Z][A-Z .'-]{1,60}", re.I)),
)

_PLACEHOLDERS = {"UNKNOWN", "UNAVAILABLE", "NOT AVAILABLE", "NOT APPLICABLE", "NONE", "NULL", "N/A", "NA"}

def _normalized_values(values: Iterable[str] | None) -> list[str]:
    result = set()
    for value in values or ():
        phrase = re.sub(r"\s+", " ", str(value or "")).strip()
        # Placeholder strings are not identifying values. Real short values still
        # count; conservative suppression can remove a common word such as a city.
        if phrase and phrase.upper() not in _PLACEHOLDERS and re.search(r"[A-Za-z0-9]", phrase):
            result.add(phrase)
    return sorted(result, key=lambda value: (-len(value), value.casefold()))

def _denied_pattern(denied: Iterable[str] | None):
    values = _normalized_values(denied)
    if not values:
        return None
    # Korean summaries attach particles directly to Latin names ("Exampleville에서").
    # Hangul is a Unicode word character, so plain \w boundaries would miss them.
    # Preserve word boundaries for other scripts to avoid matching Normal in Normalville.
    left = r"(?:(?<!\w)|(?<=[가-힣]))"
    right = r"(?:(?!\w)|(?=[가-힣]))"
    parts = [left + re.escape(value).replace(r"\ ", r"\s+") + right for value in values]
    return re.compile("|".join(parts), re.I)

def sensitive_values(con, odinos: Iterable[str]) -> dict[str, list[str]]:
    """Read known identifying values for local redaction only; never serialize them.

    Include every component row of an ODINO, because its dealer contacts may
    differ. Query parameters keep complaint IDs out of executable SQL. Neither
    returned values nor this mapping belong in labels, API metadata, or exports.
    """
    ids = sorted({str(value) for value in odinos})
    result = {odino: [] for odino in ids}
    if not ids:
        return result
    rows = con.execute("""SELECT trim(c02), c15, c13, c41, c42, c43, c51
        FROM complaints_raw WHERE trim(c02) IN (SELECT unnest(?))""", [ids]).fetchall()
    collected = {odino: set() for odino in ids}
    for odino, *values in rows:
        collected[odino].update(_normalized_values(values))
    return {odino: _normalized_values(values) for odino, values in collected.items()}

def privacy_matches(text: str, denied: Iterable[str] | None = None) -> list[str]:
    matches = {name for name, pattern in PATTERNS if pattern.search(text)}
    known = _denied_pattern(denied)
    if known is not None and known.search(text):
        matches.add("known_identifier")
    return sorted(matches)

def redact_text(text: str, limit: int | None = None, *, denied: Iterable[str] | None = None) -> str:
    result = re.sub(r"\s+", " ", str(text or "")).strip()
    known = _denied_pattern(denied)
    if known is not None:
        result = known.sub("[REDACTED IDENTIFIER]", result)
    for name, pattern in PATTERNS:
        result = pattern.sub(f"[REDACTED {name.upper()}]", result)
    return result if limit is None else result[:limit]

def public_text(text: str, limit: int = 520, *, denied: Iterable[str] | None = None) -> str:
    sentences = re.split(r"(?<=[.!?])\s+|[\r\n]+", str(text or ""))
    safe = ["[식별정보가 포함된 문장 생략]" if privacy_matches(s, denied) else s for s in sentences]
    return redact_text(" ".join(safe), limit, denied=denied)
