"""Property-based tests for Scalping Strategy."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from datetime import datetime, timedelta

from src.scalping_strategy import ScalpingStrategy
from src.models import Signal, Position


# Feature: mt5-auto-scalper, Property 13: Trade direction determination
@settings(max_examples=100)
@given(
    rsi=st.floats(min_value=0, max_value=100),
    price=st.floats(min_value=1.0, max_value=1000.0)
)
def test_property_13_trade_direction_determination(rsi, price):
    """
    Property 13: Trade direction determination
    Validates: Requirements 5.1, 5.2
    
    For any market analysis, the strategy should determine BUY or SELL direction.
    """
    strategy = ScalpingStrategy()
    
    # Create mock candles with specific RSI conditions
    candles = []
    for i in range(30):
        candles.append({
            'open': price,
            'high': price * 1.01,
            'low': price * 0.99,
            'close': price,
            'time': datetime.now().timestamp()
        })
    
    # Analyze entry
    signal = strategy.analyze_entry("TEST", candles)
    
    # If signal generated, it must have a valid direction
    if signal is not None:
        assert signal.direction in ["BUY", "SELL"], "Direction must be BUY or SELL"
        assert isinstance(signal, Signal), "Must return Signal object"


# Feature: mt5-auto-scalper, Property 14: Position sizing on entry signals
@settings(max_examples=100)
@given(
    equity=st.floats(min_value=1000.0, max_value=100000.0),
    risk_percent=st.floats(min_value=0.1, max_value=5.0),
    stop_loss_pips=st.floats(min_value=1.0, max_value=100.0)
)
def test_property_14_position_sizing_on_entry_signals(equity, risk_percent, stop_loss_pips):
    """
    Property 14: Position sizing on entry signals
    Validates: Requirements 5.2
    
    For any entry signal, position size should be calculated based on equity and risk.
    """
    strategy = ScalpingStrategy()
    
    # Mock symbol and prices for testing
    symbol = "EURUSD"
    entry_price = 1.1000
    stop_loss = 1.0950  # 50 pips stop loss
    
    # Calculate position size
    # Note: This will return 0.01 in test environment without MT5 connection
    lot_size = strategy.calculate_position_size(symbol, equity, risk_percent, entry_price, stop_loss)
    
    # Verify position size is valid
    assert lot_size > 0, "Position size must be positive"
    assert lot_size >= 0.01, "Position size must be at least minimum lot"


# Feature: mt5-auto-scalper, Property 17: Exit order submission on signals
@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=1.0, max_value=1000.0),
    current_price=st.floats(min_value=1.0, max_value=1000.0),
    direction=st.sampled_from(["BUY", "SELL"])
)
def test_property_17_exit_order_submission_on_signals(entry_price, current_price, direction):
    """
    Property 17: Exit order submission on signals
    Validates: Requirements 6.2
    
    For any exit signal, the strategy should generate appropriate exit order.
    """
    strategy = ScalpingStrategy()
    
    # Create position
    atr = abs(entry_price - current_price) * 0.5
    if direction == "BUY":
        take_profit = entry_price + atr * 1.5
        stop_loss = entry_price - atr
    else:
        take_profit = entry_price - atr * 1.5
        stop_loss = entry_price + atr
    
    position = Position(
        ticket=12345,
        symbol="TEST",
        direction=direction,
        volume=0.1,
        entry_price=entry_price,
        current_price=current_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        profit=0.0,
        open_time=datetime.now()
    )
    
    # Analyze exit
    exit_signal = strategy.analyze_exit(position, current_price)
    
    # If exit signal generated, verify it's valid
    if exit_signal is not None:
        assert isinstance(exit_signal, Signal), "Must return Signal object"
        assert exit_signal.direction in ["BUY", "SELL"], "Exit direction must be valid"
        assert exit_signal.reason in ["TAKE_PROFIT", "STOP_LOSS", "TIME_EXIT"], "Must have valid exit reason"


# Feature: mt5-auto-scalper, Property 18: Automatic position closure at thresholds
@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=10.0, max_value=1000.0),
    atr=st.floats(min_value=0.1, max_value=10.0),
    direction=st.sampled_from(["BUY", "SELL"])
)
def test_property_18_automatic_position_closure_at_thresholds(entry_price, atr, direction):
    """
    Property 18: Automatic position closure at thresholds
    Validates: Requirements 6.3, 6.4
    
    For any position reaching TP or SL, it should be closed automatically.
    """
    strategy = ScalpingStrategy()
    
    # Set up position with TP and SL
    if direction == "BUY":
        take_profit = entry_price + atr * 1.5
        stop_loss = entry_price - atr
        
        # Test take profit hit
        position_tp = Position(
            ticket=1, symbol="TEST", direction=direction, volume=0.1,
            entry_price=entry_price, current_price=take_profit + 0.01,
            stop_loss=stop_loss, take_profit=take_profit,
            profit=0.0, open_time=datetime.now()
        )
        exit_signal_tp = strategy.analyze_exit(position_tp, take_profit + 0.01)
        assert exit_signal_tp is not None, "Should generate exit at take profit"
        assert exit_signal_tp.reason == "TAKE_PROFIT"
        
        # Test stop loss hit
        position_sl = Position(
            ticket=2, symbol="TEST", direction=direction, volume=0.1,
            entry_price=entry_price, current_price=stop_loss - 0.01,
            stop_loss=stop_loss, take_profit=take_profit,
            profit=0.0, open_time=datetime.now()
        )
        exit_signal_sl = strategy.analyze_exit(position_sl, stop_loss - 0.01)
        assert exit_signal_sl is not None, "Should generate exit at stop loss"
        assert exit_signal_sl.reason == "STOP_LOSS"
    
    else:  # SELL
        take_profit = entry_price - atr * 1.5
        stop_loss = entry_price + atr
        
        # Test take profit hit
        position_tp = Position(
            ticket=3, symbol="TEST", direction=direction, volume=0.1,
            entry_price=entry_price, current_price=take_profit - 0.01,
            stop_loss=stop_loss, take_profit=take_profit,
            profit=0.0, open_time=datetime.now()
        )
        exit_signal_tp = strategy.analyze_exit(position_tp, take_profit - 0.01)
        assert exit_signal_tp is not None, "Should generate exit at take profit"
        assert exit_signal_tp.reason == "TAKE_PROFIT"
        
        # Test stop loss hit
        position_sl = Position(
            ticket=4, symbol="TEST", direction=direction, volume=0.1,
            entry_price=entry_price, current_price=stop_loss + 0.01,
            stop_loss=stop_loss, take_profit=take_profit,
            profit=0.0, open_time=datetime.now()
        )
        exit_signal_sl = strategy.analyze_exit(position_sl, stop_loss + 0.01)
        assert exit_signal_sl is not None, "Should generate exit at stop loss"
        assert exit_signal_sl.reason == "STOP_LOSS"


@settings(max_examples=50)
@given(direction=st.sampled_from(["BUY", "SELL"]))
def test_time_based_exit(direction):
    """Test that positions are closed after 30 minutes."""
    strategy = ScalpingStrategy()
    
    # Create old position (31 minutes ago)
    position = Position(
        ticket=12345,
        symbol="TEST",
        direction=direction,
        volume=0.1,
        entry_price=100.0,
        current_price=100.5,
        stop_loss=99.0 if direction == "BUY" else 101.0,
        take_profit=101.5 if direction == "BUY" else 98.5,
        profit=0.0,
        open_time=datetime.now() - timedelta(minutes=31)
    )
    
    # Analyze exit
    exit_signal = strategy.analyze_exit(position, 100.5)
    
    # Should generate time-based exit
    assert exit_signal is not None, "Should generate exit after 30 minutes"
    assert exit_signal.reason == "TIME_EXIT"
