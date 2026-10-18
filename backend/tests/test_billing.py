"""Payment tests. Run with:  pytest -q

The first group is pure logic (no database). The second drives the API with the M-Pesa client in
simulation mode and posts fake Safaricom callbacks.
"""
import pytest

from app import billing_rules as rules
from app import mpesa
from app import create_app
from app.extensions import db
from app.models import Payment
from app.seed import seed_all

HDR = {"X-Requested-With": "XMLHttpRequest"}
SECRET = "test-callback-secret"


# ------------------------------------------------------------------ pure rules
def test_phone_numbers_are_normalised():
    assert rules.normalize_phone("0712 345 678") == "254712345678"
    assert rules.normalize_phone("+254712345678") == "254712345678"
    assert rules.normalize_phone("254112345678") == "254112345678"
    assert rules.normalize_phone("712345678") == "254712345678"
    assert rules.normalize_phone("0812345678") is None
    assert rules.normalize_phone("07123") is None
    assert rules.normalize_phone(None) is None


def test_discount_maths():
    assert rules.discount_amount(8000, "percent", 10) == 800
    assert rules.discount_amount(15000, "fixed", 2000) == 2000
    assert rules.discount_amount(8000, "percent", 150) == 8000  # capped at 100%
    assert rules.discount_amount(1000, "fixed", 5000) == 1000  # never more than the price
    assert rules.net_price(8000, 800) == 7200


def test_weeks_unlock_with_each_share_paid():
    assert [rules.unlocked_weeks(p, 8000, 4) for p in (0, 1999, 2000, 3999, 4000, 7999, 8000, 9000)] == [0, 0, 1, 1, 2, 3, 4, 4]
    assert rules.unlocked_weeks(0, 0, 4) == 4  # a free / scholarship path is fully open


def test_suggested_payments():
    s = rules.suggested_payments(0, 8000, 4, 100)
    assert [x["amount"] for x in s] == [2000, 4000, 8000]
    assert rules.suggested_payments(8000, 8000, 4, 100) == []
    assert [x["amount"] for x in rules.suggested_payments(7500, 8000, 4, 100)] == [500]


def test_first_lesson_is_a_free_preview():
    assert rules.lesson_unlocked(1, 1, 0) is True
    assert rules.lesson_unlocked(2, 1, 0) is False
    assert rules.lesson_unlocked(2, 1, 1) is True and rules.lesson_unlocked(6, 2, 1) is False


def test_mpesa_helpers():
    assert mpesa.password("174379", "pass", "20260101120000") == "MTc0Mzc5cGFzczIwMjYwMTAxMTIwMDAw"
    ok = {"Body": {"stkCallback": {"MerchantRequestID": "m1", "CheckoutRequestID": "c1", "ResultCode": 0, "ResultDesc": "ok",
          "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 2000.0}, {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                                        {"Name": "PhoneNumber", "Value": 254712345678}]}}}}
    p = mpesa.parse_callback(ok)
    assert p["checkout_request_id"] == "c1" and p["amount"] == 2000.0 and p["receipt"] == "NLJ7RT61SV" and p["phone"] == "254712345678"
    cancelled = {"Body": {"stkCallback": {"MerchantRequestID": "m", "CheckoutRequestID": "c2", "ResultCode": 1032, "ResultDesc": "Request cancelled by user"}}}
    assert mpesa.parse_callback(cancelled)["result_code"] == 1032
    assert mpesa.parse_callback({"nope": 1}) is None
    assert mpesa.interpret_query({"errorCode": "500.001.1001", "errorMessage": "being processed"})["state"] == "pending"
    assert mpesa.interpret_query({"ResultCode": "0"})["state"] == "success"
    assert mpesa.interpret_query({"ResultCode": "1032"})["state"] == "failed"


def test_refund_policy_tiers():
    assert rules.refund_policy(False, 0, 8000) == ("full", 8000)  # nothing started yet
    assert rules.refund_policy(True, 2, 8000) == ("partial", 4000)  # started, within 3 days
    assert rules.refund_policy(True, 3.0, 8000) == ("partial", 4000)
    assert rules.refund_policy(True, 5, 8000) == ("none", 0)
    assert rules.refund_policy(False, 40, 0) == ("none", 0)  # nothing paid, nothing to refund
    assert rules.refund_policy(True, 1, 5000, 3, 60) == ("partial", 3000)


def test_workspace_pass_code_cannot_be_forged():
    code = rules.workspace_code(42, "s3cret")
    assert code.startswith("WS-") and rules.decode_workspace_code(code, "s3cret") == 42
    assert rules.decode_workspace_code(code.lower(), "s3cret") == 42  # typed in lower case
    assert rules.decode_workspace_code(code, "other-secret") is None
    assert rules.decode_workspace_code("WS-16-DEADBEEF", "s3cret") is None
    assert rules.decode_workspace_code("garbage", "s3cret") is None
    assert rules.workspace_code(1, "k") != rules.workspace_code(2, "k")


def test_csv_cells_cannot_run_as_formulas():
    assert rules.csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert rules.csv_safe("+254712345678") == "'+254712345678"
    assert rules.csv_safe("Amina") == "Amina" and rules.csv_safe(None) == "" and rules.csv_safe(8000) == "8000"


# ------------------------------------------------------------------ API with the paywall on
@pytest.fixture()
def client():
    app = create_app({
        "TESTING": True, "DEV_AUTH": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "ADMIN_EMAILS": {"boss@example.com"}, "PAYWALL_ENABLED": True,
        "MPESA_SIMULATE": True, "MPESA_CALLBACK_SECRET": SECRET,
    })
    with app.app_context():
        db.create_all()
        seed_all(app.config["SEED_DIR"])
    with app.test_client() as c:
        c.app = app
        yield c


def login(c, email, path="beginner"):
    return c.post("/api/auth/dev-login", json={"email": email, "name": email.split("@")[0], "path_slug": path}, headers=HDR)


def callback(c, checkout_id, amount=2000, code=0, receipt="NLJ7RT61SV", secret=SECRET):
    meta = {"CallbackMetadata": {"Item": [{"Name": "Amount", "Value": amount}, {"Name": "MpesaReceiptNumber", "Value": receipt}]}} if code == 0 else {}
    body = {"Body": {"stkCallback": {"MerchantRequestID": "m", "CheckoutRequestID": checkout_id, "ResultCode": code, "ResultDesc": "x", **meta}}}
    return c.post(f"/api/mpesa/callback/{secret}", json=body)  # note: no X-Requested-With header, like Safaricom


def start_payment(c, amount=2000):
    r = c.post("/api/billing/pay", json={"phone": "0712345678", "amount": amount}, headers=HDR)
    assert r.status_code == 200, r.get_json()
    pid = r.get_json()["payment"]["id"]
    with c.app.app_context():
        return pid, db.session.get(Payment, pid).checkout_request_id


def test_only_the_preview_lesson_is_open_before_payment(client):
    login(client, "amina@example.com")
    assert client.get("/api/lessons/1").status_code == 200
    r = client.get("/api/lessons/2")
    assert r.status_code == 402 and r.get_json()["code"] == "payment_required"
    lessons = client.get("/api/lessons").get_json()["lessons"]
    assert [l["locked"] for l in lessons][:3] == [False, True, True]
    assert client.get("/api/resources").status_code == 402


def test_mpesa_payment_unlocks_a_week(client):
    login(client, "amina@example.com")
    _, checkout = start_payment(client, 2000)
    assert client.get("/api/lessons/2").status_code == 402  # still waiting for the callback
    assert callback(client, checkout).get_json()["ResultCode"] == 0
    assert client.get("/api/lessons/5").status_code == 200  # week 1 = lessons 1-5
    assert client.get("/api/lessons/6").status_code == 402
    assert client.get("/api/resources").status_code == 200
    state = client.get("/api/billing").get_json()["billing"]
    assert state["paid"] == 2000 and state["unlocked_weeks"] == 1 and state["balance"] == 6000


def test_callback_is_idempotent_and_checks_amount(client):
    login(client, "amina@example.com")
    pid, checkout = start_payment(client, 2000)
    callback(client, checkout)
    callback(client, checkout)  # Safaricom may retry
    assert client.get("/api/billing").get_json()["billing"]["paid"] == 2000
    login(client, "bob@example.com")
    pid2, checkout2 = start_payment(client, 4000)
    callback(client, checkout2, amount=100, receipt="OTHER00001")  # wrong amount: must not unlock
    assert client.get("/api/billing").get_json()["billing"]["paid"] == 0
    assert client.get(f"/api/billing/payments/{pid2}").get_json()["payment"]["status"] == "review"


def test_failed_or_cancelled_payment_unlocks_nothing(client):
    login(client, "amina@example.com")
    pid, checkout = start_payment(client, 2000)
    callback(client, checkout, code=1032)
    assert client.get(f"/api/billing/payments/{pid}").get_json()["payment"]["status"] == "failed"
    assert client.get("/api/lessons/2").status_code == 402


def test_callback_needs_the_secret(client):
    assert callback(client, "anything", secret="wrong").status_code == 404


def test_payment_validation(client):
    login(client, "amina@example.com")
    bad = lambda **kw: client.post("/api/billing/pay", json=kw, headers=HDR).status_code
    assert bad(phone="123", amount=2000) == 400
    assert bad(phone="0712345678", amount=50) == 400  # below the minimum payment
    assert bad(phone="0712345678", amount=9000) == 400  # more than the balance
    assert bad(phone="0712345678", amount=20.5) == 400


def test_discount_codes_managed_by_admin(client):
    login(client, "boss@example.com")
    r = client.post("/api/admin/discounts", json={"code": "early10", "kind": "percent", "value": 10, "description": "Early bird", "max_redemptions": 1}, headers=HDR)
    assert r.status_code == 201 and r.get_json()["discount"]["code"] == "EARLY10"
    assert client.post("/api/admin/discounts", json={"code": "EARLY10", "kind": "percent", "value": 10}, headers=HDR).status_code == 409
    client.post("/api/auth/logout", headers=HDR)

    login(client, "amina@example.com")
    assert client.post("/api/billing/discount", json={"code": "nope"}, headers=HDR).status_code == 400
    ok = client.post("/api/billing/discount", json={"code": "early10"}, headers=HDR).get_json()["billing"]
    assert ok["discount"] == 800 and ok["net"] == 7200
    assert client.post("/api/billing/discount", json={"code": "early10"}, headers=HDR).status_code == 400  # one discount per learner
    client.post("/api/auth/logout", headers=HDR)

    login(client, "bob@example.com")
    r = client.post("/api/billing/discount", json={"code": "EARLY10"}, headers=HDR)
    assert r.status_code == 400 and "used up" in r.get_json()["error"]


def test_admin_scholarship_opens_everything(client):
    login(client, "amina@example.com")
    uid = client.get("/api/me").get_json()["user"]["id"]
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    r = client.post(f"/api/admin/learners/{uid}/discount", json={"percent": 100, "reason": "Sponsor seat"}, headers=HDR)
    assert r.get_json()["billing"]["net"] == 0
    client.post("/api/auth/logout", headers=HDR)
    login(client, "amina@example.com")
    assert client.get("/api/lessons/20").status_code == 200


def test_admin_records_cash_payment_and_changes_price(client):
    login(client, "amina@example.com", "intermediate")
    uid = client.get("/api/me").get_json()["user"]["id"]
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    assert client.patch("/api/admin/paths/intermediate", json={"price_kes": 12000}, headers=HDR).status_code == 200
    assert client.post("/api/admin/payments/manual", json={"user_id": uid, "amount": 6000, "note": "Cash"}, headers=HDR).status_code == 200
    client.post("/api/auth/logout", headers=HDR)
    login(client, "amina@example.com", "intermediate")
    st = client.get("/api/billing").get_json()["billing"]
    assert st["price"] == 12000 and st["paid"] == 6000 and st["unlocked_weeks"] == 2  # 6000 of 12000 = half


def test_learners_cannot_use_admin_money_routes(client):
    login(client, "amina@example.com")
    assert client.get("/api/admin/payments").status_code == 403
    assert client.post("/api/admin/discounts", json={"code": "X1X", "kind": "fixed", "value": 5}, headers=HDR).status_code == 403


# ------------------------------------------------------------------ refunds
def pay_in_full(c, who="amina@example.com", path="beginner", amount=8000):
    login(c, who, path)
    _, checkout = start_payment(c, amount)
    callback(c, checkout, amount=amount, receipt="RCP" + who[:3].upper() + str(amount))


def test_refund_request_approval_and_access(client):
    pay_in_full(client)  # KES 8,000 = whole Beginner path
    info = client.get("/api/billing").get_json()["refund"]
    assert info["tier"] == "full" and info["eligible"] == 8000 and info["can_request"]
    assert client.post("/api/billing/refund", json={"reason": "no"}, headers=HDR).status_code == 400  # needs a real reason
    r = client.post("/api/billing/refund", json={"reason": "I cannot attend after all"}, headers=HDR)
    assert r.status_code == 200 and r.get_json()["refund"]["open"]["requested_amount"] == 8000
    assert client.post("/api/billing/refund", json={"reason": "again please"}, headers=HDR).status_code == 400  # one at a time
    rid = r.get_json()["refund"]["open"]["id"]
    assert client.get("/api/lessons/20").status_code == 200  # still unlocked until the admin approves
    client.post("/api/auth/logout", headers=HDR)

    login(client, "boss@example.com")
    assert client.post(f"/api/admin/refunds/{rid}/approve", json={"amount": 9000}, headers=HDR).status_code == 400  # more than was paid
    ok = client.post(f"/api/admin/refunds/{rid}/approve", json={"amount": 8000, "note": "Approved"}, headers=HDR)
    assert ok.status_code == 200 and ok.get_json()["refund"]["status"] == "approved"
    assert client.post(f"/api/admin/refunds/{rid}/paid-out", json={"reference": ""}, headers=HDR).status_code == 400
    assert client.post(f"/api/admin/refunds/{rid}/paid-out", json={"method": "M-Pesa", "reference": "QWE123"}, headers=HDR).get_json()["refund"]["status"] == "paid_out"
    client.post("/api/auth/logout", headers=HDR)

    login(client, "amina@example.com")
    assert client.get("/api/lessons/2").status_code == 402  # money went back, access went with it
    assert client.get("/api/workspace").get_json()["workspace"]["active"] is False
    state = client.get("/api/billing").get_json()["billing"]
    assert state["paid"] == 0 and state["refunded"] == 8000


def test_partial_refund_reduces_unlocked_weeks(client):
    pay_in_full(client)
    client.get("/api/lessons/2")  # viewing alone does not count as starting
    client.post("/api/lessons/2/complete", headers=HDR)  # now a paid lesson has been started
    info = client.get("/api/billing").get_json()["refund"]
    assert info["tier"] == "partial" and info["eligible"] == 4000
    rid = client.post("/api/billing/refund", json={"reason": "Changed my mind"}, headers=HDR).get_json()["refund"]["open"]["id"]
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    client.post(f"/api/admin/refunds/{rid}/approve", json={"amount": 4000}, headers=HDR)
    client.post("/api/auth/logout", headers=HDR)
    login(client, "amina@example.com")
    st = client.get("/api/billing").get_json()["billing"]
    assert st["paid"] == 4000 and st["unlocked_weeks"] == 2
    assert client.get("/api/lessons/10").status_code == 200 and client.get("/api/lessons/11").status_code == 402


def test_reject_needs_reason_and_learner_can_cancel(client):
    pay_in_full(client)
    rid = client.post("/api/billing/refund", json={"reason": "Just checking"}, headers=HDR).get_json()["refund"]["open"]["id"]
    assert client.post(f"/api/billing/refund/{rid}/cancel", headers=HDR).status_code == 200
    rid2 = client.post("/api/billing/refund", json={"reason": "Please refund me"}, headers=HDR).get_json()["refund"]["open"]["id"]
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    assert client.post(f"/api/admin/refunds/{rid2}/reject", json={"note": ""}, headers=HDR).status_code == 400
    assert client.post(f"/api/admin/refunds/{rid2}/reject", json={"note": "Outside the refund window"}, headers=HDR).status_code == 200


def test_learners_cannot_decide_refunds(client):
    pay_in_full(client)
    rid = client.post("/api/billing/refund", json={"reason": "Please refund me"}, headers=HDR).get_json()["refund"]["open"]["id"]
    assert client.post(f"/api/admin/refunds/{rid}/approve", json={"amount": 8000}, headers=HDR).status_code == 403


# ------------------------------------------------------------------ workspace tied to payment
def test_workspace_needs_payment_and_front_desk_logs_scans(client):
    login(client, "amina@example.com")
    ws = client.get("/api/workspace").get_json()["workspace"]
    assert ws["active"] is False and ws["required"] == 2000  # 25% of KES 8,000
    code = ws["code"]
    _, checkout = start_payment(client, 2000)
    callback(client, checkout)
    ws = client.get("/api/workspace").get_json()["workspace"]
    assert ws["active"] is True and ws["until"]
    client.post("/api/auth/logout", headers=HDR)

    login(client, "boss@example.com")
    ok = client.post("/api/admin/workspace/verify", json={"code": code}, headers=HDR).get_json()
    assert ok["valid"] and ok["allowed"] and ok["learner"]["email"] == "amina@example.com"
    assert client.post("/api/admin/workspace/verify", json={"code": "WS-1-00000000"}, headers=HDR).get_json()["valid"] is False
    assert len(client.get("/api/admin/workspace/checkins").get_json()["checkins"]) == 1
    client.post("/api/auth/logout", headers=HDR)
    login(client, "amina@example.com")
    assert client.post("/api/admin/workspace/verify", json={"code": code}, headers=HDR).status_code == 403  # learners cannot run the desk


def test_admin_can_extend_workspace_pass(client):
    login(client, "amina@example.com")
    _, checkout = start_payment(client, 2000)
    callback(client, checkout)
    uid = client.get("/api/me").get_json()["user"]["id"]
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    r = client.post(f"/api/admin/learners/{uid}/workspace", json={"until": "2020-01-01"}, headers=HDR)  # in the past: pass ends
    assert r.get_json()["workspace"]["active"] is False
    r = client.post(f"/api/admin/learners/{uid}/workspace", json={"until": None}, headers=HDR)
    assert r.get_json()["workspace"]["active"] is True


# ------------------------------------------------------------------ receipts, exports, audit, privacy
def test_receipt_only_for_own_successful_payment(client):
    login(client, "amina@example.com")
    pid, checkout = start_payment(client, 2000)
    assert client.get(f"/api/billing/payments/{pid}/receipt").status_code == 404  # not paid yet
    callback(client, checkout, receipt="NLJ7RT61SV")
    r = client.get(f"/api/billing/payments/{pid}/receipt").get_json()["receipt"]
    assert r["number"] == "NLJ7RT61SV" and r["amount"] == 2000 and r["balance"] == 6000
    client.post("/api/auth/logout", headers=HDR)
    login(client, "bob@example.com")
    assert client.get(f"/api/billing/payments/{pid}/receipt").status_code == 404  # someone else's


def test_admin_csv_export_and_activity_log(client):
    login(client, "amina@example.com")
    uid = client.get("/api/me").get_json()["user"]["id"]
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    client.post("/api/admin/payments/manual", json={"user_id": uid, "amount": 2000, "note": "=SUM(A1)"}, headers=HDR)
    csv_text = client.get("/api/admin/payments.csv").get_data(as_text=True)
    assert "amina@example.com" in csv_text and "'=SUM(A1)" in csv_text and ",=SUM" not in csv_text
    entries = client.get("/api/admin/audit").get_json()["entries"]
    assert any(e["action"] == "payment.manual" and e["target"] == f"user:{uid}" for e in entries)
    client.post("/api/auth/logout", headers=HDR)
    login(client, "amina@example.com")
    assert client.get("/api/admin/audit").status_code == 403
    assert client.get("/api/admin/payments.csv").status_code == 403


def test_reconcile_endpoint_is_admin_only(client):
    login(client, "amina@example.com")
    assert client.post("/api/admin/payments/reconcile", headers=HDR).status_code == 403
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    assert client.post("/api/admin/payments/reconcile", headers=HDR).get_json() == {"checked": 0, "updated": 0}


def test_learner_can_export_and_delete_their_data(client):
    login(client, "amina@example.com")
    pid, checkout = start_payment(client, 2000)
    callback(client, checkout, receipt="NLJ7RT61SV")
    data = client.get("/api/me/export").get_json()
    assert data["profile"]["email"] == "amina@example.com" and data["payments"][0]["amount"] == 2000
    assert client.post("/api/me/delete", json={}, headers=HDR).status_code == 400  # needs the word DELETE
    assert client.post("/api/me/delete", json={"confirm": "DELETE"}, headers=HDR).status_code == 200
    assert client.get("/api/me").status_code == 401  # signed out
    client.post("/api/auth/logout", headers=HDR)
    login(client, "boss@example.com")
    rows = client.get("/api/admin/payments").get_json()["payments"]
    assert rows[0]["amount"] == 2000 and rows[0]["email"].startswith("deleted-")  # money record kept, identity gone


def test_admins_cannot_delete_their_own_account(client):
    login(client, "boss@example.com")
    assert client.post("/api/me/delete", json={"confirm": "DELETE"}, headers=HDR).status_code == 403
