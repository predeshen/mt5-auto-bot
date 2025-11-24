"""Property-based tests for Display Manager."""

import pytest
from io import StringIO
import sys
from unittest.mock import patch
from hypothesis import given, settings
from hypothesis import strategies as st
from datetime import datetime

from src.display import DisplayManager
from src.models import (
    AccountInfo, TradingParameters, InstrumentVolatility,
    Position, TradeResult
)


# Feature: mt5-auto-scalper, Property 4: Equity display formatting
# For any retrieved equity value, the displayed output should include the value
# formatted with appropriate decimal precision and the account's base currency
@settings(max_examples=100)
@given(
    account=st.integers(min_value=1, max_value=999999999),
    equity=st.floats(min_value=100.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
    balance=st.floats(min_value=100.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
    currency=st.sampled_from(['USD', 'EUR', 'GBP', 'JPY'])
)
def test_property_4_equity_display_formatting(account, equity, balance, currency):
    """
    Property 4: Equity display formatting
    Validates: Requirements 2.2, 2.4
    
    For any equity value, display should include formatted value with decimal
    precision and currency.
    """
    display = DisplayManager()
    
    account_info = AccountInfo(
        account_number=account,
        equity=equity,
        balance=balance,
        margin=0.0,
        free_margin=balance,
        currency=currency
    )
    
    # Capture output
    captured_output = StringIO()
    sys.stdout = captured_output
    
    display.display_account_info(account_info)
    
    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    
    # Verify output contains equity with proper formatting
    assert f"{equity:,.2f}" in output, "Equity should be formatted with 2 decimal places"
    assert currency in output, "Currency should be displayed"
    assert str(account) in output, "Account number should be displayed"


# Feature: mt5-auto-scalper, Property 7: Parameter confirmation display
# For any collected trading parameters, the application should display a summary
# and request user confirmation before proceeding
@settings(max_examples=100)
@given(
    max_positions=st.integers(min_value=1, max_value=10),
    risk_percent=st.floats(min_value=0.1, max_value=5.0)
)
@patch('builtins.input', return_value='yes')
def test_property_7_parameter_confirmation_display(mock_input, max_positions, risk_percent):
    """
    Property 7: Parameter confirmation display
    Validates: Requirements 3.4, 3.5
    
    For any trading parameters, a summary should be displayed with confirmation.
    """
    display = DisplayManager()
    
    params = TradingParameters(
        max_open_positions=max_positions,
        risk_percent=risk_percent
    )
    
    # Capture output
    captured_output = StringIO()
    sys.stdout = captured_output
    
    result = display.display_parameter_summary(params)
    
    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    
    # Verify output contains all parameters
    assert str(max_positions) in output, "Max positions should be displayed"
    assert str(risk_percent) in output or f"{risk_percent:.1f}" in output, "Risk percent should be displayed"
    assert "Summary" in output, "Summary header should be present"
    
    # Verify confirmation was requested (input was called)
    mock_input.assert_called_once()
    assert result is True


# Feature: mt5-auto-scalper, Property 20: Complete trade event display
# For any trade event (open or close), the console display should include all
# required details and a timestamp
@settings(max_examples=100)
@given(
    symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',))),
    direction=st.sampled_from(['BUY', 'SELL']),
    volume=st.floats(min_value=0.01, max_value=10.0),
    entry_price=st.floats(min_value=1.0, max_value=10000.0),
    exit_price=st.floats(min_value=1.0, max_value=10000.0),
    profit=st.floats(min_value=-1000.0, max_value=1000.0)
)
def test_property_20_complete_trade_event_display(symbol, direction, volume, entry_price, exit_price, profit):
    """
    Property 20: Complete trade event display
    Validates: Requirements 7.2, 7.3, 7.4
    
    For any trade event, all required details and timestamp should be displayed.
    """
    display = DisplayManager()
    
    # Test trade opened display
    position = Position(
        ticket=12345,
        symbol=symbol,
        direction=direction,
        volume=volume,
        entry_price=entry_price,
        current_price=entry_price,
        stop_loss=entry_price * 0.99,
        take_profit=entry_price * 1.01,
        profit=0.0,
        open_time=datetime.now()
    )
    
    captured_output = StringIO()
    sys.stdout = captured_output
    
    display.display_trade_opened(position)
    
    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    
    # Verify all required details are present
    assert symbol in output, "Symbol should be displayed"
    assert direction in output, "Direction should be displayed"
    assert str(volume) in output or f"{volume:.2f}" in output, "Volume should be displayed"
    assert ":" in output, "Timestamp should be present (contains colon)"
    
    # Test trade closed display
    result = TradeResult(
        ticket=12345,
        symbol=symbol,
        direction=direction,
        volume=volume,
        entry_price=entry_price,
        exit_price=exit_price,
        profit=profit,
        open_time=datetime.now(),
        close_time=datetime.now(),
        exit_reason="Take Profit"
    )
    
    captured_output = StringIO()
    sys.stdout = captured_output
    
    display.display_trade_closed(result)
    
    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    
    # Verify all required details are present
    assert symbol in output, "Symbol should be displayed"
    assert direction in output, "Direction should be displayed"
    assert ":" in output, "Timestamp should be present"
    assert str(profit) in output or f"{profit:.2f}" in output, "Profit should be displayed"


# Feature: mt5-auto-scalper, Property 21: Position count display
# For any active trading session, the console should display the current number
# of open positions versus the configured maximum
@settings(max_examples=100)
@given(
    current=st.integers(min_value=0, max_value=10),
    maximum=st.integers(min_value=1, max_value=10)
)
def test_property_21_position_count_display(current, maximum):
    """
    Property 21: Position count display
    Validates: Requirements 7.6
    
    For any trading session, position count vs maximum should be displayed.
    """
    display = DisplayManager()
    
    captured_output = StringIO()
    sys.stdout = captured_output
    
    display.display_position_count(current, maximum)
    
    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    
    # Verify both current and maximum are displayed
    assert str(current) in output, "Current position count should be displayed"
    assert str(maximum) in output, "Maximum position count should be displayed"
    assert "/" in output, "Separator should be present"


@settings(max_examples=100)
@given(
    instruments=st.lists(
        st.builds(
            InstrumentVolatility,
            symbol=st.text(min_size=3, max_size=10),
            volatility_score=st.floats(min_value=0.0, max_value=1.0),
            current_price=st.floats(min_value=1.0, max_value=10000.0),
            atr=st.floats(min_value=0.01, max_value=100.0),
            last_update=st.just(datetime.now())
        ),
        min_size=1,
        max_size=10
    )
)
def test_instrument_display_completeness(instruments):
    """Test that instrument display includes all required information."""
    display = DisplayManager()
    
    captured_output = StringIO()
    sys.stdout = captured_output
    
    display.display_instruments(instruments)
    
    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()
    
    # Verify all instruments are displayed with required info
    for inst in instruments:
        assert inst.symbol in output, f"Symbol {inst.symbol} should be displayed"
