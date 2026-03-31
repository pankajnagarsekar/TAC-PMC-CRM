from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rate_limiting_work_orders():
    """
    Test that rapid requests to work order creation trigger rate limiting (429).
    """
    # Note: This assumes the limiter is keyed by IP and we are hitting it from same IP.
    # The actual limit is 5 per minute in the code.

    responses = []
    for _ in range(15):
        # We don't need a valid payload for the limiter to catch it
        # (the limiter runs before the body is fully validated by business logic usually)
        response = client.post("/api/work-orders/", json={"dummy": "data"})
        responses.append(response.status_code)

    assert (
        429 in responses
    ), "Rate limiting (429) was not triggered after 10 rapid POST requests."


def test_rate_limiting_cash_transactions():
    """
    Test rate limiting on cash transactions.
    """
    responses = []
    for _ in range(15):
        response = client.post("/api/cash/transactions", json={"dummy": "data"})
        responses.append(response.status_code)

    assert (
        429 in responses
    ), "Rate limiting (429) was not triggered on cash transactions."
