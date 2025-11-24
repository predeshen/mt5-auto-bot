"""Property-based tests for Multi-Timeframe Analyzer using Hypothesis."""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from src.smc_strategy import (
    FVG, MarketStructure, ConfluenceZone, TimeframeAnalysis,
    FVGDetector, MarketStructureAnalyzer, MultiTimeframeAnalyzer
)


# Feature: smc-strategy, Property 1: Multi-timeframe FVG Detection
# For any symbol with price data, when the FVG detector analyzes the data,
# it should return FVG lists for all four timeframes (H4, H1, M15, M5).
# Validates: Requirements 1.1

def test_multi_timeframe_fvg_detection():
    """Property: Multi-timeframe analysis should return FVGs for all timeframes."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    # Create sample candles for each timeframe
    candles = []
    for i in range(20):
        candles.append({
            'open': 100 + i,
            'high': 102 + i,
            'low': 99 + i,
            'close': 101 + i
        })
    
    candles_by_tf = {
        "H4": candles,
        "H1": candles,
        "M15": candles,
        "M5": candles
    }
    
    analysis = mtf_analyzer.analyze_all_timeframes("TEST", candles_by_tf)
    
    # Property: Should return TimeframeAnalysis object
    assert isinstance(analysis, TimeframeAnalysis), "Should return TimeframeAnalysis"
    
    # Property: Should have FVG lists for all timeframes
    assert isinstance(analysis.h4_fvgs, list), "H4 FVGs should be a list"
    assert isinstance(analysis.h1_fvgs, list), "H1 FVGs should be a list"
    assert isinstance(analysis.m15_fvgs, list), "M15 FVGs should be a list"
    assert isinstance(analysis.m5_fvgs, list), "M5 FVGs should be a list"


# Feature: smc-strategy, Property 4: Timeframe Confluence Detection
# For any pair of FVGs from different timeframes that overlap in price range,
# the system should flag them as high-priority/high-confidence zones.
# Validates: Requirements 1.4, 6.3

@given(
    h4_high=st.floats(min_value=110.0, max_value=120.0, allow_nan=False, allow_infinity=False),
    h4_low=st.floats(min_value=100.0, max_value=109.0, allow_nan=False, allow_infinity=False),
    h1_high=st.floats(min_value=110.0, max_value=120.0, allow_nan=False, allow_infinity=False),
    h1_low=st.floats(min_value=100.0, max_value=109.0, allow_nan=False, allow_infinity=False)
)
def test_fvg_alignment_detection(h4_high, h4_low, h1_high, h1_low):
    """Property: FVG alignment should detect overlapping FVGs."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    # Create H4 FVG
    h4_fvg = FVG(
        timeframe="H4",
        direction="BULLISH",
        high=h4_high,
        low=h4_low,
        equilibrium=(h4_high + h4_low) / 2,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    # Create H1 FVG
    h1_fvg = FVG(
        timeframe="H1",
        direction="BULLISH",
        high=h1_high,
        low=h1_low,
        equilibrium=(h1_high + h1_low) / 2,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    # Check alignment
    is_aligned = mtf_analyzer.check_fvg_alignment(h4_fvg, h1_fvg)
    
    # Property: Alignment should be True if ranges overlap
    ranges_overlap = not (h4_high < h1_low or h1_high < h4_low)
    
    if ranges_overlap:
        assert is_aligned == True, \
            f"FVGs should align when ranges overlap: H4[{h4_low}-{h4_high}] H1[{h1_low}-{h1_high}]"
    else:
        assert is_aligned == False, \
            f"FVGs should not align when ranges don't overlap: H4[{h4_low}-{h4_high}] H1[{h1_low}-{h1_high}]"


def test_confluence_zone_creation():
    """Property: Confluence zones should be created when FVGs align."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    # Create overlapping FVGs
    h4_fvg = FVG(
        timeframe="H4",
        direction="BULLISH",
        high=115.0,
        low=105.0,
        equilibrium=110.0,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    h1_fvg = FVG(
        timeframe="H1",
        direction="BULLISH",
        high=112.0,
        low=108.0,
        equilibrium=110.0,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    analysis = TimeframeAnalysis(
        h4_fvgs=[h4_fvg],
        h1_fvgs=[h1_fvg]
    )
    
    confluence_zones = mtf_analyzer.find_confluence_zones(analysis)
    
    # Property: Should create confluence zone for overlapping FVGs
    assert len(confluence_zones) >= 1, "Should create at least one confluence zone"
    
    zone = confluence_zones[0]
    assert isinstance(zone, ConfluenceZone), "Should be ConfluenceZone object"
    assert "H4_FVG" in zone.components, "Should include H4_FVG component"
    assert "H1_FVG" in zone.components, "Should include H1_FVG component"
    assert zone.confidence > 0, "Confidence should be positive"


def test_htf_bias_determination():
    """Property: HTF bias should be determined from H4 and H1 structure."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    # Create uptrend structures
    h4_structure = MarketStructure(
        trend="UPTREND",
        swing_highs=[100, 105, 110],
        swing_lows=[95, 100, 105]
    )
    
    h1_structure = MarketStructure(
        trend="UPTREND",
        swing_highs=[108, 109, 110],
        swing_lows=[106, 107, 108]
    )
    
    bias = mtf_analyzer.get_htf_bias(h4_structure, h1_structure)
    
    # Property: Both uptrends should give BULLISH bias
    assert bias == "BULLISH", f"Both uptrends should give BULLISH bias, got {bias}"
    
    # Test downtrend
    h4_structure.trend = "DOWNTREND"
    h1_structure.trend = "DOWNTREND"
    
    bias = mtf_analyzer.get_htf_bias(h4_structure, h1_structure)
    
    # Property: Both downtrends should give BEARISH bias
    assert bias == "BEARISH", f"Both downtrends should give BEARISH bias, got {bias}"


def test_equilibrium_calculation():
    """Property: Equilibrium should always be (high + low) / 2."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    high = 120.0
    low = 100.0
    
    equilibrium = mtf_analyzer.calculate_equilibrium(high, low)
    
    # Property: Equilibrium should be midpoint
    expected = (high + low) / 2
    assert abs(equilibrium - expected) < 0.0001, \
        f"Equilibrium {equilibrium} should equal (high + low) / 2 = {expected}"
    
    # Property: Equilibrium should be between high and low
    assert low <= equilibrium <= high, \
        f"Equilibrium {equilibrium} should be between low {low} and high {high}"


@given(
    current_price=st.floats(min_value=50.0, max_value=150.0, allow_nan=False, allow_infinity=False),
    equilibrium=st.floats(min_value=90.0, max_value=110.0, allow_nan=False, allow_infinity=False)
)
def test_zone_classification(current_price, equilibrium):
    """Property: Zone classification should be consistent with price vs equilibrium."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    zone = mtf_analyzer.classify_zone(current_price, equilibrium)
    
    # Property: Classification should match price position
    if current_price > equilibrium:
        assert zone == "PREMIUM", \
            f"Price {current_price} > equilibrium {equilibrium} should be PREMIUM, got {zone}"
    else:
        assert zone == "DISCOUNT", \
            f"Price {current_price} <= equilibrium {equilibrium} should be DISCOUNT, got {zone}"


def test_bias_from_zone():
    """Property: Trading bias should be opposite of zone (sell premium, buy discount)."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    # Premium zone should give SELL bias
    bias = mtf_analyzer.get_bias_from_zone("PREMIUM")
    assert bias == "SELL", f"Premium zone should give SELL bias, got {bias}"
    
    # Discount zone should give BUY bias
    bias = mtf_analyzer.get_bias_from_zone("DISCOUNT")
    assert bias == "BUY", f"Discount zone should give BUY bias, got {bias}"


def test_fvg_alignment_requires_same_direction():
    """Property: FVGs must have same direction to align."""
    fvg_detector = FVGDetector()
    structure_analyzer = MarketStructureAnalyzer()
    mtf_analyzer = MultiTimeframeAnalyzer(fvg_detector, structure_analyzer)
    
    # Create overlapping FVGs with different directions
    h4_fvg = FVG(
        timeframe="H4",
        direction="BULLISH",
        high=115.0,
        low=105.0,
        equilibrium=110.0,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    h1_fvg = FVG(
        timeframe="H1",
        direction="BEARISH",  # Different direction
        high=112.0,
        low=108.0,
        equilibrium=110.0,
        created_at=datetime.now(),
        filled=False,
        candle_index=0
    )
    
    is_aligned = mtf_analyzer.check_fvg_alignment(h4_fvg, h1_fvg)
    
    # Property: Different directions should not align
    assert is_aligned == False, \
        "FVGs with different directions should not align"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
