import pytest
from decimal import Decimal
from bson import Decimal128
from app.modules.financial.domain.engine import FinancialEngine

def test_to_d128_valid_inputs():
    # Decimal
    assert isinstance(FinancialEngine.to_d128(Decimal("10.5")), Decimal128)
    # Float
    assert isinstance(FinancialEngine.to_d128(10.5), Decimal128)
    # Int
    assert isinstance(FinancialEngine.to_d128(10), Decimal128)
    # String
    assert isinstance(FinancialEngine.to_d128("10.5"), Decimal128)
    # Already Decimal128
    d128 = Decimal128("10.5")
    assert FinancialEngine.to_d128(d128) == d128

def test_to_d128_none_input():
    assert FinancialEngine.to_d128(None) == Decimal128("0")

def test_to_d128_invalid_input():
    with pytest.raises(Exception):
        FinancialEngine.to_d128("not a number")
