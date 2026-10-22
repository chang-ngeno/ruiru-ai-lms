"""Safaricom Daraja (M-Pesa Express / STK Push) client.

Docs: https://developer.safaricom.co.ke  (always confirm field names and limits there).
Set MPESA_SIMULATE=true to develop without credentials: no network calls are made.
"""
import base64
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

SANDBOX = "https://sandbox.safaricom.co.ke"
PRODUCTION = "https://api.safaricom.co.ke"
EAT = timezone(timedelta(hours=3))

_token = {"value": None, "expires": 0.0}


PAYBILL = "CustomerPayBillOnline"
BUYGOODS = "CustomerBuyGoodsOnline"


class MpesaError(Exception):
    """Raised for configuration problems or Daraja rejecting a request.

    `detail` keeps Safaricom's own code and message (for admins and logs); `str(exc)` is learner-friendly.
    """

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


def normalize_transaction_type(raw):
    """Accept the exact Daraja value or common spellings (till, buy goods, paybill). None if unrecognised."""
    key = re.sub(r"[^a-z]", "", (raw or "").lower())
    if key in ("customerbuygoodsonline", "buygoodsonline", "buygoods", "till", "tillnumber"):
        return BUYGOODS
    if key in ("customerpaybillonline", "paybillonline", "paybill", ""):
        return PAYBILL
    return None


def explain_rejection(code, desc) -> str:
    """Plain-language hint for the most common Daraja rejections."""
    text = f"{code or ''} {desc or ''}".lower()
    if "transactiontype" in text:
        return "Set MPESA_TRANSACTION_TYPE to CustomerBuyGoodsOnline for a Till (Buy Goods) or CustomerPayBillOnline for a Paybill."
    if "access token" in text or "401" in text:
        return "The consumer key/secret do not match MPESA_ENV (sandbox keys only work with MPESA_ENV=sandbox, production keys with production)."
    if "merchant" in text or "shortcode" in text or "wrong credentials" in text or "initiator" in text:
        return "Check MPESA_SHORTCODE, MPESA_PASSKEY and MPESA_PARTY_B belong together. For a Till: shortcode = the store/head-office number, party B = the Till number, passkey = the one Safaricom issued for that shortcode."
    if "callback" in text:
        return "MPESA_CALLBACK_BASE must be your public https address (no trailing path), and the secret must be set."
    if "phone" in text:
        return "The phone number is not a valid Safaricom number."
    if "amount" in text:
        return "The amount must be a whole number of shillings, at least 1."
    return "See the Safaricom message above; check the shortcode, passkey, transaction type and environment."


def effective_settings():
    """Normalised product settings used for every request. Raises MpesaError for settings that cannot work."""
    ttype = normalize_transaction_type(_cfg("MPESA_TRANSACTION_TYPE"))
    if ttype is None:
        raise MpesaError("M-Pesa settings are incomplete. Please contact your trainer.",
                         detail=f"MPESA_TRANSACTION_TYPE '{_cfg('MPESA_TRANSACTION_TYPE')}' is not valid. Use CustomerBuyGoodsOnline (Till) or CustomerPayBillOnline (Paybill).")
    shortcode = _cfg("MPESA_SHORTCODE")
    party_b = _cfg("MPESA_PARTY_B") or ""
    if ttype == BUYGOODS:
        if not party_b:
            raise MpesaError("M-Pesa settings are incomplete. Please contact your trainer.",
                             detail="Buy Goods needs MPESA_PARTY_B = your Till number (MPESA_SHORTCODE is the store / head-office number).")
    else:
        party_b = shortcode  # for a Paybill the receiving party is the shortcode itself
    return {"transaction_type": ttype, "shortcode": shortcode, "party_b": party_b}


def _cfg(key):
    return current_app.config[key]


def base_url() -> str:
    return PRODUCTION if _cfg("MPESA_ENV") == "production" else SANDBOX


def timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now(EAT)).astimezone(EAT).strftime("%Y%m%d%H%M%S")


def password(shortcode: str, passkey: str, ts: str) -> str:
    return base64.b64encode(f"{shortcode}{passkey}{ts}".encode()).decode()


def configured() -> bool:
    if _cfg("MPESA_SIMULATE"):
        return True
    return all(_cfg(k) for k in ("MPESA_CONSUMER_KEY", "MPESA_CONSUMER_SECRET", "MPESA_SHORTCODE", "MPESA_PASSKEY", "MPESA_CALLBACK_BASE", "MPESA_CALLBACK_SECRET"))


def callback_url() -> str:
    return f"{_cfg('MPESA_CALLBACK_BASE').rstrip('/')}/api/mpesa/callback/{_cfg('MPESA_CALLBACK_SECRET')}"


def _access_token() -> str:
    if _token["value"] and time.time() < _token["expires"]:
        return _token["value"]
    try:
        r = requests.get(
            f"{base_url()}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=(_cfg("MPESA_CONSUMER_KEY"), _cfg("MPESA_CONSUMER_SECRET")),
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        _token["value"] = data["access_token"]
        _token["expires"] = time.time() + int(data.get("expires_in", 3599)) - 60
        return _token["value"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise MpesaError("We could not start the M-Pesa payment. Please tell your trainer.",
                         detail=f"Could not get an access token from {base_url()} ({type(exc).__name__}). Hint: {explain_rejection('access token', '')}") from exc


def _post(path: str, payload: dict) -> dict:
    try:
        r = requests.post(
            f"{base_url()}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {_access_token()}"},
            timeout=30,
        )
        try:
            data = r.json()
        except ValueError:
            data = {}
        return {"http": r.status_code, **data}
    except requests.RequestException as exc:
        raise MpesaError("M-Pesa could not be reached. Please try again.") from exc


def stk_push(phone: str, amount: int, account_ref: str, description: str) -> dict:
    """Ask Safaricom to prompt the customer's phone. Returns merchant/checkout request ids."""
    if _cfg("MPESA_SIMULATE"):
        return {"merchant_request_id": "SIM-" + uuid.uuid4().hex[:10], "checkout_request_id": "ws_CO_SIM_" + uuid.uuid4().hex[:16], "message": "Simulated"}
    if not configured():
        raise MpesaError("M-Pesa is not configured on the server yet.")
    ts = timestamp()
    s = effective_settings()
    shortcode = s["shortcode"]
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password(shortcode, _cfg("MPESA_PASSKEY"), ts),
        "Timestamp": ts,
        "TransactionType": s["transaction_type"],  # CustomerPayBillOnline or CustomerBuyGoodsOnline
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": s["party_b"],  # Till number for Buy Goods, otherwise the shortcode
        "PhoneNumber": phone,
        "CallBackURL": callback_url(),
        "AccountReference": account_ref[:12],
        "TransactionDesc": description[:13],
    }
    data = _post("/mpesa/stkpush/v1/processrequest", payload)
    if str(data.get("ResponseCode")) != "0":
        code = data.get("errorCode") or data.get("ResponseCode") or data.get("http")
        desc = data.get("errorMessage") or data.get("ResponseDescription") or data.get("CustomerMessage") or ""
        current_app.logger.warning("STK push rejected: http=%s code=%s desc=%s type=%s env=%s", data.get("http"), code, desc, s["transaction_type"], _cfg("MPESA_ENV"))
        raise MpesaError("We could not start the M-Pesa payment. Please try again, and tell your trainer if it keeps failing.",
                         detail=f"Safaricom said: {code} {desc}".strip() + f" | Hint: {explain_rejection(code, desc)}")
    return {"merchant_request_id": data.get("MerchantRequestID"), "checkout_request_id": data.get("CheckoutRequestID"), "message": data.get("CustomerMessage", "")}


def stk_query(checkout_request_id: str) -> dict:
    """Ask Safaricom what happened to a push. Returns {'state': 'success'|'failed'|'pending', 'code', 'desc'}."""
    if _cfg("MPESA_SIMULATE"):
        return {"state": "pending", "code": None, "desc": "Simulated"}
    ts = timestamp()
    shortcode = _cfg("MPESA_SHORTCODE")
    data = _post(
        "/mpesa/stkpushquery/v1/query",
        {
            "BusinessShortCode": shortcode,
            "Password": password(shortcode, _cfg("MPESA_PASSKEY"), ts),
            "Timestamp": ts,
            "CheckoutRequestID": checkout_request_id,
        },
    )
    return interpret_query(data)


def interpret_query(data: dict) -> dict:
    """While Safaricom is still processing it answers with an errorCode and no ResultCode."""
    if "ResultCode" not in data:
        return {"state": "pending", "code": data.get("errorCode"), "desc": data.get("errorMessage") or "Still processing"}
    code = str(data.get("ResultCode"))
    return {"state": "success" if code == "0" else "failed", "code": code, "desc": data.get("ResultDesc", "")}


def parse_callback(body) -> dict | None:
    """Extract the useful fields from Safaricom's STK callback JSON. None if the shape is wrong."""
    try:
        cb = body["Body"]["stkCallback"]
        out = {
            "merchant_request_id": cb.get("MerchantRequestID"),
            "checkout_request_id": cb["CheckoutRequestID"],
            "result_code": int(cb["ResultCode"]),
            "result_desc": str(cb.get("ResultDesc", "")),
            "amount": None,
            "receipt": None,
            "phone": None,
        }
        items = (cb.get("CallbackMetadata") or {}).get("Item") or []
        for item in items:
            name, value = item.get("Name"), item.get("Value")
            if name == "Amount" and value is not None:
                out["amount"] = float(value)
            elif name == "MpesaReceiptNumber" and value:
                out["receipt"] = str(value)
            elif name == "PhoneNumber" and value is not None:
                out["phone"] = str(int(value)) if isinstance(value, (int, float)) else str(value)
        return out
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def settings_report() -> dict:
    """Non-secret summary of the M-Pesa setup, with warnings, for the admin screen."""
    c = _cfg
    warnings = []
    ttype = normalize_transaction_type(c("MPESA_TRANSACTION_TYPE"))
    if ttype is None:
        warnings.append("MPESA_TRANSACTION_TYPE is not valid. Use CustomerBuyGoodsOnline (Till) or CustomerPayBillOnline (Paybill).")
    if ttype == BUYGOODS and not c("MPESA_PARTY_B"):
        warnings.append("Buy Goods needs MPESA_PARTY_B = your Till number.")
    if ttype == BUYGOODS and c("MPESA_ENV") != "production":
        warnings.append("Buy Goods STK Push cannot be tested in the Safaricom sandbox; use MPESA_ENV=production with your live Till.")
    if not str(c("MPESA_CALLBACK_BASE")).startswith("https://"):
        warnings.append("MPESA_CALLBACK_BASE must be an https address.")
    for key in ("MPESA_CONSUMER_KEY", "MPESA_CONSUMER_SECRET", "MPESA_SHORTCODE", "MPESA_PASSKEY", "MPESA_CALLBACK_SECRET"):
        if not c(key):
            warnings.append(f"{key} is empty.")
    secret = c("MPESA_CALLBACK_SECRET")
    cb = f"{str(c('MPESA_CALLBACK_BASE')).rstrip('/')}/api/mpesa/callback/{'*' * 6 if secret else '(secret missing)'}"
    return {
        "env": c("MPESA_ENV"), "simulate": bool(c("MPESA_SIMULATE")),
        "product": "Till (Buy Goods)" if ttype == BUYGOODS else "Paybill" if ttype == PAYBILL else "Unknown",
        "transaction_type": ttype or c("MPESA_TRANSACTION_TYPE"),
        "shortcode": c("MPESA_SHORTCODE"), "party_b": c("MPESA_PARTY_B") or ("(same as shortcode)" if ttype == PAYBILL else ""),
        "callback_url": cb, "base_url": base_url(), "warnings": warnings,
    }


def diagnose(phone: str | None, amount: int = 1) -> dict:
    """Admin test: (1) can we get an access token? (2) optionally send a KES 1 prompt to a phone."""
    steps = []
    if c_sim := _cfg("MPESA_SIMULATE"):
        return {"steps": [{"name": "Simulation mode is on, so no request goes to Safaricom.", "ok": True}]}
    try:
        _token["value"] = None  # force a fresh token so key/secret problems show up
        _access_token()
        steps.append({"name": "Authenticate with Safaricom", "ok": True})
    except MpesaError as exc:
        steps.append({"name": "Authenticate with Safaricom", "ok": False, "detail": exc.detail or str(exc)})
        return {"steps": steps}
    if phone:
        try:
            res = stk_push(phone, amount, "TEST", "AI Training")
            steps.append({"name": f"Send a KES {amount} prompt to the phone", "ok": True, "detail": f"Accepted by Safaricom (checkout {res['checkout_request_id']}). Approve it on the phone. This test is not credited to any learner."})
        except MpesaError as exc:
            steps.append({"name": f"Send a KES {amount} prompt to the phone", "ok": False, "detail": exc.detail or str(exc)})
    return {"steps": steps}
