import pytest

@pytest.mark.asyncio
async def test_rate_limiting_work_orders(client):
    """
    Test that rapid requests to work order creation trigger rate limiting (429).
    """
    from app.core.rate_limit import limiter
    # Temporarily lower the limit to 5 per second for testing
    original_rate = limiter.TIERS["Standard"]["rate"]
    limiter.TIERS["Standard"]["rate"] = 5
    
    try:
        responses = []
        for _ in range(10):
            # Using a project-specific endpoint for work order creation
            response = await client.post("/api/v1/work-orders/test-proj-123", json={"dummy": "data"})
            responses.append(response.status_code)

        assert (
            429 in responses
        ), f"Rate limiting (429) was not triggered after rapid POST requests to work-orders. Statuses: {responses}"
    finally:
        limiter.TIERS["Standard"]["rate"] = original_rate


@pytest.mark.asyncio
async def test_rate_limiting_cash_transactions(client):
    """
    Test rate limiting on cash transactions.
    """
    from app.core.rate_limit import limiter
    # Temporarily lower the limit to 5 per second for testing
    original_rate = limiter.TIERS["Standard"]["rate"]
    limiter.TIERS["Standard"]["rate"] = 5

    try:
        responses = []
        for _ in range(10):
            # Using the correct petty-cash endpoint
            response = await client.post("/api/v1/petty-cash/transaction", json={"dummy": "data"})
            responses.append(response.status_code)

        assert (
            429 in responses
        ), f"Rate limiting (429) was not triggered on cash transactions. Statuses: {responses}"
    finally:
        limiter.TIERS["Standard"]["rate"] = original_rate
