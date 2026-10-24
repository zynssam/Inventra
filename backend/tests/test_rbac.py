"""
tests/test_rbac.py — role-based access control tests.

Checks every role boundary defined in architecture.md §7.
"""
from __future__ import annotations

import pytest
from tests.conftest import auth_headers, create_user, get_token


class TestAdminOnlyEndpoints:
    def test_list_users_requires_admin(self, client, db_session):
        create_user(db_session, email="admin@t.com", role="admin")
        create_user(db_session, email="store@t.com", role="storekeeper")
        db_session.commit()

        store_token = get_token(client, "store@t.com")
        resp = client.get("/api/v1/users", headers=auth_headers(store_token))
        assert resp.status_code == 403

    def test_adjustments_requires_admin(self, client, db_session):
        create_user(db_session, email="admin@t.com", role="admin")
        create_user(db_session, email="store@t.com", role="storekeeper")
        db_session.commit()

        admin_token = get_token(client, "admin@t.com")
        store_token = get_token(client, "store@t.com")

        # Create a product
        resp = client.post(
            "/api/v1/products",
            json={"name": "A", "sku": "A-001", "unit": "pcs", "unit_cost": "1.00", "initial_quantity": 10},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        # Storekeeper cannot adjust
        resp2 = client.post(
            "/api/v1/transactions/adjustments",
            json={"product_id": pid, "new_quantity": 5, "reason": "test"},
            headers=auth_headers(store_token),
        )
        assert resp2.status_code == 403

    def test_archive_product_requires_admin(self, client, db_session):
        create_user(db_session, email="admin@t.com", role="admin")
        create_user(db_session, email="store@t.com", role="storekeeper")
        db_session.commit()

        admin_token = get_token(client, "admin@t.com")
        store_token = get_token(client, "store@t.com")

        resp = client.post(
            "/api/v1/products",
            json={"name": "B", "sku": "B-001", "unit": "pcs", "unit_cost": "1.00"},
            headers=auth_headers(admin_token),
        )
        pid = resp.json()["id"]

        resp2 = client.delete(f"/api/v1/products/{pid}", headers=auth_headers(store_token))
        assert resp2.status_code == 403

    def test_audit_logs_requires_admin(self, client, db_session):
        create_user(db_session, email="admin@t.com", role="admin")
        create_user(db_session, email="viewer@t.com", role="viewer")
        db_session.commit()

        viewer_token = get_token(client, "viewer@t.com")
        resp = client.get("/api/v1/audit-logs", headers=auth_headers(viewer_token))
        assert resp.status_code == 403


class TestStorekeeperPermissions:
    def test_storekeeper_can_stock_in(self, client, db_session):
        create_user(db_session, email="admin@t.com", role="admin")
        create_user(db_session, email="store@t.com", role="storekeeper")
        db_session.commit()

        admin_token = get_token(client, "admin@t.com")
        store_token = get_token(client, "store@t.com")

        resp = client.post(
            "/api/v1/products",
            json={"name": "C", "sku": "C-001", "unit": "pcs", "unit_cost": "1.00"},
            headers=auth_headers(admin_token),
        )
        pid = resp.json()["id"]

        resp2 = client.post(
            "/api/v1/transactions/stock-in",
            json={"product_id": pid, "quantity": 5, "type": "purchase", "reason": "delivery"},
            headers=auth_headers(store_token),
        )
        assert resp2.status_code == 201

    def test_storekeeper_can_create_product(self, client, db_session):
        create_user(db_session, email="store@t.com", role="storekeeper")
        db_session.commit()
        store_token = get_token(client, "store@t.com")

        resp = client.post(
            "/api/v1/products",
            json={"name": "D", "sku": "D-001", "unit": "pcs", "unit_cost": "1.00"},
            headers=auth_headers(store_token),
        )
        assert resp.status_code == 201


class TestViewerPermissions:
    def test_viewer_can_read_products(self, client, db_session):
        create_user(db_session, email="viewer@t.com", role="viewer")
        db_session.commit()
        viewer_token = get_token(client, "viewer@t.com")

        resp = client.get("/api/v1/products", headers=auth_headers(viewer_token))
        assert resp.status_code == 200

    def test_viewer_cannot_create_product(self, client, db_session):
        create_user(db_session, email="viewer@t.com", role="viewer")
        db_session.commit()
        viewer_token = get_token(client, "viewer@t.com")

        resp = client.post(
            "/api/v1/products",
            json={"name": "E", "sku": "E-001", "unit": "pcs", "unit_cost": "1.00"},
            headers=auth_headers(viewer_token),
        )
        assert resp.status_code == 403

    def test_viewer_can_read_dashboard(self, client, db_session):
        create_user(db_session, email="viewer@t.com", role="viewer")
        db_session.commit()
        viewer_token = get_token(client, "viewer@t.com")

        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers(viewer_token))
        assert resp.status_code == 200


class TestNoTokenRejected:
    @pytest.mark.parametrize("path", [
        "/api/v1/products",
        "/api/v1/categories",
        "/api/v1/dashboard/summary",
        "/api/v1/forecasts",
        "/api/v1/audit-logs",
        "/api/v1/settings",
    ])
    def test_no_token_401(self, client, db_session, path):
        resp = client.get(path)
        assert resp.status_code == 401
        assert resp.json()["code"] == "INVALID_CREDENTIALS"
