"""Property-based tests for Order Block Detector using Hypothesis."""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from src.smc_strategy import OrderBlock, BreakerBlock, OrderBlockDetector


# Feature: smc-strategy, Property 7: Order Block Level Calculation
# For any detected Order Block, it should have high, low, and entry_price (50% level) calculated,
# where entry_price = (high + low) / 2.
# Validates: Requirements 2.2

@given(
    high=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    low=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
)
def test_order_block_level_calculation(high, low):
    """Property: Order Block entry_price should always equal (high + low) / 2."""
    # Ensure high > low
    if high < low:
        high, low = low, high
    
    if high == low:
        return  # Skip degenerate case
    
    # Create Order Block
    ob = OrderBlock(
        timeframe="H1",
        direction="BULLISH",
        high=high,
        low=low,
        entry_price=(high + low) / 2,
        created_at=datetime.now(),
        valid=True,
        strength=10.0
    )
    
    detector = OrderBlockDetector()
    
    # Property 1: Entry price should equal (high + low) / 2
    expected_entry = (high + low) / 2
    assert abs(ob.entry_price - expected_entry) < 0.0001, \
        f"Entry price {ob.entry_price} != (high + low) / 2 = {expected_entry}"
    
    # Property 2: get_order_block_entry should return entry_price
    calculated_entry = detector.get_order_block_entry(ob)
    assert abs(calculated_entry - ob.entry_price) < 0.0001, \
        f"Calculated entry {calculated_entry} != stored entry {ob.entry_price}"
    
    # Property 3: All three levels should be populated
    assert ob.high is not None, "High should be populated"
    assert ob.low is not None, "Low should be populated"
    assert ob.entry_price is not None, "Entry price should be populated"
    
    # Property 4: Entry price should be between high and low
    assert low <= ob.entry_price <= high, \
        f"Entry price {ob.entry_price} should be between low {low} and high {high}"


# Feature: smc-strategy, Property 8: Order Block to Breaker Block Conversion
# For any Order Block, when price breaks through it (closes beyond the opposite extreme),
# it should be converted to a Breaker Block with opposite direction.
# Validates: Requirements 2.3

@given(
    ob_high=st.floats(min_value=100.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    ob_low=st.floats(min_value=50.0, max_value=99.0, allow_nan=False, allow_infinity=False),
    break_price=st.floats(min_value=1.0, max_value=300.0, allow_nan=False, allow_infinity=False),
    direction=st.sampled_from(["BULLISH", "BEARISH"])
)
def test_order_block_to_breaker_block_conversion(ob_high, ob_low, break_price, direction):
    """Property: Order Block should convert to Breaker Block when broken."""
    detector = OrderBlockDetector()
    
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
    
    # Create candle that breaks the OB
    candles = [
        {'open': break_price, 'high': break_price + 5, 'low': break_price - 5, 'close': break_price}
    ]
    
    # Detect breaker blocks
    breaker_blocks = detector.detect_breaker_blocks([ob], candles)
    
    # Property: If OB is broken, it should become a Breaker Block
    if direction == "BULLISH":
        # Bullish OB broken if price closes below low
        is_broken = break_price < ob_low
    else:  # BEARISH
        # Bearish OB broken if price closes above high
        is_broken = break_price > ob_high
    
    if is_broken:
        # Should have created a Breaker Block
        assert len(breaker_blocks) >= 1, \
            f"Expected Breaker Block when {direction} OB broken at {break_price}"
        
        bb = breaker_blocks[0]
        
        # Property: Breaker Block should have opposite direction
        expected_direction = "BEARISH" if direction == "BULLISH" else "BULLISH"
        assert bb.direction == expected_direction, \
            f"Breaker Block direction {bb.direction} should be opposite of OB {direction}"
        
        # Property: Original OB should be invalidated
        assert not ob.valid, "Original Order Block should be invalidated"
        
        # Property: Breaker Block should reference original OB
        assert bb.original_ob == ob, "Breaker Block should reference original OB"
    else:
        # Should not have created a Breaker Block
        assert len(breaker_blocks) == 0, \
            f"Should not create Breaker Block when {direction} OB not broken at {break_price}"


@given(
    high=st.floats(min_value=100.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    low=st.floats(min_value=50.0, max_value=99.0, allow_nan=False, allow_infinity=False),
    current_price=st.floats(min_value=1.0, max_value=300.0, allow_nan=False, allow_infinity=False),
    direction=st.sampled_from(["BULLISH", "BEARISH"])
)
def test_order_block_validity(high, low, current_price, direction):
    """Property: Order Block validity should be correctly determined."""
    detector = OrderBlockDetector()
    
    ob = OrderBlock(
        timeframe="H1",
        direction=direction,
        high=high,
        low=low,
        entry_price=(high + low) / 2,
        created_at=datetime.now(),
        valid=True,
        strength=10.0
    )
    
    is_valid = detector.is_order_block_valid(ob, current_price)
    
    # Property: Validity logic should match direction
    if direction == "BULLISH":
        # Bullish OB valid if price >= low
        expected_valid = current_price >= low
    else:  # BEARISH
        # Bearish OB valid if price <= high
        expected_valid = current_price <= high
    
    assert is_valid == expected_valid, \
        f"{direction} OB validity {is_valid} incorrect for price {current_price}"


def test_order_block_detection_with_real_candles():
    """Unit test: Verify Order Block detection with known candle patterns."""
    detector = OrderBlockDetector()
    
    # Bullish Order Block: Last red candle before 3+ green candles
    # Need at least 5 candles for detection (i + 4)
    candles = [
        {'open': 105, 'high': 110, 'low': 100, 'close': 102},  # i=0: Red candle (OB)
        {'open': 102, 'high': 115, 'low': 101, 'close': 113},  # i=1: Green 1
        {'open': 113, 'high': 120, 'low': 112, 'close': 118},  # i=2: Green 2
        {'open': 118, 'high': 125, 'low': 117, 'close': 123},  # i=3: Green 3
        {'open': 123, 'high': 128, 'low': 122, 'close': 126},  # i=4: Extra candle
    ]
    
    obs = detector.detect_order_blocks(candles)
    
    assert len(obs) >= 1, f"Expected at least 1 Order Block, got {len(obs)}"
    
    # Find bullish OB
    bullish_obs = [ob for ob in obs if ob.direction == "BULLISH"]
    assert len(bullish_obs) >= 1, "Expected at least 1 bullish Order Block"
    
    ob = bullish_obs[0]
    assert ob.high == 110  # High of red candle
    assert ob.low == 100   # Low of red candle
    assert abs(ob.entry_price - 105.0) < 0.01  # 50% level


def test_breaker_block_creation():
    """Unit test: Verify Breaker Block creation when OB is broken."""
    detector = OrderBlockDetector()
    
    # Create bullish Order Block
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
    
    # Create candle that breaks below the OB
    candles = [
        {'open': 98, 'high': 102, 'low': 95, 'close': 96}  # Closes below OB low
    ]
    
    bbs = detector.detect_breaker_blocks([ob], candles)
    
    assert len(bbs) == 1, f"Expected 1 Breaker Block, got {len(bbs)}"
    assert bbs[0].direction == "BEARISH", "Breaker Block should be bearish"
    assert not ob.valid, "Original OB should be invalidated"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
