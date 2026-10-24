"""
tests/test_inventory.py — inventory ledger tests using Member A's real schema.
"""
from __future__ import annotations
from tests.conftest import auth_headers, create_user, get_token


def create_product(client, headers, name="Test Widget", sku="SKU-001", initial_qty=50):
    resp = client.post(
        "/api/v1/products",
        json={"name": name, "sku": sku, "unit": "pcs", "unit_cost": "10.00", "initial_quantity": initial_qty},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_no_token_401(client, db_session):
    resp = client.post("/api/v1/transactions/stock-in", json={})
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_viewer_403_on_stock_in(client, db_session):
    create_user(db_session, email="viewer@test.com", role="viewer")
    create_user(db_session, email="admin@test.com", role="admin")
    admin_token = get_token(client, "admin@test.com")
    viewer_token = get_token(client, "viewer@test.com")
    product_id = create_product(client, auth_headers(admin_token))
    resp = client.post(
        "/api/v1/transactions/stock-in",
        json={"product_id": product_id, "quantity": 10, "type": "stock_in", "reason": "test"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_over_issue_409(client, db_session):
    create_user(db_session, email="admin@test.com", role="admin")
    token = get_token(client)
    headers = auth_headers(token)
    product_id = create_product(client, headers, initial_qty=5)
    resp = client.post(
        "/api/v1/transactions/stock-out",
        json={"product_id": product_id, "quantity": 10, "type": "stock_out", "reason": "over-issue"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INSUFFICIENT_STOCK"


def test_balance_after_correct(client, db_session):
    create_user(db_session, email="admin@test.com", role="admin")
    token = get_token(client)
    headers = auth_headers(token)
    product_id = create_product(client, headers, initial_qty=20)

    resp = client.post(
        "/api/v1/transactions/stock-out",
        json={"product_id": product_id, "quantity": 7, "type": "stock_out", "reason": "sale"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["balance_after"] == 13

    resp2 = client.post(
        "/api/v1/transactions/stock-in",
        json={"product_id": product_id, "quantity": 5, "type": "stock_in", "reason": "restock"},
        headers=headers,
    )
    assert resp2.status_code == 201
    assert resp2.json()["balance_after"] == 18


def test_reversal_once_only(client, db_session):
    create_user(db_session, email="admin@test.com", role="admin")
    token = get_token(client)
    headers = auth_headers(token)
    product_id = create_product(client, headers, initial_qty=30)

    resp = client.post(
        "/api/v1/transactions/stock-out",
        json={"product_id": product_id, "quantity": 10, "type": "stock_out", "reason": "sale"},
        headers=headers,
    )
    assert resp.status_code == 201
    tx_id = resp.json()["id"]

    r1 = client.post(f"/api/v1/transactions/{tx_id}/reverse", json={"reason": "mistake"}, headers=headers)
    assert r1.status_code == 201
    assert r1.json()["balance_after"] == 30

    r2 = client.post(f"/api/v1/transactions/{tx_id}/reverse", json={"reason": "dup"}, headers=headers)
    assert r2.status_code == 409
    assert r2.json()["code"] == "ALREADY_REVERSED"


def test_duplicate_sku_rejected(client, db_session):
    create_user(db_session, email="admin@test.com", role="admin")
    token = get_token(client)
    headers = auth_headers(token)
    create_product(client, headers, sku="SAME-SKU")
    resp = client.post(
        "/api/v1/products",
        json={"name": "Another", "sku": "SAME-SKU", "unit": "pcs", "unit_cost": "1.00"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DUPLICATE_SKU"


def test_adjustment_sets_quantity(client, db_session):
    create_user(db_session, email="admin@test.com", role="admin")
    token = get_token(client)
    headers = auth_headers(token)
    product_id = create_product(client, headers, initial_qty=10)
    resp = client.post(
        "/api/v1/transactions/adjustments",
        json={"product_id": product_id, "new_quantity": 25, "reason": "recount"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["balance_after"] == 25
    assert resp.json()["quantity_delta"] == 15
