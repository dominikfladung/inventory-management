"""Tests for restocking endpoints"""

import pytest

from mock_data import submitted_orders


@pytest.fixture(autouse=True)
def clear_submitted_orders():
    submitted_orders.clear()
    yield
    submitted_orders.clear()


class TestRestockRecommendations:
    def test_zero_budget_returns_no_items(self, client):
        data = client.get("/api/restocking/recommendations?budget=0").json()
        assert data["items"] == []
        assert data["total_cost"] == 0

    def test_total_never_exceeds_budget(self, client):
        for budget in (1000, 5000, 50000, 250000, 500000):
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget
            assert data["remaining_budget"] == pytest.approx(budget - data["total_cost"])
            line_sum = sum(i["quantity"] * i["unit_cost"] for i in data["items"])
            assert line_sum == pytest.approx(data["total_cost"])

    def test_increasing_trend_first(self, client):
        data = client.get("/api/restocking/recommendations?budget=500000").json()
        trends = [i["trend"] for i in data["items"]]
        assert trends and trends[0] == "increasing"
        assert all(t == "increasing" for t in trends[:3])

    def test_larger_budget_spends_at_least_as_much(self, client):
        small = client.get("/api/restocking/recommendations?budget=10000").json()
        large = client.get("/api/restocking/recommendations?budget=100000").json()
        assert large["total_cost"] >= small["total_cost"]

    def test_negative_budget_rejected(self, client):
        assert client.get("/api/restocking/recommendations?budget=-1").status_code == 422

    def test_missing_budget_rejected(self, client):
        assert client.get("/api/restocking/recommendations").status_code == 422


class TestPlaceRestockOrder:
    def _payload(self, client, budget=100000):
        rec = client.get(f"/api/restocking/recommendations?budget={budget}").json()
        return {"budget": budget, "items": rec["items"]}

    def test_place_order_and_list(self, client):
        payload = self._payload(client)
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201
        order = response.json()
        assert order["id"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] == max(i["lead_time_days"] for i in order["items"])

        listed = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in listed] == [order["id"]]

    def test_orders_newest_first(self, client):
        first = client.post("/api/restocking/orders", json=self._payload(client)).json()
        second = client.post("/api/restocking/orders", json=self._payload(client)).json()
        listed = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in listed] == [second["id"], first["id"]]

    def test_does_not_affect_existing_orders(self, client):
        before = len(client.get("/api/orders").json())
        client.post("/api/restocking/orders", json=self._payload(client))
        assert len(client.get("/api/orders").json()) == before

    def test_empty_order_rejected(self, client):
        response = client.post("/api/restocking/orders", json={"budget": 1000, "items": []})
        assert response.status_code == 400

    def test_over_budget_rejected(self, client):
        payload = self._payload(client)
        payload["budget"] = 1
        assert client.post("/api/restocking/orders", json=payload).status_code == 400

    def test_unknown_sku_rejected(self, client):
        payload = self._payload(client)
        payload["items"][0]["sku"] = "NOPE-999"
        assert client.post("/api/restocking/orders", json=payload).status_code == 400

    def test_zero_quantity_rejected(self, client):
        payload = self._payload(client)
        payload["items"][0]["quantity"] = 0
        assert client.post("/api/restocking/orders", json=payload).status_code == 422

    def test_client_cannot_underprice(self, client):
        payload = self._payload(client)
        payload["items"][0]["unit_cost"] = 0.01
        order = client.post("/api/restocking/orders", json=payload).json()
        assert order["items"][0]["unit_cost"] > 0.01
