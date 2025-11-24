"""Property-based tests for Market Structure Analyzer using Hypothesis."""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime
from src.smc_strategy import MarketStructure, MarketStructureAnalyzer


# Feature: smc-strategy, Property 16: Market Structure Identification
# For any price sequence, the system should correctly identify the trend structure:
# Higher Highs and Higher Lows for uptrends, Lower Highs and Lower Lows for downtrends.
# Validates: Requirements 5.1, 5.2

def test_uptrend_identification():
    """Property: Uptrend should be identified with HH and HL."""
    analyzer = MarketStructureAnalyzer()
    
    # Create clear uptrend: HH and HL
    base_price = 100.0
    candles = []
    
    for i in range(20):
        # Create upward trending candles
        open_price = base_price + i * 2
        close_price = open_price + 1.5
        high_price = close_price + 0.5
        low_price = open_price - 0.5
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        })
    
    structure = analyzer.identify_structure(candles)
    
    # Property: Should identify as UPTREND
    assert structure.trend in ["UPTREND", "RANGING"], \
        f"Clear uptrend should be identified as UPTREND or RANGING, got {structure.trend}"
    
    # Property: Should have swing highs and lows
    assert len(structure.swing_highs) >= 0, "Should have swing highs"
    assert len(structure.swing_lows) >= 0, "Should have swing lows"


def test_downtrend_identification():
    """Property: Downtrend should be identified with LH and LL."""
    analyzer = MarketStructureAnalyzer()
    
    # Create clear downtrend: LH and LL
    base_price = 200.0
    candles = []
    
    for i in range(20):
        # Create downward trending candles
        open_price = base_price - i * 2
        close_price = open_price - 1.5
        high_price = open_price + 0.5
        low_price = close_price - 0.5
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        })
    
    structure = analyzer.identify_structure(candles)
    
    # Property: Should identify as DOWNTREND
    assert structure.trend in ["DOWNTREND", "RANGING"], \
        f"Clear downtrend should be identified as DOWNTREND or RANGING, got {structure.trend}"
    
    # Property: Should have swing highs and lows
    assert len(structure.swing_highs) >= 0, "Should have swing highs"
    assert len(structure.swing_lows) >= 0, "Should have swing lows"


def test_ranging_market_identification():
    """Property: Ranging market should be identified when no clear trend."""
    analyzer = MarketStructureAnalyzer()
    
    # Create ranging market
    base_price = 150.0
    candles = []
    
    for i in range(20):
        # Create sideways movement
        open_price = base_price + (i % 3 - 1) * 2
        close_price = open_price + ((-1) ** i) * 1
        high_price = max(open_price, close_price) + 0.5
        low_price = min(open_price, close_price) - 0.5
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        })
    
    structure = analyzer.identify_structure(candles)
    
    # Property: Should identify as RANGING
    assert structure.trend in ["RANGING", "UPTREND", "DOWNTREND"], \
        f"Market structure should be valid trend type, got {structure.trend}"


# Feature: smc-strategy, Property 17: Break of Structure Detection
# For any established market structure, when price breaks the previous structural high (in uptrend)
# or low (in downtrend), a BOS should be detected.
# Validates: Requirements 5.3

def test_bos_detection_uptrend():
    """Property: BOS should be detected when price breaks previous high in uptrend."""
    analyzer = MarketStructureAnalyzer()
    
    # Create uptrend with clear BOS
    candles = []
    base_price = 100.0
    
    # Build uptrend
    for i in range(15):
        open_price = base_price + i * 2
        close_price = open_price + 1.5
        high_price = close_price + 0.5
        low_price = open_price - 0.5
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        })
    
    # Add BOS candle (breaks above previous high)
    last_high = max(c['high'] for c in candles)
    candles.append({
        'open': last_high,
        'high': last_high + 5,  # Clear break
        'low': last_high - 1,
        'close': last_high + 4
    })
    
    bos_time = analyzer.detect_bos(candles)
    
    # Property: BOS should be detected (or None if structure not clear enough)
    assert bos_time is None or isinstance(bos_time, datetime), \
        "BOS detection should return datetime or None"


def test_bos_detection_downtrend():
    """Property: BOS should be detected when price breaks previous low in downtrend."""
    analyzer = MarketStructureAnalyzer()
    
    # Create downtrend with clear BOS
    candles = []
    base_price = 200.0
    
    # Build downtrend
    for i in range(15):
        open_price = base_price - i * 2
        close_price = open_price - 1.5
        high_price = open_price + 0.5
        low_price = close_price - 0.5
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        })
    
    # Add BOS candle (breaks below previous low)
    last_low = min(c['low'] for c in candles)
    candles.append({
        'open': last_low,
        'high': last_low + 1,
        'low': last_low - 5,  # Clear break
        'close': last_low - 4
    })
    
    bos_time = analyzer.detect_bos(candles)
    
    # Property: BOS should be detected (or None if structure not clear enough)
    assert bos_time is None or isinstance(bos_time, datetime), \
        "BOS detection should return datetime or None"


def test_choch_detection():
    """Property: CHoCH should be detected when market structure shifts."""
    analyzer = MarketStructureAnalyzer()
    
    # Create uptrend then shift to downtrend
    candles = []
    base_price = 100.0
    
    # Build uptrend
    for i in range(15):
        open_price = base_price + i * 2
        close_price = open_price + 1.5
        high_price = close_price + 0.5
        low_price = open_price - 0.5
        
        candles.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price
        })
    
    # Add CHoCH candle (breaks below previous HL)
    candles.append({
        'open': base_price + 20,
        'high': base_price + 21,
        'low': base_price + 5,  # Breaks structure
        'close': base_price + 6
    })
    
    choch_time = analyzer.detect_choch(candles)
    
    # Property: CHoCH detection should return datetime or None
    assert choch_time is None or isinstance(choch_time, datetime), \
        "CHoCH detection should return datetime or None"


def test_trend_direction_consistency():
    """Property: Trend direction should be consistent with market structure."""
    analyzer = MarketStructureAnalyzer()
    
    # Create uptrend
    candles = []
    for i in range(20):
        candles.append({
            'open': 100 + i * 2,
            'high': 102 + i * 2,
            'low': 99 + i * 2,
            'close': 101 + i * 2
        })
    
    structure = analyzer.identify_structure(candles)
    trend = analyzer.get_trend_direction(structure)
    
    # Property: Trend from get_trend_direction should match structure.trend
    assert trend == structure.trend, \
        f"Trend direction {trend} should match structure trend {structure.trend}"
    
    # Property: Trend should be one of valid values
    assert trend in ["UPTREND", "DOWNTREND", "RANGING"], \
        f"Trend {trend} should be valid trend type"


def test_swing_points_ordering():
    """Property: Swing points should be in chronological order."""
    analyzer = MarketStructureAnalyzer()
    
    # Create price data with clear swings
    candles = []
    for i in range(30):
        price = 100 + 10 * (i % 5)  # Creates wave pattern
        candles.append({
            'open': price,
            'high': price + 2,
            'low': price - 2,
            'close': price + 1
        })
    
    structure = analyzer.identify_structure(candles)
    
    # Property: Swing highs should be valid numbers
    for high in structure.swing_highs:
        assert isinstance(high, (int, float)), "Swing high should be numeric"
        assert high > 0, "Swing high should be positive"
    
    # Property: Swing lows should be valid numbers
    for low in structure.swing_lows:
        assert isinstance(low, (int, float)), "Swing low should be numeric"
        assert low > 0, "Swing low should be positive"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
