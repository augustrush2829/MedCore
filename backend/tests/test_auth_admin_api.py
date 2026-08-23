from sqlalchemy import select

from app.db.models import User

from conftest import login


def test_super_admin_can_create_hospital_with_hospital_admin(client, db_session):
    token = login(client, "super@test.mn")

    response = client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "New Hospital",
            "plan": "mvp",
            "status": "active",
            "settings": {"timezone": "Asia/Ulaanbaatar"},
            "admin_name": "New Admin",
            "admin_email": "new-admin@test.mn",
            "admin_password": "secret123",
        },
    )

    assert response.status_code == 201, response.text
    organization_id = response.json()["id"]
    created_admin = db_session.scalar(select(User).where(User.email == "new-admin@test.mn"))
    assert created_admin is not None
    assert created_admin.role == "admin"
    assert created_admin.organization_id == organization_id


def test_hospital_admin_cannot_create_hospital_or_other_admin(client):
    token = login(client, "admin@test.mn")

    hospital_response = client.post(
        "/admin/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Blocked Hospital",
            "admin_name": "Blocked Admin",
            "admin_email": "blocked@test.mn",
            "admin_password": "secret123",
        },
    )
    assert hospital_response.status_code == 403

    admin_response = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Second Admin",
            "email": "second-admin@test.mn",
            "role": "admin",
            "password": "secret123",
        },
    )
    assert admin_response.status_code == 403


def test_hospital_admin_can_create_doctor_only_in_own_hospital(client, db_session):
    token = login(client, "admin@test.mn")

    response = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "New Doctor",
            "email": "new-doctor@test.mn",
            "role": "doctor",
            "password": "secret123",
        },
    )

    assert response.status_code == 201, response.text
    new_user = db_session.scalar(select(User).where(User.email == "new-doctor@test.mn"))
    admin = db_session.scalar(select(User).where(User.email == "admin@test.mn"))
    assert new_user is not None
    assert admin is not None
    assert new_user.organization_id == admin.organization_id


def test_super_admin_lists_all_hospitals(client):
    token = login(client, "super@test.mn")

    response = client.get("/admin/organizations", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"Hospital A", "Hospital B", "MedCore Platform"}.issubset(names)


def test_admin_overview_is_scoped_to_own_hospital(client):
    token = login(client, "admin@test.mn")
    response = client.get("/admin/overview", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    overview = response.json()
    org = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["organization_id"]
    assert overview["organization_id"] == org
