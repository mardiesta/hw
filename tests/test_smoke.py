"""основной сценарий"""

from fastapi.testclient import TestClient


def test_health_reports_database_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_docs_are_available(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200


def test_task_lifecycle_with_filters_and_cascade(client: TestClient) -> None:
    user = client.post(
        "/v1/users", json={"email": "anna@example.com", "display_name": "Anna", "role": "admin"}
    )
    assert user.status_code == 201
    user_id = user.json()["id"]

    project = client.post("/v1/projects", json={"name": "Website", "description": "Corporate site"})
    assert project.status_code == 201
    project_id = project.json()["id"]

    label = client.post("/v1/labels", json={"name": "bug", "color": "#ff0000"})
    assert label.status_code == 201
    label_id = label.json()["id"]

    task = client.post(
        "/v1/tasks",
        json={
            "project_id": project_id,
            "assignee_id": user_id,
            "label_id": label_id,
            "title": "Fix login",
            "priority": "high",
        },
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    assert task.json()["status"] == "open"

    comment = client.post(
        "/v1/comments", json={"task_id": task_id, "author_id": user_id, "body": "Reproduced"}
    )
    assert comment.status_code == 201
    comment_id = comment.json()["id"]

    tasks = client.get("/v1/tasks", params={"project_id": project_id, "status": "open"})
    assert tasks.status_code == 200
    assert [item["id"] for item in tasks.json()] == [task_id]

    comments = client.get("/v1/comments", params={"task_id": task_id})
    assert comments.status_code == 200
    assert [item["id"] for item in comments.json()] == [comment_id]

    patched = client.patch(f"/v1/tasks/{task_id}", json={"status": "done"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "done"

    deleted = client.delete(f"/v1/projects/{project_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    # Удаление проекта каскадно удаляет его задачи и их комментарии.
    assert client.get(f"/v1/tasks/{task_id}").status_code == 404
    assert client.get(f"/v1/comments/{comment_id}").status_code == 404


def test_missing_user_returns_404(client: TestClient) -> None:
    response = client.get("/v1/users/999999")

    assert response.status_code == 404


def test_unknown_field_is_rejected_with_422(client: TestClient) -> None:
    response = client.post(
        "/v1/users",
        json={"id": 42, "email": "anna@example.com", "display_name": "Anna"},
    )

    assert response.status_code == 422


def test_duplicate_email_returns_409(client: TestClient) -> None:
    payload = {"email": "anna@example.com", "display_name": "Anna"}
    assert client.post("/v1/users", json=payload).status_code == 201

    response = client.post("/v1/users", json=payload)

    assert response.status_code == 409
