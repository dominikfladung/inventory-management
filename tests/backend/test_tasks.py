"""
Tests for tasks API endpoints.
"""

import pytest


@pytest.fixture
def created_task(client):
    """Create a task and clean it up afterwards."""
    response = client.post(
        "/api/tasks",
        json={"title": "Check supplier lead times", "priority": "high", "dueDate": "2025-12-01"},
    )
    assert response.status_code == 201
    task = response.json()
    yield task
    client.delete(f"/api/tasks/{task['id']}")


class TestTasksEndpoints:
    """Test suite for task-related endpoints."""

    def test_get_all_tasks(self, client, created_task):
        """Test getting all tasks."""
        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert any(t["id"] == created_task["id"] for t in data)

    def test_create_task_structure(self, created_task):
        """Test that a created task has the expected fields and defaults."""
        assert created_task["title"] == "Check supplier lead times"
        assert created_task["priority"] == "high"
        assert created_task["dueDate"] == "2025-12-01"
        assert created_task["status"] == "pending"

    def test_create_task_missing_title(self, client):
        """Test that an empty title is rejected."""
        response = client.post("/api/tasks", json={"title": "", "dueDate": "2025-12-01"})
        assert response.status_code == 422

    def test_toggle_task(self, client, created_task):
        """Test toggling a task between pending and completed."""
        response = client.patch(f"/api/tasks/{created_task['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        response = client.patch(f"/api/tasks/{created_task['id']}")
        assert response.json()["status"] == "pending"

    def test_delete_task(self, client, created_task):
        """Test deleting a task."""
        response = client.delete(f"/api/tasks/{created_task['id']}")
        assert response.status_code == 200

        ids = [t["id"] for t in client.get("/api/tasks").json()]
        assert created_task["id"] not in ids

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist."""
        response = client.patch("/api/tasks/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist."""
        response = client.delete("/api/tasks/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
