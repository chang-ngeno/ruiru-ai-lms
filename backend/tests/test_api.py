"""Run with:  pytest -q   (uses an in-memory SQLite database and DEV_AUTH sign-in)."""
import pytest

from app import create_app
from app.extensions import db
from app.seed import seed_all

HDR = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture()
def client():
    app = create_app(
        {
            "TESTING": True,
            "DEV_AUTH": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "ADMIN_EMAILS": {"boss@example.com"},
            "PAYWALL_ENABLED": False,  # payment rules are tested in test_billing.py
        }
    )
    with app.app_context():
        db.create_all()
        seed_all(app.config["SEED_DIR"])
    with app.test_client() as c:
        yield c


def signup(client, email="amina@example.com", path="beginner"):
    return client.post("/api/auth/dev-login", json={"email": email, "name": "Amina W", "path_slug": path}, headers=HDR)


def test_three_paths_public(client):
    data = client.get("/api/paths").get_json()["paths"]
    assert [p["slug"] for p in data] == ["beginner", "intermediate", "advanced"]
    assert all(p["lessons"] == 20 for p in data)


def test_signup_assigns_chosen_path(client):
    r = signup(client, path="advanced")
    assert r.status_code == 200
    body = r.get_json()
    assert body["created"] is True and body["user"]["path"]["slug"] == "advanced"
    me = client.get("/api/me").get_json()["user"]
    assert me["email"] == "amina@example.com"


def test_csrf_header_required_on_writes(client):
    r = client.post("/api/auth/dev-login", json={"email": "x@example.com"})
    assert r.status_code == 403


def test_path_is_chosen_once(client):
    signup(client, path=None)
    assert client.get("/api/lessons").status_code == 409  # must choose a path first
    assert client.post("/api/me/path", json={"path_slug": "beginner"}, headers=HDR).status_code == 200
    assert client.post("/api/me/path", json={"path_slug": "advanced"}, headers=HDR).status_code == 409


def test_lessons_are_scoped_to_path(client):
    signup(client, path="intermediate")
    lessons = client.get("/api/lessons").get_json()["lessons"]
    assert len(lessons) == 20 and lessons[0]["title"] == "Advanced prompting techniques"
    assert client.get("/api/lessons/21").status_code == 404


def test_complete_progress_and_quiz(client):
    signup(client)
    r = client.post("/api/lessons/1/complete", headers=HDR).get_json()["summary"]
    assert r["completed"] == 1 and r["percent"] == 5 and r["streak"] == 1
    assert client.post("/api/lessons/1/quiz", json={"score": 9}, headers=HDR).status_code == 400
    assert client.post("/api/lessons/1/quiz", json={"score": 4}, headers=HDR).status_code == 200
    r = client.put("/api/lessons/1/progress", json={"steps_done": [0, 2], "notes": "hello"}, headers=HDR)
    assert r.status_code == 200
    detail = client.get("/api/lessons/1").get_json()
    assert detail["progress"]["steps_done"] == [0, 2] and detail["progress"]["notes"] == "hello"
    assert client.put("/api/lessons/1/progress", json={"steps_done": [99]}, headers=HDR).status_code == 400
    undone = client.delete("/api/lessons/1/complete", headers=HDR).get_json()["summary"]
    assert undone["completed"] == 0


def test_certificate_locked_until_finished(client):
    signup(client)
    assert client.get("/api/certificate").status_code == 403
    for n in range(1, 21):
        client.post(f"/api/lessons/{n}/complete", headers=HDR)
    cert = client.get("/api/certificate").get_json()
    assert cert["code"].startswith("RAI-") and cert["name"] == "Amina W"


def test_resources_gated_by_path(client):
    signup(client, path="advanced")
    keys = [r["key"] for r in client.get("/api/resources").get_json()["resources"]]
    assert keys == ["notes", "workbook", "decks", "outline"]
    assert client.get("/api/resources/nope").status_code == 404


def test_admin_only(client):
    signup(client)
    assert client.get("/api/admin/overview").status_code == 403
    client.post("/api/auth/logout", headers=HDR)
    signup(client, email="boss@example.com")
    assert client.get("/api/admin/overview").status_code == 200
    assert client.get("/api/admin/learners").status_code == 200


def test_dev_login_disabled_in_production():
    app = create_app({"TESTING": True, "DEV_AUTH": False, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
    r = app.test_client().post("/api/auth/dev-login", json={"email": "a@b.co"}, headers=HDR)
    assert r.status_code == 404
