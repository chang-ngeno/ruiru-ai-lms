from flask import Blueprint, g, jsonify, make_response, request

from . import billing
from .security import clear_session, login_required

bp = Blueprint("privacy", __name__, url_prefix="/api")


@bp.get("/me/export")
@login_required
def export_my_data():
    resp = make_response(jsonify(billing.export_user_data(g.user)))
    resp.headers["Content-Disposition"] = 'attachment; filename="my-data.json"'
    return resp


@bp.post("/me/delete")
@login_required
def delete_my_account():
    """Erase my personal data. Payment and refund records stay (amounts and receipts only) for accounting."""
    if g.user.role == "admin":
        return jsonify(error="Administrator accounts cannot be deleted here."), 403
    if (request.get_json(silent=True) or {}).get("confirm") != "DELETE":
        return jsonify(error='Type DELETE to confirm.'), 400
    billing.delete_user_data(g.user)
    return clear_session(make_response(jsonify(ok=True)))
