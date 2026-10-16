import base64
from datetime import datetime
import os
import requests
from requests.auth import HTTPBasicAuth


class MpesaService:

  @staticmethod
  def get_access_token():
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    r = requests.get(
        url, auth=HTTPBasicAuth(consumer_key, consumer_secret), timeout=30
    )
    return r.json().get("access_token")

  @classmethod
  def stk_push(cls, phone_number, amount, account_reference, description):
    access_token = cls.get_access_token()
    if not access_token:
      raise Exception("Failed to authenticate with M-Pesa Daraja API")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")

    # Generate password
    data_to_encode = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(data_to_encode.encode()).decode("utf-8")

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    # Ensure phone number is formatted as 254XXXXXXXXX
    formatted_phone = phone_number.strip("+")
    if formatted_phone.startswith("0"):
      formatted_phone = "254" + formatted_phone[1:]

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),  # Daraja expects a whole number
        "PartyA": formatted_phone,
        "PartyB": shortcode,
        "PhoneNumber": formatted_phone,
        "CallBackURL": os.getenv("MPESA_CALLBACK_URL"),
        "AccountReference": account_reference[:12],  # Max 12 chars
        "TransactionDesc": description[:13],
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return response.json()
    
