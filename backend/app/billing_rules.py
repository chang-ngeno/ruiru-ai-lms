"""Pure billing rules (no database, no network) so they are easy to test."""
import math
import re

PHONE_RE = re.compile(r"^254([71]\d{8})$")


def normalize_phone(raw) -> str | None:
    """Return a Safaricom MSISDN like 2547XXXXXXXX, or None if the input is not valid."""
    if raw is None:
        return None
    digits = re.sub(r"[\s\-()]", "", str(raw))
    if digits.startswith("+"):
        digits = digits[1:]
    if re.fullmatch(r"0[71]\d{8}", digits):
        digits = "254" + digits[1:]
    elif re.fullmatch(r"[71]\d{8}", digits):
        digits = "254" + digits
    return digits if PHONE_RE.match(digits) else None


def discount_amount(price: int, kind: str, value: int) -> int:
    """KES taken off `price` by a percent or fixed discount. Never negative, never above price."""
    price = max(0, int(price))
    value = max(0, int(value))
    if kind == "percent":
        value = min(value, 100)
        amount = round(price * value / 100)
    elif kind == "fixed":
        amount = value
    else:
        raise ValueError("kind must be 'percent' or 'fixed'")
    return min(price, amount)


def net_price(price: int, discount_kes: int) -> int:
    return max(0, int(price) - max(0, int(discount_kes)))


def unlocked_weeks(paid: int, net: int, total_weeks: int) -> int:
    """Each equal share of the net price paid opens one more week. Fully paid opens all."""
    if total_weeks <= 0:
        return 0
    if net <= 0 or paid >= net:
        return total_weeks
    return max(0, min(total_weeks, (paid * total_weeks) // net))


def amount_for_week(week: int, net: int, total_weeks: int) -> int:
    """Total paid needed to open `week` (1-based)."""
    if week >= total_weeks:
        return net
    return math.ceil(net * week / total_weeks)


def suggested_payments(paid: int, net: int, total_weeks: int, min_payment: int) -> list[dict]:
    """Handy amounts for the pay screen: next week, next two weeks, remaining balance."""
    balance = max(0, net - paid)
    if balance <= 0:
        return []
    weeks_open = unlocked_weeks(paid, net, total_weeks)
    out, seen = [], set()
    for step in (1, 2):
        target_week = weeks_open + step
        if target_week > total_weeks:
            break
        amount = max(min_payment, amount_for_week(target_week, net, total_weeks) - paid)
        amount = min(amount, balance)
        if amount not in seen:
            seen.add(amount)
            out.append({"label": f"Unlock Week {target_week}" if step == 1 else f"Unlock up to Week {target_week}", "amount": amount})
    if balance not in seen:
        out.append({"label": "Pay the full balance", "amount": balance})
    return out


def lesson_unlocked(lesson_number: int, lesson_week: int, open_weeks: int, preview_lessons: int = 1) -> bool:
    return lesson_number <= preview_lessons or lesson_week <= open_weeks


def refund_policy(started: bool, days_since_first_payment: float, refundable: int,
                  partial_days: int = 3, partial_percent: int = 50) -> tuple[str, int]:
    """Suggested refund. The admin always makes the final decision.

    full    : the learner has not started any paid lesson yet -> everything refundable
    partial : started, but within `partial_days` of the first payment -> `partial_percent` of it
    none    : later than that
    """
    refundable = max(0, int(refundable))
    if refundable == 0:
        return "none", 0
    if not started:
        return "full", refundable
    if days_since_first_payment <= partial_days:
        return "partial", round(refundable * min(100, max(0, partial_percent)) / 100)
    return "none", 0


def _b36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if n == 0:
            return out


def workspace_code(user_id: int, secret: str) -> str:
    """A stable pass code the learner shows (as text or QR) at the door. Cannot be forged without the secret."""
    import hashlib
    import hmac

    sig = hmac.new(secret.encode(), f"workspace:{user_id}".encode(), hashlib.sha256).hexdigest()[:8].upper()
    return f"WS-{_b36(user_id).upper()}-{sig}"


def decode_workspace_code(code: str, secret: str) -> int | None:
    """User id from a pass code, or None if the code is malformed or the signature is wrong."""
    import hmac

    parts = (code or "").strip().upper().split("-")
    if len(parts) != 3 or parts[0] != "WS":
        return None
    try:
        user_id = int(parts[1], 36)
    except ValueError:
        return None
    expected = workspace_code(user_id, secret)
    return user_id if hmac.compare_digest(expected, "-".join(parts)) else None


def csv_safe(value) -> str:
    """Stop spreadsheet formula injection: a cell starting with = + - @ would run as a formula in Excel."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text
