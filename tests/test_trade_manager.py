"""Property-based tests for Trade Manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, settings
from hypothesis import strategies as st
from datetime import datetime

from src.trade_manager import TradeManager
from src.models import Signal, Position


# Feature: mt5-auto-scalper, Property 16: Maximum position limit enforcement
@settings(max_examples=100)
@given(
    max_positions=st.integers(min_value=1, max_value=10),
    attempts=st.integers(min_value=1, max_value=20)
)
def test_property_16_maximum_position_limit_enforcement(max_positions, attempts):
    """
    Property 16: Maximum position limit enforcement
    Validates: Requirements 5.6
    
    For any entry signal, when max positions reached, no new positions should open.
    """
    manager = TradeManager()
    manager.set_max_positions(max_positions)
    
    # Simulate opening positions up to the limit
    for i in range(attempts):
        can_open = manager.can_open_new_position()
        current_count = manager.get_position_count()
        
        if current_count < max_positions:
            assert can_open is True, "Should allow opening when under limit"
            # Simulate adding a position
            manager._positions[i] = Position(
                ticket=i, symbol="TEST", direction="BUY", volume=0.1,
                entry_price=100.0, current_price=100.0,
                stop_loss=99.0, take_profit=101.0,
                profit=0.0, open_time=datetime.now()
            )
        else:
            assert can_open is False, "Should not allow opening when at limit"
    
    # Verify final count doesn't exceed maximum
    assert manager.get_position_count() <= max_positions, "Position count should not exceed maximum"


# Feature: mt5-auto-scalper, Property 15: Order submission and verification
@settings(max_examples=50)
@given(
    symbol=st.text(min_size=3, max_size=10),
    direction=st.sampled_from(["BUY", "SELL"]),
    size=st.floats(min_value=0.01, max_value=10.0)
)
@patch('src.trade_manager.mt5')
def test_property_15_order_submission_and_verification(mock_mt5, symbol, direction, size):
    """
    Property 15: Order submission and verification
    Validates: Requirements 5.3, 5.4
    
    For any calculated position size, order should be submitted and verified.
    """
    manager = TradeManager()
    
    # Setup mock for successful order
    mock_result = MagicMock()
    mock_result.retcode = 10009  # TRADE_RETCODE_DONE
    mock_result.order = 12345
    mock_result.price = 100.0
    mock_result.comment = "Success"
    
    mock_mt5.TRADE_RETCODE_DONE = 10009
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.TRADE_ACTION_DEAL = 1
    mock_mt5.ORDER_TIME_GTC = 0
    mock_mt5.ORDER_FILLING_IOC = 1
    mock_mt5.order_send.return_value = mock_result
    
    # Create signal
    signal = Signal(
        symbol=symbol,
        direction=direction,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=101.0,
        timestamp=datetime.now(),
        confidence=0.7,
        reason="TEST"
    )
    
    # Open position
    position = manager.open_position(signal, size)
    
    # Verify order was submitted
    mock_mt5.order_send.assert_called_once()
    
    # Verify position was created if successful
    if position is not None:
        assert position.symbol == symbol
        assert position.direction == direction
        assert position.volume == size


# Feature: mt5-auto-scalper, Property 12: Continuous monitoring of selected instruments
@settings(max_examples=50)
@given(position_count=st.integers(min_value=0, max_value=5))
@patch('src.trade_manager.mt5')
def test_property_12_continuous_monitoring(mock_mt5, position_count):
    """
    Property 12: Continuous monitoring of selected instruments
    Validates: Requirements 5.1
    
    For any selected instruments, monitoring should be active.
    """
    manager = TradeManager()
    
    # Add positions
    for i in range(position_count):
        manager._positions[i] = Position(
            ticket=i, symbol=f"SYM{i}", direction="BUY", volume=0.1,
            entry_price=100.0, current_price=100.0,
            stop_loss=99.0, take_profit=101.0,
            profit=0.0, open_time=datetime.now()
        )
    
    # Setup mock
    mock_mt5.positions_get.return_value = []
    
    # Monitor positions
    manager.monitor_positions()
    
    # Verify monitoring was called
    mock_mt5.positions_get.assert_called_once()


# Feature: mt5-auto-scalper, Property 19: Complete trade logging on closure
@settings(max_examples=50)
@given(
    entry_price=st.floats(min_value=10.0, max_value=1000.0),
    exit_price=st.floats(min_value=10.0, max_value=1000.0),
    direction=st.sampled_from(["BUY", "SELL"])
)
@patch('src.trade_manager.mt5')
def test_property_19_complete_trade_logging_on_closure(mock_mt5, entry_price, exit_price, direction):
    """
    Property 19: Complete trade logging on closure
    Validates: Requirements 6.5
    
    For any closed trade, complete logging should occur.
    """
    manager = TradeManager()
    
    # Create position
    position = Position(
        ticket=12345,
        symbol="TEST",
        direction=direction,
        volume=0.1,
        entry_price=entry_price,
        current_price=entry_price,
        stop_loss=entry_price * 0.99,
        take_profit=entry_price * 1.01,
        profit=0.0,
        open_time=datetime.now()
    )
    
    manager._positions[12345] = position
    
    # Setup mock for close
    mock_tick = MagicMock()
    mock_tick.bid = exit_price
    mock_tick.ask = exit_price
    mock_mt5.symbol_info_tick.return_value = mock_tick
    
    mock_result = MagicMock()
    mock_result.retcode = 10009
    mock_result.order = 12345
    mock_result.price = exit_price
    
    mock_mt5.TRADE_RETCODE_DONE = 10009
    mock_mt5.ORDER_TYPE_BUY = 0
    mock_mt5.ORDER_TYPE_SELL = 1
    mock_mt5.TRADE_ACTION_DEAL = 1
    mock_mt5.ORDER_TIME_GTC = 0
    mock_mt5.ORDER_FILLING_IOC = 1
    mock_mt5.order_send.return_value = mock_result
    
    # Close position
    result = manager.close_position(position)
    
    # Verify trade result contains all required information
    if result is not None:
        assert result.ticket == position.ticket
        assert result.symbol == position.symbol
        assert result.direction == position.direction
        assert result.entry_price == entry_price
        assert result.exit_price == exit_price
        assert hasattr(result, 'profit')
        assert hasattr(result, 'open_time')
        assert hasattr(result, 'close_time')
        assert hasattr(result, 'exit_reason')


@settings(max_examples=50)
@given(max_pos=st.integers(min_value=1, max_value=5))
def test_position_count_tracking(max_pos):
    """Test that position count is accurately tracked."""
    manager = TradeManager()
    manager.set_max_positions(max_pos)
    
    # Add positions up to limit
    for i in range(max_pos):
        manager._positions[i] = Position(
            ticket=i, symbol="TEST", direction="BUY", volume=0.1,
            entry_price=100.0, current_price=100.0,
            stop_loss=99.0, take_profit=101.0,
            profit=0.0, open_time=datetime.now()
        )
    
    assert manager.get_position_count() == max_pos
    assert not manager.can_open_new_position()
    
    # Remove one position
    del manager._positions[0]
    
    assert manager.get_position_count() == max_pos - 1
    assert manager.can_open_new_position()
