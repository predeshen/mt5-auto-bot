# Requirements Document - Smart Money Concepts (SMC) Strategy Module

## Introduction

This document specifies requirements for an advanced Smart Money Concepts (SMC) / Inner Circle Trader (ICT) strategy module that identifies Fair Value Gaps (FVG), Order Blocks, Points of Interest (POI), and liquidity zones across multiple timeframes for high-probability trade setups.

## Glossary

- **FVG (Fair Value Gap)**: Price imbalance/gap where price moved quickly leaving an inefficiency
- **POI (Point of Interest)**: Key decision zones including order blocks and breaker blocks
- **Order Block**: Last bullish/bearish candle before significant move in opposite direction
- **Breaker Block**: Failed order block that becomes support/resistance in opposite direction
- **Premium Zone**: Upper 50% of a range (typically bearish area)
- **Discount Zone**: Lower 50% of a range (typically bullish area)
- **Liquidity Sweep**: Price taking out stops above highs or below lows before reversing
- **BOS (Break of Structure)**: Price breaking previous high/low confirming trend
- **CHoCH (Change of Character)**: Market structure shift indicating potential reversal
- **Volume Imbalance (VI)**: Unfilled gap that price tends to revisit
- **Trading Session**: Active market hours when a symbol is available for trading
- **Symbol Mapping**: Broker-specific symbol name resolution for standard instruments

## Requirements

### Requirement 1

**User Story:** As a trader, I want the system to detect Fair Value Gaps on multiple timeframes, so that I can identify key supply and demand imbalances.

#### Acceptance Criteria

1. WHEN analyzing price data, THEN the SMC Module SHALL identify FVGs on H4, H1, M15, and M5 timeframes
2. WHEN an FVG is detected, THEN the SMC Module SHALL calculate the gap's high, low, and 50% equilibrium level
3. WHEN multiple FVGs exist, THEN the SMC Module SHALL track which FVGs are filled and which remain unfilled
4. WHEN FVGs align across timeframes, THEN the SMC Module SHALL flag these as high-priority zones
5. WHEN price enters an FVG zone, THEN the SMC Module SHALL generate a notification

### Requirement 2

**User Story:** As a trader, I want the system to identify Order Blocks and Breaker Blocks, so that I can trade from institutional supply and demand zones.

#### Acceptance Criteria

1. WHEN a significant price move occurs, THEN the SMC Module SHALL identify the last opposite candle as an Order Block
2. WHEN an Order Block is identified, THEN the SMC Module SHALL mark its high, low, and 50% level
3. WHEN an Order Block fails (price breaks through), THEN the SMC Module SHALL convert it to a Breaker Block
4. WHEN a Breaker Block is created, THEN the SMC Module SHALL track it as a potential reversal zone
5. WHEN price returns to an Order Block or Breaker Block, THEN the SMC Module SHALL generate an entry signal

### Requirement 3

**User Story:** As a trader, I want the system to calculate Premium and Discount zones, so that I can enter trades at optimal prices.

#### Acceptance Criteria

1. WHEN analyzing a price range, THEN the SMC Module SHALL calculate the 50% equilibrium level
2. WHEN the 50% level is calculated, THEN the SMC Module SHALL define Premium zone as above 50% and Discount zone as below 50%
3. WHEN price is in Premium zone, THEN the SMC Module SHALL bias towards SELL setups
4. WHEN price is in Discount zone, THEN the SMC Module SHALL bias towards BUY setups
5. WHEN price crosses the 50% level, THEN the SMC Module SHALL update the bias accordingly

### Requirement 4

**User Story:** As a trader, I want the system to detect liquidity sweeps, so that I can identify false breakouts and reversal opportunities.

#### Acceptance Criteria

1. WHEN price approaches recent highs or lows, THEN the SMC Module SHALL monitor for liquidity sweeps
2. WHEN price breaks above a recent high by a small amount, THEN the SMC Module SHALL detect a potential buyside liquidity sweep
3. WHEN price breaks below a recent low by a small amount, THEN the SMC Module SHALL detect a potential sellside liquidity sweep
4. WHEN a liquidity sweep occurs and price reverses, THEN the SMC Module SHALL generate a high-confidence entry signal
5. WHEN multiple liquidity levels are swept, THEN the SMC Module SHALL track the sequence for pattern recognition

### Requirement 5

**User Story:** As a trader, I want the system to identify market structure shifts, so that I can recognize trend changes and continuations.

#### Acceptance Criteria

1. WHEN analyzing price action, THEN the SMC Module SHALL identify higher highs and higher lows for uptrends
2. WHEN analyzing price action, THEN the SMC Module SHALL identify lower highs and lower lows for downtrends
3. WHEN market structure breaks, THEN the SMC Module SHALL detect Break of Structure (BOS)
4. WHEN market structure shifts direction, THEN the SMC Module SHALL detect Change of Character (CHoCH)
5. WHEN a CHoCH occurs, THEN the SMC Module SHALL update the trend bias and look for reversal setups

### Requirement 6

**User Story:** As a trader, I want multi-timeframe confluence analysis, so that I can take only the highest probability setups.

#### Acceptance Criteria

1. WHEN analyzing a potential trade, THEN the SMC Module SHALL check H4 trend direction
2. WHEN H4 trend is established, THEN the SMC Module SHALL verify H1 structure aligns with H4
3. WHEN H1 FVG exists within H4 FVG, THEN the SMC Module SHALL mark this as high-confluence zone
4. WHEN all timeframes align, THEN the SMC Module SHALL generate a high-confidence signal
5. WHEN timeframes conflict, THEN the SMC Module SHALL either skip the trade or reduce position size

### Requirement 7

**User Story:** As a trader, I want the system to detect Volume Imbalances, so that I can anticipate price returning to fill gaps.

#### Acceptance Criteria

1. WHEN analyzing price data, THEN the SMC Module SHALL identify unfilled volume imbalances
2. WHEN a Volume Imbalance is detected, THEN the SMC Module SHALL mark its location and size
3. WHEN price approaches a Volume Imbalance, THEN the SMC Module SHALL anticipate potential fill
4. WHEN a Volume Imbalance is filled, THEN the SMC Module SHALL remove it from active tracking
5. WHEN multiple Volume Imbalances exist, THEN the SMC Module SHALL prioritize the nearest unfilled gaps

### Requirement 8

**User Story:** As a trader, I want the system to generate SMC-based entry signals, so that I can execute trades based on institutional order flow.

#### Acceptance Criteria

1. WHEN all SMC conditions align, THEN the SMC Module SHALL generate an entry signal
2. WHEN generating a signal, THEN the SMC Module SHALL include entry price, stop loss, and take profit levels
3. WHEN calculating stop loss, THEN the SMC Module SHALL place it beyond the invalidation point (opposite side of Order Block)
4. WHEN calculating take profit, THEN the SMC Module SHALL target the next FVG, Order Block, or liquidity level
5. WHEN signal confidence is low, THEN the SMC Module SHALL either skip the trade or suggest reduced position size

### Requirement 9

**User Story:** As a trader, I want the system to integrate SMC signals with the existing scalping strategy, so that I can choose between aggressive scalping and patient SMC setups.

#### Acceptance Criteria

1. WHEN the application starts, THEN the user SHALL be able to select between Momentum Strategy, SMC Strategy, or Hybrid mode
2. WHEN Hybrid mode is selected, THEN the system SHALL use SMC for bias and Momentum for entries
3. WHEN SMC bias is bearish, THEN the Momentum strategy SHALL only take SELL signals
4. WHEN SMC bias is bullish, THEN the Momentum strategy SHALL only take BUY signals
5. WHEN SMC and Momentum signals conflict, THEN the system SHALL prioritize the SMC signal

### Requirement 10

**User Story:** As a trader, I want visual logging of SMC zones and signals, so that I can review and understand the system's analysis.

#### Acceptance Criteria

1. WHEN SMC analysis runs, THEN the system SHALL log all detected FVGs with their levels
2. WHEN Order Blocks are identified, THEN the system SHALL log their locations and types
3. WHEN a signal is generated, THEN the system SHALL log the SMC reasoning (which zones aligned)
4. WHEN displaying status, THEN the system SHALL show current bias (bullish/bearish) and active zones
5. WHEN trades are executed, THEN the system SHALL log which SMC setup triggered the entry

### Requirement 11

**User Story:** As a trader, I want the system to only trade specific high-value symbols, so that I can focus on the most liquid and profitable instruments.

#### Acceptance Criteria

1. WHEN the SMC Module initializes, THEN the system SHALL define a whitelist containing US30, XAUUSD, US30 FT, NASDAQ, and NASDAQ FT
2. WHEN connecting to a broker, THEN the system SHALL map standard symbol names to broker-specific symbol names
3. WHEN a symbol is requested for analysis, THEN the system SHALL verify it exists in the broker's available symbols
4. WHEN a non-whitelisted symbol is encountered, THEN the SMC Module SHALL skip analysis for that symbol
5. WHEN displaying active symbols, THEN the system SHALL show both the standard name and the broker-specific symbol name

### Requirement 12

**User Story:** As a trader, I want the system to only trade during active market hours, so that I avoid low-liquidity periods and reduce slippage.

#### Acceptance Criteria

1. WHEN the SMC Module starts, THEN the system SHALL load trading session schedules for each whitelisted symbol
2. WHEN the current time is checked, THEN the system SHALL determine if each symbol's market is currently open
3. WHEN a symbol's market is closed, THEN the SMC Module SHALL skip signal generation and order placement for that symbol
4. WHEN a symbol's market opens, THEN the SMC Module SHALL resume analysis and trading for that symbol
5. WHEN displaying status, THEN the system SHALL indicate which symbols are currently tradeable based on market hours
