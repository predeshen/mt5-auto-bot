"""Property-based tests for data models."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models import TradingParameters


# Feature: mt5-auto-scalper, Property 6: Trading parameters validation
# For any user-entered maximum open positions value, the application should validate
# it is a positive integer before accepting
@settings(max_examples=100)
@given(max_positions=st.integers())
def test_property_6_trading_parameters_validation(max_positions):
    """
    Property 6: Trading parameters validation
    Validates: Requirements 3.2
    
    For any integer value, the validation should accept positive integers
    and reject non-positive integers.
    """
    risk_percent = 1.0  # Valid risk percentage
    
    if max_positions > 0:
        # Positive integers should be accepted
        params = TradingParameters(
            max_open_positions=max_positions,
            risk_percent=risk_percent
        )
        assert params.validate() is True
        assert params.max_open_positions == max_positions
    else:
        # Non-positive integers should be rejected
        params = TradingParameters(
            max_open_positions=max_positions,
            risk_percent=risk_percent
        )
        with pytest.raises(ValueError, match="max_open_positions must be a positive integer"):
            params.validate()


@settings(max_examples=100)
@given(
    max_positions=st.integers(min_value=1, max_value=100),
    risk_percent=st.floats(min_value=0.01, max_value=100.0)
)
def test_valid_trading_parameters(max_positions, risk_percent):
    """Test that valid parameters pass validation."""
    params = TradingParameters(
        max_open_positions=max_positions,
        risk_percent=risk_percent
    )
    assert params.validate() is True


@settings(max_examples=100)
@given(risk_percent=st.one_of(
    st.floats(max_value=0.0),
    st.floats(min_value=100.01, max_value=1000.0)
))
def test_invalid_risk_percent(risk_percent):
    """Test that invalid risk percentages are rejected."""
    params = TradingParameters(
        max_open_positions=1,
        risk_percent=risk_percent
    )
    with pytest.raises(ValueError, match="risk_percent must be between 0 and 100"):
        params.validate()
