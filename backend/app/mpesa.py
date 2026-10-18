"""Safaricom Daraja (M-Pesa Express / STK Push) client.

Docs: https://developer.safaricom.co.ke  (always confirm field names and limits there).
Set MPESA_SIMULATE=true to develop without credentials: no network calls are made.
"""
import base64
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

SANDBOX = "https://sandbox.safaricom.co.ke"
PRODUCTION = "https://api.safaricom.co.ke"
EAT = timezone(timedelta(hours=3))

_token = {"value": None, "expires": 0.0}


class MpesaError(Exception):
    """Raised for configuration problems or Daraja rejecting a request."""


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
        raise MpesaError("Could not authenticate with M-Pesa. Check the consumer key and secret.") from exc


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
    shortcode = _cfg("MPESA_SHORTCODE")
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password(shortcode, _cfg("MPESA_PASSKEY"), ts),
        "Timestamp": ts,
        "TransactionType": _cfg("MPESA_TRANSACTION_TYPE"),  # CustomerPayBillOnline or CustomerBuyGoodsOnline
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": _cfg("MPESA_PARTY_B") or shortcode,  # till number for Buy Goods, otherwise the shortcode
        "PhoneNumber": phone,
        "CallBackURL": callback_url(),
        "AccountReference": account_ref[:12],
        "TransactionDesc": description[:13],
    }
    data = _post("/mpesa/stkpush/v1/processrequest", payload)
    if str(data.get("ResponseCode")) != "0":
        current_app.logger.warning("STK push rejected: http=%s code=%s desc=%s", data.get("http"), data.get("errorCode") or data.get("ResponseCode"), data.get("errorMessage") or data.get("ResponseDescription"))
        raise MpesaError("M-Pesa did not accept the request. Check the phone number and try again.")
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
