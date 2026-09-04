def test_first_register_can_be_hr(client):
    r = client.post("/api/auth/register", json={
        "email": "hr@example.com",
        "password": "password",
        "name": "Pat HR",
        "role": "hr",
    })
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "hr"
    assert "token" in r.json()


def test_second_register_cannot_be_hr(client):
    client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr"
    })
    r = client.post("/api/auth/register", json={
        "email": "other@example.com", "password": "password", "name": "X", "role": "hr"
    })
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "candidate"


def test_login_and_me(client):
    client.post("/api/auth/register", json={
        "email": "c@example.com", "password": "password", "name": "C", "role": "candidate"
    })
    r = client.post("/api/auth/login", json={"email": "c@example.com", "password": "password"})
    token = r.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "c@example.com"
