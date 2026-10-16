from flask import Blueprint, jsonify, request
from .extensions import db
from .models import Course, Enrollment, Transaction, User
from .services import MpesaService

payment_bp = Blueprint("payments", __name__)


@payment_bp.route("/api/payments/stk-push", methods=["POST"])
def initiate_stk_push():
  data = request.get_json()
  user_id = data.get("user_id")
  course_id = data.get("course_id")
  phone_number = data.get("phone_number")
  applied_discount = float(
      data.get("discount", 0.0)
  )  # Admin-applied discount percentage or flat amount

  course = Course.query.get_or_404(course_id)
  user = User.query.get_or_404(user_id)

  # Calculate final price with admin-implemented adjustments/discounts
  base_price = course.price
  final_amount = max(
      0, base_price - applied_discount
  )  # Custom logic depending on rule type

  try:
    res = MpesaService.stk_push(
        phone_number=phone_number,
        amount=final_amount,
        account_reference=f"Course {course.id}",
        description=f"Enrollment - {course.name}",
    )

    # Save pending transaction tracking
    if res.get("ResponseCode") == "0":
      tx = Transaction(
          user_id=user.id,
          course_id=course.id,
          checkout_request_id=res.get("CheckoutRequestID"),
          amount=final_amount,
          status="PENDING",
      )
      db.session.add(tx)
      db.session.commit()

    return jsonify(res), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500


@payment_bp.route("/api/payments/callback", methods=["POST"])
def mpesa_callback():
  incoming_data = request.get_json()
  callback_data = (
      incoming_data.get("Body", {}).get("stkCallback", {})
  )

  checkout_request_id = callback_data.get("CheckoutRequestID")
  result_code = callback_data.get("ResultCode")

  tx = Transaction.query.filter_by(
      checkout_request_id=checkout_request_id
  ).first()
  if not tx or tx.status == "COMPLETED":
    # Idempotency guard: Prevent double-processing
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

  if result_code == 0:
    # Transaction successful
    tx.status = "COMPLETED"
    meta_items = (
        callback_data.get("CallbackMetadata", {}).get("Item", [])
    )
    for item in meta_items:
      if item.get("Name") == "MpesaReceiptNumber":
        tx.receipt_number = item.get("Value")

    # Automatically unlock course access for the user
    enrollment = Enrollment(
        user_id=tx.user_id, course_id=tx.course_id, status="ACTIVE"
    )
    db.session.add(enrollment)
    db.session.commit()
  else:
    # Transaction failed or cancelled (e.g., user entered wrong PIN or timeout)
    tx.status = "FAILED"
    db.session.commit()

  # Always return a 200 success response back to Safaricom to acknowledge receipt
  return jsonify({"ResultCode": 0, "ResultDesc": "Success"}), 200
  
