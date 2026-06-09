from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_advise_returns_recommendation():
    r = client.post("/advise", json={
        "hole": ["As", "Ah"], "board": [], "numOpponents": 1,
        "pot": 100, "toCall": 0, "myStack": 500})
    assert r.status_code == 200
    data = r.json()
    assert data["action"] in ("check", "raise")   # AA 강함
    assert 0.0 <= data["equity"] <= 1.0


def test_advise_rejects_invalid():
    r = client.post("/advise", json={
        "hole": ["As", "As"], "board": [], "numOpponents": 1,
        "pot": 100, "toCall": 0, "myStack": 500})
    assert r.status_code == 400
    assert "error" in r.json()
