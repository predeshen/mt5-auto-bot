# Design Document

## Overview

This design modifies the HTF (Higher Timeframe) bias calculation in the SMC strategy to be less conservative. Currently, the system requires both H4 and H1 to show clear trends before allowing trades. The new design will allow H1 trends to generate trading signals even when H4 is ranging, while maintaining the existing priority system when both timeframes have clear trends.

## Architecture

The modification will be made to the `MultiTimeframeAnalyzer` class in `src/smc_strategy.py`. Specifically, the `get_htf_bias()` method will be updated to handle the case where H1 has a clear trend but H4 is ranging.

### Current Flow
1. Analyze H4 and H1 market structures
2. Check if both agree on direction → return that direction
3. Check if H4 has clear trend → return H4 direction (priority)
4. Otherwise → return NEUTRAL

### New Flow
1. Analyze H4 and H1 market structures
2. Check if both agree on direction → return that direction (highest confidence)
3. Check if H4 has clear trend → return H4 direction (high confidence, H4 priority)
4. **NEW:** Check if H1 has clear trend while H4 is ranging → return H1 direction (medium confidence)
5. Otherwise → return NEUTRAL (both ranging)

## Components and Interfaces

### Modified Component: MultiTimeframeAnalyzer

**Method:** `get_htf_bias(h4_data: Optional[MarketStructure], h1_data: Optional[MarketStructure]) -> str`

**Current Signature:**
```python
def get_htf_bias(self, h4_data: Optional[MarketStructure], h1_data: Optional[MarketStructure]) -> str:
    """Returns: "BULLISH", "BEARISH", or "NEUTRAL" """
```

**New Signature (unchanged but behavior modified):**
```python
def get_htf_bias(self, h4_data: Optional[MarketStructure], h1_data: Optional[MarketStructure]) -> str:
    """
    Get higher timeframe bias from H4 and H1.
    
    Priority order:
    1. Both timeframes agree → return agreed direction
    2. H4 has clear trend → return H4 direction (takes priority)
    3. H1 has clear trend while H4 ranging → return H1 direction
    4. Both ranging → return NEUTRAL
    
    Returns: "BULLISH", "BEARISH", or "NEUTRAL"
    """
```

## Data Models

No new data models required. Existing `MarketStructure` dataclass is sufficient:

```python
@dataclass
class MarketStructure:
    trend: str  # "UPTREND", "DOWNTREND", "RANGING"
    swing_highs: List[float]
    swing_lows: List[float]
    last_bos: Optional[datetime]
    last_choch: Optional[datetime]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: H1 trend with H4 ranging produces H1 bias

*For any* market structure where H1 is UPTREND and H4 is RANGING, the HTF bias should be BULLISH

**Validates: Requirements 1.1**

### Property 2: H1 downtrend with H4 ranging produces bearish bias

*For any* market structure where H1 is DOWNTREND and H4 is RANGING, the HTF bias should be BEARISH

**Validates: Requirements 1.2**

### Property 3: Agreement produces agreed bias

*For any* market structure where both H4 and H1 are UPTREND, the HTF bias should be BULLISH

**Validates: Requirements 1.3, 2.1**

### Property 4: Downtrend agreement produces bearish bias

*For any* market structure where both H4 and H1 are DOWNTREND, the HTF bias should be BEARISH

**Validates: Requirements 1.4, 2.2**

### Property 5: Both ranging produces neutral

*For any* market structure where both H4 and H1 are RANGING, the HTF bias should be NEUTRAL

**Validates: Requirements 1.5**

### Property 6: H4 priority on conflict

*For any* market structure where H4 is UPTREND and H1 is DOWNTREND, the HTF bias should be BULLISH (H4 takes priority)

**Validates: Requirements 2.3**

### Property 7: H4 priority on bearish conflict

*For any* market structure where H4 is DOWNTREND and H1 is UPTREND, the HTF bias should be BEARISH (H4 takes priority)

**Validates: Requirements 2.4**

## Error Handling

The method already handles None values for h4_data and h1_data by returning "NEUTRAL". This behavior will be maintained.

**Edge Cases:**
- If h4_data is None → check h1_data only
- If h1_data is None → check h4_data only  
- If both are None → return NEUTRAL

## Testing Strategy

### Unit Tests
- Test each specific combination of H4/H1 trends
- Test None handling for missing data
- Test logging output contains expected information

### Property-Based Tests
- Generate random combinations of H4 and H1 trends
- Verify bias calculation follows the priority rules
- Verify that UPTREND/DOWNTREND always produce BULLISH/BEARISH (never NEUTRAL) when at least one timeframe has a trend

### Integration Tests
- Run the full SMC strategy with the modified bias calculation
- Verify that signals are now generated when H1 has clear trends
- Verify that existing high-confidence setups still work correctly

## Implementation Notes

1. The modification is minimal - only the `get_htf_bias()` method needs to be changed
2. Add logging statements to show H4 trend, H1 trend, and resulting bias
3. The change is backward compatible - existing behavior for agreeing timeframes is unchanged
4. This change will immediately allow the system to generate signals in the current market conditions where H1 shows UPTREND but H4 is RANGING
