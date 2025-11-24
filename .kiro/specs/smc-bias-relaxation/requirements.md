# Requirements Document

## Introduction

The SMC (Smart Money Concepts) strategy is currently detecting FVGs and Order Blocks correctly but not placing any trades because the Higher Timeframe (HTF) Bias calculation is too conservative. The system requires both H4 and H1 timeframes to show a clear trend (UPTREND or DOWNTREND) before allowing trades. However, in current market conditions, H4 is showing RANGING while H1 shows UPTREND, resulting in a NEUTRAL bias that prevents all trade execution.

This feature will relax the HTF bias calculation to allow trades when H1 shows a clear trend, even if H4 is ranging, while still maintaining risk management and quality signal generation.

## Glossary

- **HTF Bias**: Higher Timeframe Bias - the overall directional bias determined from H4 and H1 timeframes
- **H4**: 4-hour timeframe
- **H1**: 1-hour timeframe  
- **FVG**: Fair Value Gap - price imbalance zones
- **Order Block**: Institutional supply/demand zones
- **Market Structure**: Trend identification (UPTREND, DOWNTREND, or RANGING)
- **SMC Strategy**: Smart Money Concepts trading strategy
- **MultiTimeframeAnalyzer**: Component that analyzes multiple timeframes and determines HTF bias

## Requirements

### Requirement 1

**User Story:** As a trader, I want the system to place trades when H1 shows a clear trend, so that I can capture trading opportunities even when H4 is ranging.

#### Acceptance Criteria

1. WHEN H1 market structure is UPTREND and H4 market structure is RANGING THEN the system SHALL return BULLISH bias
2. WHEN H1 market structure is DOWNTREND and H4 market structure is RANGING THEN the system SHALL return BEARISH bias
3. WHEN both H4 and H1 market structures are UPTREND THEN the system SHALL return BULLISH bias with higher confidence
4. WHEN both H4 and H1 market structures are DOWNTREND THEN the system SHALL return BEARISH bias with higher confidence
5. WHEN both H4 and H1 market structures are RANGING THEN the system SHALL return NEUTRAL bias

### Requirement 2

**User Story:** As a trader, I want the system to maintain existing behavior when both timeframes agree, so that high-confidence setups are still prioritized.

#### Acceptance Criteria

1. WHEN H4 is UPTREND and H1 is UPTREND THEN the system SHALL return BULLISH bias
2. WHEN H4 is DOWNTREND and H1 is DOWNTREND THEN the system SHALL return BEARISH bias
3. WHEN H4 is UPTREND and H1 is DOWNTREND THEN the system SHALL return BULLISH bias with H4 taking priority
4. WHEN H4 is DOWNTREND and H1 is UPTREND THEN the system SHALL return BEARISH bias with H4 taking priority

### Requirement 3

**User Story:** As a trader, I want the system to log the bias calculation details, so that I can understand why trades are or are not being placed.

#### Acceptance Criteria

1. WHEN the system calculates HTF bias THEN the system SHALL log the H4 trend
2. WHEN the system calculates HTF bias THEN the system SHALL log the H1 trend
3. WHEN the system calculates HTF bias THEN the system SHALL log the resulting bias decision
4. WHEN the system calculates HTF bias THEN the system SHALL log the confidence level if applicable
