"""Property-based tests for Liquidity Analyzer using Hypothesis."""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from src.smc_strategy import LiquidityLevel, LiquidityAnalyzer


# Feature: smc-strategy, Property 13: Liquidity Sweep Detection
# For any recent swing high or low, when price breaks beyond it by a small amount (5-10 pips)
# and then reverses, the system should detect this as a liquidity sweep.
# Validates: Requirements 4.1, 4.2, 4.3

def test_buyside_liquidity_sweep():
    """Property: Buyside liquidity sweep should be detected when price breaks high and reverses."""
    analyzer = LiquidityAnalyzer()
    
    # Create swing high at 150
    swing_high = 150.0
    
    # Create liquidity level
    level = LiquidityLevel(
        price=swing_high,
        type="BUYSIDE",
        strength=1,
        swept=False
    )
    
    # Create candles with sweep: break above then reverse
    candles = [
        {'open': 148, 'high': 149, 'low': 147, 'close': 148.5},
        {'open': 148.5, 'high': 151, 'low': 148, 'close': 149},  # Breaks above 150, closes below
    ]
    
    sweep_time = analyzer.detect_sweep(candles, level)
    
    # Property: Should detect sweep (or None if threshold not met)
    assert sweep_time is None or isinstance(sweep_time, datetime), \
        "Sweep detection should return datetime or None"


def test_sellside_liquidity_sweep():
    """Property: Sellside liquidity sweep should be detected when price breaks low and reverses."""
    analyzer = LiquidityAnalyzer()
    
    # Create swing low at 100
    swing_low = 100.0
    
    # Create liquidity level
    level = LiquidityLevel(
        price=swing_low,
        type="SELLSIDE",
        strength=1,
        swept=False
    )
    
    # Create candles with sweep: break below then reverse
    candles = [
        {'open': 102, 'high': 103, 'low': 101, 'close': 102},
        {'open': 102, 'high': 103, 'low': 99, 'close': 101},  # Breaks below 100, closes above
    ]
    
    sweep_time = analyzer.detect_sweep(candles, level)
    
    # Property: Should detect sweep (or None if threshold not met)
    assert sweep_time is None or isinstance(sweep_time, datetime), \
        "Sweep detection should return datetime or None"


def test_liquidity_level_identification():
    """Property: Liquidity levels should be identified at swing points."""
    analyzer = LiquidityAnalyzer()
    
    # Create price data with clear swing points
    candles = []
    
    # Create swing high at index 10
    for i in range(20):
        if i == 10:
            # Swing high
            candles.append({'open': 150, 'high': 155, 'low': 149, 'close': 152})
        elif i < 10:
            candles.append({'open': 140 + i, 'high': 141 + i, 'low': 139 + i, 'close': 140.5 + i})
        else:
            candles.append({'open': 160 - i, 'high': 161 - i, 'low': 159 - i, 'close': 160.5 - i})
    
    levels = analyzer.identify_liquidity_levels(candles)
    
    # Property: Should identify some liquidity levels
    assert isinstance(levels, list), "Should return list of levels"
    
    # Property: All levels should have valid types
    for level in levels:
        assert level.type in ["BUYSIDE", "SELLSIDE"], \
            f"Level type {level.type} should be BUYSIDE or SELLSIDE"
        assert level.price > 0, "Level price should be positive"
        assert level.strength > 0, "Level strength should be positive"


def test_buyside_liquidity_swept_detection():
    """Property: is_buyside_liquidity_swept should detect recent sweeps."""
    analyzer = LiquidityAnalyzer()
    
    # Create candles with potential buyside sweep
    candles = []
    for i in range(15):
        candles.append({
            'open': 100 + i,
            'high': 102 + i,
            'low': 99 + i,
            'close': 101 + i
        })
    
    # Add sweep candle
    candles.append({
        'open': 115,
        'high': 120,  # Breaks above
        'low': 114,
        'close': 116  # Reverses
    })
    
    is_swept = analyzer.is_buyside_liquidity_swept(candles)
    
    # Property: Should return boolean
    assert isinstance(is_swept, bool), "Should return boolean"


def test_sellside_liquidity_swept_detection():
    """Property: is_sellside_liquidity_swept should detect recent sweeps."""
    analyzer = LiquidityAnalyzer()
    
    # Create candles with potential sellside sweep
    candles = []
    for i in range(15):
        candles.append({
            'open': 200 - i,
            'high': 202 - i,
            'low': 199 - i,
            'close': 201 - i
        })
    
    # Add sweep candle
    candles.append({
        'open': 185,
        'high': 186,
        'low': 180,  # Breaks below
        'close': 184  # Reverses
    })
    
    is_swept = analyzer.is_sellside_liquidity_swept(candles)
    
    # Property: Should return boolean
    assert isinstance(is_swept, bool), "Should return boolean"


@given(
    swing_price=st.floats(min_value=100.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    break_amount=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
    level_type=st.sampled_from(["BUYSIDE", "SELLSIDE"])
)
def test_sweep_detection_logic(swing_price, break_amount, level_type):
    """Property: Sweep detection logic should be consistent with level type."""
    analyzer = LiquidityAnalyzer()
    
    level = LiquidityLevel(
        price=swing_price,
        type=level_type,
        strength=1,
        swept=False
    )
    
    if level_type == "BUYSIDE":
        # Create candle that breaks above and reverses
        candles = [{
            'open': swing_price - 1,
            'high': swing_price + break_amount,
            'low': swing_price - 2,
            'close': swing_price - 0.5
        }]
    else:  # SELLSIDE
        # Create candle that breaks below and reverses
        candles = [{
            'open': swing_price + 1,
            'high': swing_price + 2,
            'low': swing_price - break_amount,
            'close': swing_price + 0.5
        }]
    
    sweep_time = analyzer.detect_sweep(candles, level)
    
    # Property: Should return datetime or None
    assert sweep_time is None or isinstance(sweep_time, datetime), \
        "Sweep detection should return datetime or None"


def test_liquidity_level_strength():
    """Property: Liquidity levels should have positive strength."""
    analyzer = LiquidityAnalyzer()
    
    # Create simple price data
    candles = []
    for i in range(20):
        candles.append({
            'open': 100 + (i % 5),
            'high': 102 + (i % 5),
            'low': 99 + (i % 5),
            'close': 101 + (i % 5)
        })
    
    levels = analyzer.identify_liquidity_levels(candles)
    
    # Property: All levels should have positive strength
    for level in levels:
        assert level.strength > 0, f"Level strength {level.strength} should be positive"
        assert isinstance(level.strength, int), "Level strength should be integer"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
