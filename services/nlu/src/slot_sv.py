import re
import dateparser
import phonenumbers
from datetime import datetime

RE_EMAIL = re.compile(r"[\w.\+\-]+@[\w\.-]+\.[A-Za-z]{2,}")
RE_TIME = re.compile(r"\b(?:(?:kl\s*)?(\d{1,2})(?::(\d{2}))?)\b", re.IGNORECASE)


def to_iso(dt: datetime) -> str:
    try:
        return dt.isoformat()
    except Exception:
        return None


def parse_datetime_sv(text: str) -> str | None:
    dt = dateparser.parse(text, languages=["sv"])  # bäst-effort
    return to_iso(dt) if dt else None


def extract_slots_sv(text: str) -> dict:
    slots = {}
    # datetime
    iso = parse_datetime_sv(text)
    if iso:
        slots["datetime_iso"] = iso

    # email
    m = RE_EMAIL.search(text)
    if m:
        slots["email"] = m.group(0)

    # phone
    for m in phonenumbers.PhoneNumberMatcher(text, "SE"):
        slots["phone_e164"] = phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
        break

    # person (enkel baseline)
    # Tokens (utan \p{L} som inte stöds av re)
    tokens = [t for t in re.findall(r"\b[A-Za-zÅÄÖåäö]+\b", text)]
    # fallback: leta ett kapitaliserat ord efter "med"
    m = re.search(r"med\s+([A-ZÅÄÖ][a-zåäö]+)", text)
    if m:
        slots["person"] = m.group(1)

    return slots


