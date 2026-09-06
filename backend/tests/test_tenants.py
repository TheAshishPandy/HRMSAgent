from app.crypto import encrypt_str, hmac_email
from app.models import Organization, User
from app.modules.auth.service import create_token, hash_password
from app.themes import DEFAULT_MODULES


def _user(db, email, role, org_id=None):
    u = User(
        email_enc=encrypt_str(email),
        email_hash=hmac_email(email),
        password_hash=hash_password("password"),
        role=role,
        name_enc=encrypt_str(email),
        timezone="UTC",
        organization_id=org_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u, create_token(u.id, u.role)


def _org(db, name, slug, theme="corporate_blue"):
    org = Organization(
        name=name,
        slug=slug,
        theme_key=theme,
        layout_key="classic_sidebar",
        modules=list(DEFAULT_MODULES),
        status="active",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_cannot_become_super_admin(client):
    r = client.post("/api/auth/register", json={
        "email": "x@example.com", "password": "password", "name": "X", "role": "super_admin",
    })
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "candidate"


def test_super_admin_org_crud(client, db):
    _, token = _user(db, "admin@example.com", "super_admin")
    themes = client.get("/api/orgs/themes")
    assert themes.status_code == 200
    assert any(t["key"] == "corporate_blue" for t in themes.json())
    created = client.post("/api/orgs", json={
        "name": "Acme", "slug": "acme", "theme_key": "emerald",
    }, headers=_auth(token))
    assert created.status_code == 200
    body = created.json()
    assert body["slug"] == "acme"
    assert body["theme"]["key"] == "emerald"
    dup = client.post("/api/orgs", json={"name": "A", "slug": "acme"}, headers=_auth(token))
    assert dup.status_code == 409
    listed = client.get("/api/orgs", headers=_auth(token))
    assert any(o["id"] == body["id"] for o in listed.json())
    patched = client.patch(
        f"/api/orgs/{body['id']}",
        json={"theme_key": "dark_enterprise"},
        headers=_auth(token),
    )
    assert patched.status_code == 200
    assert patched.json()["theme_key"] == "dark_enterprise"


def test_hr_cannot_manage_orgs(client):
    r = client.post("/api/auth/register", json={
        "email": "hr@example.com", "password": "password", "name": "Pat", "role": "hr",
    })
    token = r.json()["token"]
    assert client.get("/api/orgs", headers=_auth(token)).status_code == 403
    assert client.post("/api/orgs", json={"name": "X", "slug": "x"}, headers=_auth(token)).status_code == 403


def test_job_tenant_isolation(client, db):
    a = _org(db, "Org A", "org-a")
    b = _org(db, "Org B", "org-b")
    _, ha = _user(db, "hra@example.com", "hr", a.id)
    _, hb = _user(db, "hrb@example.com", "hr", b.id)
    payload = {
        "title": "Backend", "team": "Eng", "location": "Remote", "seniority": "mid",
        "required_skills": ["python"], "nice_to_have": [], "min_years": 1,
        "education": "none", "narrative": "n",
    }
    ja = client.post("/api/jobs", json=payload, headers=_auth(ha)).json()
    jb = client.post("/api/jobs", json={**payload, "title": "Other"}, headers=_auth(hb)).json()
    assert ja["organization_id"] == a.id
    list_a = client.get("/api/jobs", headers=_auth(ha)).json()
    assert any(j["id"] == ja["id"] for j in list_a)
    assert all(j["id"] != jb["id"] for j in list_a)
    denied = client.patch(f"/api/jobs/{jb['id']}", json={"title": "Nope"}, headers=_auth(ha))
    assert denied.status_code == 404


def test_employee_tenant_isolation(client, db):
    a = _org(db, "Org A", "org-a")
    b = _org(db, "Org B", "org-b")
    _, ha = _user(db, "hra@example.com", "hr", a.id)
    _, hb = _user(db, "hrb@example.com", "hr", b.id)
    created = client.post("/api/employees", json={
        "first_name": "Sam", "last_name": "Lee", "email": "sam@a.example",
        "department": "Eng", "designation": "IC",
    }, headers=_auth(ha))
    assert created.status_code == 200
    emp_id = created.json()["id"]
    listed_b = client.get("/api/employees", headers=_auth(hb)).json()
    assert listed_b == []
    assert client.get(f"/api/employees/{emp_id}", headers=_auth(hb)).status_code == 403
    listed_a = client.get("/api/employees", headers=_auth(ha)).json()
    assert len(listed_a) == 1


def test_me_includes_organization_theme(client, db):
    org = _org(db, "Northstar", "northstar", "modern_purple")
    user, token = _user(db, "hr@example.com", "hr", org.id)
    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["organization"]["theme"]["key"] == "modern_purple"
    assert me.json()["organization_id"] == org.id
    assert user.id
