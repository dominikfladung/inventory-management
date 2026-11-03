"""
Tests for purchase order API endpoints.
"""

import pytest

import mock_data


@pytest.fixture(autouse=True)
def clean_purchase_orders():
    """Restore the in-memory purchase orders after each test."""
    original = list(mock_data.purchase_orders)
    yield
    mock_data.purchase_orders[:] = original


def po_payload(backlog_item_id, **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Components",
        "quantity": 50,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-12-15",
        "notes": "Rush order",
    }
    payload.update(overrides)
    return payload


def first_backlog_id(client):
    return client.get("/api/backlog").json()[0]["id"]


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client):
        """Test creating a purchase order for a backlog item."""
        backlog_id = first_backlog_id(client)
        response = client.post("/api/purchase-orders", json=po_payload(backlog_id))
        assert response.status_code == 201

        po = response.json()
        assert po["id"].startswith("PO-")
        assert po["backlog_item_id"] == backlog_id
        assert po["supplier_name"] == "Acme Components"
        assert po["quantity"] == 50
        assert po["status"].lower() == "pending"
        assert "created_date" in po

    def test_get_purchase_order_by_backlog_item(self, client):
        """Test fetching a purchase order by backlog item ID."""
        backlog_id = first_backlog_id(client)
        created = client.post("/api/purchase-orders", json=po_payload(backlog_id)).json()

        response = client.get(f"/api/purchase-orders/{backlog_id}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_backlog_reflects_purchase_order(self, client):
        """Test that the backlog marks items that have a purchase order."""
        backlog_id = first_backlog_id(client)
        created = client.post("/api/purchase-orders", json=po_payload(backlog_id)).json()

        item = next(b for b in client.get("/api/backlog").json() if b["id"] == backlog_id)
        assert item["has_purchase_order"] is True
        assert item["purchase_order_id"] == created["id"]

    def test_create_duplicate_purchase_order(self, client):
        """Test that a backlog item can only have one purchase order."""
        backlog_id = first_backlog_id(client)
        assert client.post("/api/purchase-orders", json=po_payload(backlog_id)).status_code == 201

        response = client.post("/api/purchase-orders", json=po_payload(backlog_id))
        assert response.status_code == 400

    def test_create_purchase_order_unknown_backlog_item(self, client):
        """Test creating a purchase order for a nonexistent backlog item."""
        response = client.post("/api/purchase-orders", json=po_payload("nonexistent-999"))
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_purchase_order_invalid_quantity(self, client):
        """Test that a non-positive quantity is rejected."""
        response = client.post(
            "/api/purchase-orders", json=po_payload(first_backlog_id(client), quantity=0)
        )
        assert response.status_code == 400

    def test_create_purchase_order_negative_cost(self, client):
        """Test that a negative unit cost is rejected."""
        response = client.post(
            "/api/purchase-orders", json=po_payload(first_backlog_id(client), unit_cost=-1)
        )
        assert response.status_code == 422

    def test_get_nonexistent_purchase_order(self, client):
        """Test getting a purchase order that doesn't exist."""
        response = client.get("/api/purchase-orders/nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
