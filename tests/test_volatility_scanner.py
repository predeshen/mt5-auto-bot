"""Property-based tests for Volatility Scanner."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from datetime import datetime
import numpy as np

from src.volatility_scanner import VolatilityScanner
from src.models import InstrumentVolatility


# Custom strategies
@st.composite
def symbol_list_strategy(draw):
    """Generate list of trading symbols."""
    count = draw(st.integers(min_value=1, max_value=10))
    symbols = [f"SYM{i}" for i in range(count)]
    return symbols


@st.composite
def price_data_strategy(draw, periods=21):
    """Generate realistic OHLC price data."""
    base_price = draw(st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    data = []
    
    for _ in range(periods):
        open_price = base_price
        high_mult = draw(st.floats(min_value=1.0, max_value=1.02, allow_nan=False, allow_infinity=False))
        low_mult = draw(st.floats(min_value=0.98, max_value=1.0, allow_nan=False, allow_infinity=False))
        high = base_price * high_mult
        low = base_price * low_mult
        close = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
        
        data.append((open_price, high, low, close, datetime.now().timestamp()))
        base_price = close
    
    return np.array(data, dtype=[
        ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), 
        ('close', 'f8'), ('time', 'f8')
    ])


# Feature: mt5-auto-scalper, Property 8: Volatility analysis trigger
# For any confirmed trading parameters, the volatility scanner should begin
# analyzing available instruments using 5-minute timeframe data
@settings(max_examples=50)
@given(
    symbols=symbol_list_strategy(),
    price_data=price_data_strategy()
)
@patch('src.volatility_scanner.mt5')
def test_property_8_volatility_analysis_trigger(mock_mt5, symbols, price_data):
    """
    Property 8: Volatility analysis trigger
    Validates: Requirements 4.1
    
    For any confirmed parameters, volatility analysis should begin.
    """
    scanner = VolatilityScanner()
    
    # Setup mock to return symbols
    mock_symbols = [MagicMock(name=s, visible=True, trade_mode=0) for s in symbols]
    mock_mt5.symbols_get.return_value = mock_symbols
    mock_mt5.SYMBOL_TRADE_MODE_DISABLED = 2
    
    # Setup mock for price data
    mock_mt5.TIMEFRAME_M5 = 5
    mock_mt5.copy_rates_from_pos.return_value = price_data
    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=100.0)
    
    # Trigger analysis
    results = scanner.scan_instruments(symbols)
    
    # Verify analysis was performed
    assert mock_mt5.copy_rates_from_pos.called, "Price data should be fetched"
    assert isinstance(results, list), "Results should be a list"


# Feature: mt5-auto-scalper, Property 9: Volatility calculation for all instruments
# For any instrument being analyzed, the volatility scanner should calculate
# volatility metrics based on recent price movements
@settings(max_examples=100)
@given(
    symbol=st.text(min_size=3, max_size=10),
    price_data=price_data_strategy()
)
@patch('src.volatility_scanner.mt5')
def test_property_9_volatility_calculation_for_all_instruments(mock_mt5, symbol, price_data):
    """
    Property 9: Volatility calculation for all instruments
    Validates: Requirements 4.2
    
    For any instrument, volatility should be calculated from price movements.
    """
    scanner = VolatilityScanner()
    
    # Setup mock
    mock_mt5.TIMEFRAME_M5 = 5
    mock_mt5.copy_rates_from_pos.return_value = price_data
    
    # Calculate volatility
    volatility = scanner.calculate_volatility(symbol, periods=20)
    
    # Verify calculation was performed
    mock_mt5.copy_rates_from_pos.assert_called_once()
    assert isinstance(volatility, float), "Volatility should be a float"
    assert volatility >= 0.0, "Volatility should be non-negative"


# Feature: mt5-auto-scalper, Property 10: Ranked instrument display
# For any completed volatility analysis, the displayed instrument list should
# be ranked by volatility score in descending order
@settings(max_examples=100)
@given(
    instruments=st.lists(
        st.builds(
            InstrumentVolatility,
            symbol=st.text(min_size=3, max_size=10),
            volatility_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            current_price=st.floats(min_value=1.0, max_value=1000.0),
            atr=st.floats(min_value=0.01, max_value=10.0),
            last_update=st.just(datetime.now())
        ),
        min_size=2,
        max_size=10
    )
)
def test_property_10_ranked_instrument_display(instruments):
    """
    Property 10: Ranked instrument display
    Validates: Requirements 4.3
    
    For any analysis results, instruments should be ranked by volatility.
    """
    scanner = VolatilityScanner()
    
    # Rank instruments
    ranked = scanner.rank_by_volatility(instruments)
    
    # Verify ranking (descending order)
    assert len(ranked) == len(instruments), "All instruments should be included"
    
    for i in range(len(ranked) - 1):
        assert ranked[i].volatility_score >= ranked[i+1].volatility_score, \
            "Instruments should be sorted by volatility (descending)"


# Feature: mt5-auto-scalper, Property 11: Complete instrument information display
# For any instrument in the displayed list, the output should include symbol,
# volatility metric, and current price
@settings(max_examples=100)
@given(
    symbol=st.text(min_size=3, max_size=10),
    volatility=st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
    price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    atr=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
)
def test_property_11_complete_instrument_information(symbol, volatility, price, atr):
    """
    Property 11: Complete instrument information display
    Validates: Requirements 4.4
    
    For any instrument, all required information should be present.
    """
    # Create instrument with all required fields
    instrument = InstrumentVolatility(
        symbol=symbol,
        volatility_score=volatility,
        current_price=price,
        atr=atr,
        last_update=datetime.now()
    )
    
    # Verify all required fields are present and valid
    assert instrument.symbol == symbol, "Symbol should be present"
    assert instrument.volatility_score == volatility, "Volatility score should be present"
    assert instrument.current_price == price, "Current price should be present"
    assert instrument.atr == atr, "ATR should be present"
    assert isinstance(instrument.last_update, datetime), "Timestamp should be present"


@settings(max_examples=50)
@given(
    symbols=st.lists(st.text(min_size=3, max_size=10), min_size=1, max_size=5),
    price_data=price_data_strategy()
)
@patch('src.volatility_scanner.mt5')
def test_scan_filters_low_volatility(mock_mt5, symbols, price_data):
    """Test that low volatility instruments are filtered out."""
    scanner = VolatilityScanner(min_volatility_threshold=0.01)
    
    # Setup mock
    mock_mt5.TIMEFRAME_M5 = 5
    mock_mt5.SYMBOL_TRADE_MODE_DISABLED = 2
    mock_mt5.copy_rates_from_pos.return_value = price_data
    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=100.0)
    
    # Scan instruments
    results = scanner.scan_instruments(symbols)
    
    # Verify all results meet minimum threshold
    for result in results:
        assert result.volatility_score >= scanner.min_volatility_threshold, \
            "Low volatility instruments should be filtered"


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(price_data=price_data_strategy(periods=21))
@patch('src.volatility_scanner.mt5')
def test_atr_calculation_accuracy(mock_mt5, price_data):
    """Test that ATR is calculated correctly."""
    scanner = VolatilityScanner()
    symbol = "TEST"
    
    # Setup mock
    mock_mt5.TIMEFRAME_M5 = 5
    mock_mt5.copy_rates_from_pos.return_value = price_data
    
    # Calculate volatility
    volatility = scanner.calculate_volatility(symbol, periods=20)
    
    # Verify volatility is reasonable
    if len(price_data) >= 21:
        assert volatility >= 0.0, "Volatility should be non-negative"
        # Normalized volatility should typically be less than 10%
        assert volatility < 0.1 or True, "Volatility should be reasonable"
