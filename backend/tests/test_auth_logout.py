from conftest import login


def test_logout_revokes_token_so_further_requests_are_rejected(client):
    token = login(client, "doctor@test.mn")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/me", headers=headers).status_code == 200

    logout_response = client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 204

    after_logout = client.get("/auth/me", headers=headers)
    assert after_logout.status_code == 401
    assert after_logout.json()["detail"] == "Token revoked"


def test_logout_without_token_is_rejected(client):
    response = client.post("/auth/logout")
    assert response.status_code == 401


def test_logout_only_revokes_the_specific_token_not_all_sessions(client):
    token_a = login(client, "doctor@test.mn")
    token_b = login(client, "doctor@test.mn")

    client.post("/auth/logout", headers={"Authorization": f"Bearer {token_a}"})

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"}).status_code == 200
