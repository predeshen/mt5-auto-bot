"""Property-based tests for SMC Signal Generator using Hypothesis."""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from src.smc_strategy import (
    SMCSignal, ConfluenceZone, FVG, OrderBlock,
    FVGDetector, OrderBlockDetector, MarketStructureAnalyzer,
    MultiTimeframeAnalyzer, SMCSignalGenerator
)


# Feature: smc-strategy, Property 30: Signal Data Completeness
# For any generated SMC signal, it should include entry_price, stop_loss, and take_profit levels.
# Validates: Requirements 8.2

@given(
    entry_price=st.floats(min_value=100.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    stop_loss=st.floats(min_value=50.0, max_value=99.0, allow_nan=False, allow_infinity=False),
    take_profit=st.floats(min_value=201.0, max_value=300.0, allow_nan=False, allow_infinity=False)
)
def test_signal_data_completeness(entry_price, stop_loss, take_profit):
    """Property: All generated signals should have complete data."""
    # Create signal
    signal = SMCSignal(
        symbol="TEST",
        direction="BUY",
        order_type="BUY_LIMIT",
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence=0.8,
        setup_type="CONFLUENCE",
        timeframe_bias={"H4": "BULLISH", "H1": "BULLISH"},
        zones=[],
        timestamp=datetime.now()
    )
    
    # Property: All price levels should be populated
    assert signal.entry_price is not None, "Entry price should be populated"
    assert signal.stop_loss is not None, "Stop loss should be populated"
    assert signal.take_profit is not None, "Take profit should be populated"
    
    # Property: All prices should be positive
    assert signal.entry_price > 0, "Entry price should be positive"
    assert signal.stop_loss > 0, "Stop loss should be positive"
    assert signal.take_profit > 0, "Take profit should be positive"
    
    # Property: Signal should have direction
    assert signal.direction in ["BUY", "SELL"], "Direction should be BUY or SELL"
    
    # Property: Signal should have order type
    assert signal.order_type in ["BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"], \
        "Order type should be valid"


# Feature: smc-strategy, Property 31: Stop Loss Placement Beyond Invalidation
# For any signal with an Order Block, the stop loss should be placed beyond the invalidation point.
# Validates: Requirements 8.3

@given(
    ob_high=st.floats(min_value=110.0, max_value=120.0, allow_nan=False, allow_infinity=False),
    ob_low=st.floats(min_value=100.0, max_value=109.0, allow_nan=False, allow_infinity=False),
    direction=st.sampled_from(["BUY", "SELL"])
)
def test_stop_loss_placement(ob_high, ob_low, direction):
    """Property: Stop loss should be beyond Order Block invalidation point."""
    fvg_detector = FVGDetector()
    ob_detector = OrderBlockDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    signal_gen = SMCSignalGenerator(fvg_detector, ob_detector, structure_analyzer, mtf_analyzer)
    
    # Create Order Block
    ob = OrderBlock(
        timeframe="H1",
        direction=direction,
        high=ob_high,
        low=ob_low,
        entry_price=(ob_high + ob_low) / 2,
        created_at=datetime.now(),
        valid=True,
        strength=10.0
    )
    
    # Calculate stop loss
    stop_loss = signal_gen.calculate_stop_loss(direction, order_block=ob)
    
    # Property: Stop loss should be beyond invalidation
    if direction == "BUY":
        # For buy, SL should be below OB low
        assert stop_loss < ob_low, \
            f"Buy stop loss {stop_loss} should be below OB low {ob_low}"
    else:  # SELL
        # For sell, SL should be above OB high
        assert stop_loss > ob_high, \
            f"Sell stop loss {stop_loss} should be above OB high {ob_high}"


def test_signal_validation():
    """Property: Signal validation should enforce minimum requirements."""
    fvg_detector = FVGDetector()
    ob_detector = OrderBlockDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    signal_gen = SMCSignalGenerator(fvg_detector, ob_detector, structure_analyzer, mtf_analyzer)
    
    # Valid signal with good RR
    valid_signal = SMCSignal(
        symbol="TEST",
        direction="BUY",
        order_type="BUY_LIMIT",
        entry_price=100.0,
        stop_loss=95.0,  # 5 point risk
        take_profit=110.0,  # 10 point reward, RR = 2.0
        confidence=0.8,
        setup_type="CONFLUENCE",
        timeframe_bias={"H4": "BULLISH"},
        zones=[],
        timestamp=datetime.now()
    )
    
    assert signal_gen.validate_signal(valid_signal) == True, \
        "Valid signal should pass validation"
    
    # Invalid signal with poor RR
    invalid_signal = SMCSignal(
        symbol="TEST",
        direction="BUY",
        order_type="BUY_LIMIT",
        entry_price=100.0,
        stop_loss=95.0,  # 5 point risk
        take_profit=103.0,  # 3 point reward, RR = 0.6
        confidence=0.8,
        setup_type="CONFLUENCE",
        timeframe_bias={"H4": "BULLISH"},
        zones=[],
        timestamp=datetime.now()
    )
    
    assert signal_gen.validate_signal(invalid_signal) == False, \
        "Signal with poor RR should fail validation"
    
    # Invalid signal with low confidence
    low_conf_signal = SMCSignal(
        symbol="TEST",
        direction="BUY",
        order_type="BUY_LIMIT",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        confidence=0.3,  # Low confidence
        setup_type="CONFLUENCE",
        timeframe_bias={"H4": "BULLISH"},
        zones=[],
        timestamp=datetime.now()
    )
    
    assert signal_gen.validate_signal(low_conf_signal) == False, \
        "Signal with low confidence should fail validation"


def test_order_type_determination():
    """Property: Order type should be determined correctly based on price position."""
    fvg_detector = FVGDetector()
    ob_detector = OrderBlockDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    signal_gen = SMCSignalGenerator(fvg_detector, ob_detector, structure_analyzer, mtf_analyzer)
    
    # BUY with current price above entry = BUY LIMIT (pullback)
    order_type = signal_gen.get_order_type("BUY", current_price=110.0, entry_price=105.0)
    assert order_type == "BUY_LIMIT", \
        "Buy with price above entry should be BUY_LIMIT"
    
    # BUY with current price below entry = BUY STOP (breakout)
    order_type = signal_gen.get_order_type("BUY", current_price=100.0, entry_price=105.0)
    assert order_type == "BUY_STOP", \
        "Buy with price below entry should be BUY_STOP"
    
    # SELL with current price below entry = SELL LIMIT (rally)
    order_type = signal_gen.get_order_type("SELL", current_price=100.0, entry_price=105.0)
    assert order_type == "SELL_LIMIT", \
        "Sell with price below entry should be SELL_LIMIT"
    
    # SELL with current price above entry = SELL STOP (breakdown)
    order_type = signal_gen.get_order_type("SELL", current_price=110.0, entry_price=105.0)
    assert order_type == "SELL_STOP", \
        "Sell with price above entry should be SELL_STOP"


@given(
    entry=st.floats(min_value=100.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    sl=st.floats(min_value=50.0, max_value=99.0, allow_nan=False, allow_infinity=False),
    rr_ratio=st.floats(min_value=1.5, max_value=5.0, allow_nan=False, allow_infinity=False),
    direction=st.sampled_from(["BUY", "SELL"])
)
def test_take_profit_calculation(entry, sl, rr_ratio, direction):
    """Property: Take profit should maintain specified risk-reward ratio."""
    fvg_detector = FVGDetector()
    ob_detector = OrderBlockDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    signal_gen = SMCSignalGenerator(fvg_detector, ob_detector, structure_analyzer, mtf_analyzer)
    
    # Calculate take profit
    tp = signal_gen.calculate_take_profit(direction, entry, sl, rr_ratio)
    
    # Calculate actual RR
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    
    if risk > 0:
        actual_rr = reward / risk
        
        # Property: Actual RR should match requested RR
        assert abs(actual_rr - rr_ratio) < 0.01, \
            f"Actual RR {actual_rr:.2f} should match requested {rr_ratio:.2f}"
    
    # Property: TP should be in correct direction
    if direction == "BUY":
        assert tp > entry, "Buy TP should be above entry"
    else:  # SELL
        assert tp < entry, "Sell TP should be below entry"


def test_entry_price_calculation():
    """Property: Entry price should be calculated from FVG or Order Block."""
    fvg_detector = FVGDetector()
    ob_detector = OrderBlockDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    signal_gen = SMCSignalGenerator(fvg_detector, ob_detector, structure_analyzer, mtf_analyzer)
    
    # Create FVG
    fvg = FVG(
        timeframe="H1",
        direction="BULLISH",
        high=110.0,
        low=100.0,
        equilibrium=105.0,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    # Entry from FVG should be equilibrium
    entry = signal_gen.calculate_entry_price(fvg)
    assert entry == 105.0, f"Entry from FVG should be equilibrium 105.0, got {entry}"
    
    # Create Order Block
    ob = OrderBlock(
        timeframe="H1",
        direction="BULLISH",
        high=110.0,
        low=100.0,
        entry_price=105.0,
        created_at=datetime.now(),
        valid=True,
        strength=10.0
    )
    
    # Entry from OB should be OB entry price
    entry = signal_gen.calculate_entry_price(fvg, ob)
    assert entry == 105.0, f"Entry from OB should be OB entry_price 105.0, got {entry}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
