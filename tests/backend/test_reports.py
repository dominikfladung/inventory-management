"""
Tests for reports API endpoints.
"""


class TestReportsEndpoints:
    """Test suite for quarterly and monthly report endpoints."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports without filters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for quarter in data:
            assert "quarter" in quarter
            assert "total_orders" in quarter
            assert "total_revenue" in quarter
            assert "avg_order_value" in quarter
            assert "fulfillment_rate" in quarter

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends without filters."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for month in data:
            assert "month" in month
            assert "order_count" in month
            assert "revenue" in month

    def test_quarterly_matches_orders_total(self, client):
        """Test that unfiltered quarterly totals match the orders endpoint."""
        orders = client.get("/api/orders").json()
        quarterly = client.get("/api/reports/quarterly").json()

        assert sum(q["total_orders"] for q in quarterly) == len(orders)
        assert (
            abs(sum(q["total_revenue"] for q in quarterly) - sum(o["total_value"] for o in orders))
            < 0.01
        )

    def test_monthly_trends_by_warehouse(self, client):
        """Test that the warehouse filter narrows the monthly trends."""
        orders = client.get("/api/orders?warehouse=Tokyo").json()
        response = client.get("/api/reports/monthly-trends?warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        assert sum(m["order_count"] for m in data) == len(orders)
        assert abs(sum(m["revenue"] for m in data) - sum(o["total_value"] for o in orders)) < 0.01

    def test_monthly_trends_by_month(self, client):
        """Test that the month filter returns only that month."""
        response = client.get("/api/reports/monthly-trends?month=2025-01")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["month"] == "2025-01"

    def test_quarterly_by_month(self, client):
        """Test that a month filter limits quarterly reports to its quarter."""
        response = client.get("/api/reports/quarterly?month=2025-01")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["quarter"] == "Q1-2025"

        january_orders = client.get("/api/orders?month=2025-01").json()
        assert data[0]["total_orders"] == len(january_orders)

    def test_quarterly_by_quarter(self, client):
        """Test filtering quarterly reports by quarter."""
        response = client.get("/api/reports/quarterly?month=Q2-2025")
        assert response.status_code == 200

        data = response.json()
        assert [q["quarter"] for q in data] == ["Q2-2025"]

    def test_reports_multiple_filters(self, client):
        """Test combining warehouse, category, status and month filters."""
        query = "warehouse=San Francisco&category=Sensors&status=Delivered&month=Q1-2025"
        orders = client.get(f"/api/orders?{query}").json()

        monthly = client.get(f"/api/reports/monthly-trends?{query}").json()
        quarterly = client.get(f"/api/reports/quarterly?{query}").json()

        assert sum(m["order_count"] for m in monthly) == len(orders)
        assert sum(q["total_orders"] for q in quarterly) == len(orders)
        for q in quarterly:
            assert q["fulfillment_rate"] == 100.0

    def test_reports_all_filter_values_are_ignored(self, client):
        """Test that 'all' behaves like no filter."""
        unfiltered = client.get("/api/reports/quarterly").json()
        with_all = client.get(
            "/api/reports/quarterly?warehouse=all&category=all&status=all&month=all"
        ).json()
        assert unfiltered == with_all

    def test_reports_empty_result(self, client):
        """Test that filters matching nothing return an empty list."""
        for path in ("quarterly", "monthly-trends"):
            response = client.get(f"/api/reports/{path}?warehouse=Nowhere")
            assert response.status_code == 200
            assert response.json() == []
