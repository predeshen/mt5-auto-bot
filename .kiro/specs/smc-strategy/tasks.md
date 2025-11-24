# Implementation Plan - SMC Strategy Module

- [x] 1. Set up SMC module structure and data models



  - Create `src/smc_strategy.py` with core SMC strategy class
  - Define data models: FVG, OrderBlock, BreakerBlock, LiquidityLevel, MarketStructure, ConfluenceZone, SMCSignal, PendingOrder
  - Create `src/smc_config.py` for SMC configuration constants
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1_

- [x] 2. Implement FVG Detector


  - Create `FVGDetector` class with detection algorithm for 3-candle patterns
  - Implement `detect_fvgs()` to identify bullish and bearish FVGs
  - Implement `calculate_fvg_equilibrium()` for 50% level calculation
  - Implement `is_fvg_filled()` to track fill status
  - Implement `filter_valid_fvgs()` to remove filled or invalid FVGs
  - _Requirements: 1.1, 1.2, 1.3_
- [x] 2.1 Write property test for FVG equilibrium calculation


  - **Property 2: FVG Level Calculation**
  - **Validates: Requirements 1.2, 3.1**
- [x] 2.2 Write property test for FVG fill status tracking

  - **Property 3: FVG Fill Status Tracking**
  - **Validates: Requirements 1.3**

- [x] 3. Implement Order Block Detector



  - Create `OrderBlockDetector` class
  - Implement `detect_order_blocks()` to find last opposite candle before significant moves
  - Implement `get_order_block_entry()` for 50% level calculation
  - Implement `detect_breaker_blocks()` for failed Order Block conversion
  - Implement `is_order_block_valid()` to check invalidation
  - _Requirements: 2.1, 2.2, 2.3, 2.4_
- [x] 3.1 Write property test for Order Block level calculation


  - **Property 7: Order Block Level Calculation**
  - **Validates: Requirements 2.2**
- [x] 3.2 Write property test for Order Block to Breaker Block conversion

  - **Property 8: Order Block to Breaker Block Conversion**
  - **Validates: Requirements 2.3**

- [x] 4. Implement Market Structure Analyzer


  - Create `MarketStructureAnalyzer` class
  - Implement `identify_structure()` to find swing highs and lows
  - Implement `detect_bos()` for Break of Structure detection
  - Implement `detect_choch()` for Change of Character detection
  - Implement `get_trend_direction()` to determine current trend
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
- [x] 4.1 Write property test for market structure identification


  - **Property 16: Market Structure Identification**
  - **Validates: Requirements 5.1, 5.2**
- [x] 4.2 Write property test for BOS detection

  - **Property 17: Break of Structure Detection**
  - **Validates: Requirements 5.3**

- [x] 5. Implement Liquidity Analyzer



  - Create `LiquidityAnalyzer` class
  - Implement `identify_liquidity_levels()` to find swing highs/lows
  - Implement `detect_sweep()` for liquidity sweep detection
  - Implement `is_buyside_liquidity_swept()` and `is_sellside_liquidity_swept()`
  - Track sweep sequences for pattern recognition
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
- [x] 5.1 Write property test for liquidity sweep detection


  - **Property 13: Liquidity Sweep Detection**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [x] 6. Implement Multi-Timeframe Analyzer


  - Create `MultiTimeframeAnalyzer` class
  - Implement `analyze_all_timeframes()` to coordinate H4, H1, M15, M5 analysis
  - Implement `get_htf_bias()` to determine H4/H1 trend direction
  - Implement `find_confluence_zones()` to identify overlapping FVGs/OBs
  - Implement `check_fvg_alignment()` for timeframe confluence detection
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
- [x] 6.1 Write property test for multi-timeframe FVG detection


  - **Property 1: Multi-timeframe FVG Detection**
  - **Validates: Requirements 1.1**
- [x] 6.2 Write property test for timeframe confluence detection

  - **Property 4: Timeframe Confluence Detection**
  - **Validates: Requirements 1.4, 6.3**

- [x] 7. Implement Premium/Discount Zone Logic



  - Add zone classification methods to `MultiTimeframeAnalyzer`
  - Implement equilibrium calculation for price ranges
  - Implement Premium/Discount zone classification
  - Implement bias determination based on current zone
  - Implement bias update on equilibrium cross
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
- [x] 7.1 Write property test for Premium/Discount zone classification


  - **Property 11: Premium and Discount Zone Classification**
  - **Validates: Requirements 3.2, 3.3, 3.4**

- [x] 8. Implement Pending Order Manager


  - Create `PendingOrderManager` class
  - Implement `place_buy_limit()`, `place_sell_limit()`, `place_buy_stop()`, `place_sell_stop()`
  - Implement `cancel_pending_order()` for order cancellation
  - Implement `get_pending_orders()` to retrieve active pending orders
  - Implement `manage_pending_orders()` to cancel expired/invalid orders
  - Integrate with MT5 API for order placement
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 9. Implement SMC Signal Generator



  - Create `SMCSignalGenerator` class
  - Implement `analyze_setup()` to evaluate all SMC conditions
  - Implement `calculate_entry_price()` based on FVG/OB zones
  - Implement `calculate_stop_loss()` beyond invalidation points
  - Implement `calculate_take_profit()` targeting next zones
  - Implement `get_order_type()` to determine Buy/Sell Limit/Stop
  - Implement `validate_signal()` for confidence scoring
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
- [x] 9.1 Write property test for signal data completeness


  - **Property 30: Signal Data Completeness**
  - **Validates: Requirements 8.2**
- [x] 9.2 Write property test for stop loss placement

  - **Property 31: Stop Loss Placement Beyond Invalidation**
  - **Validates: Requirements 8.3**

- [x] 10. Implement Volume Imbalance Detection


  - Add Volume Imbalance detection to `FVGDetector` or create separate class
  - Implement unfilled gap identification
  - Implement location and size tracking
  - Implement fill anticipation logic
  - Implement removal after fill
  - Implement prioritization by distance to current price
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 11. Implement SMC Logging and Display


  - Add logging methods to all SMC components
  - Implement FVG detection logging with levels
  - Implement Order Block logging with locations and types
  - Implement signal generation logging with reasoning
  - Implement status display showing bias and active zones
  - Implement trade execution logging with setup types
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
- [x] 11.1 Write property test for SMC event logging

  - **Property 38: SMC Event Logging**
  - **Validates: Requirements 10.1, 10.2, 10.3, 10.5**

- [x] 12. Integrate SMC with existing system

  - Create `StrategySelector` class with MOMENTUM, SMC, HYBRID modes
  - Implement strategy selection prompt at application startup
  - Integrate SMC module into `AppController`
  - Add SMC strategy to main trading loop
  - _Requirements: 9.1_

- [x] 13. Implement Hybrid Mode

  - Implement Hybrid mode logic in `StrategySelector`
  - Use SMC for directional bias determination
  - Filter Momentum signals based on SMC bias
  - Implement signal conflict resolution (prioritize SMC)
  - _Requirements: 9.2, 9.3, 9.4, 9.5_
- [x] 13.1 Write property test for Hybrid mode bias filtering

  - **Property 35: Hybrid Mode Bearish Bias Filtering**
  - **Property 36: Hybrid Mode Bullish Bias Filtering**
  - **Validates: Requirements 9.3, 9.4**

- [x] 14. Implement caching and performance optimizations

  - Implement FVG caching with 24-hour expiry
  - Implement Order Block caching until invalidation
  - Implement timeframe data caching (H4/H1: 1 hour, M15: 15 min, M5: 5 min)
  - Implement incremental updates for new candles
  - Add cleanup for expired pending orders and filled FVGs
  - _Requirements: All_

- [x] 15. Add configuration management

  - Create `SMC_CONFIG` dictionary in `smc_config.py`
  - Add configurable parameters: timeframes, min FVG size, Order Block min move, pending order expiry
  - Add max pending orders per symbol, confluence requirements, liquidity sweep threshold
  - Add risk-reward minimum ratio
  - _Requirements: All_

- [x] 16. Checkpoint - Ensure all tests pass


  - Run all unit tests and property-based tests
  - Verify FVG detection, Order Block identification, and signal generation
  - Verify pending order placement and management
  - Verify multi-timeframe analysis and confluence detection
  - Ask the user if questions arise

- [x] 17. Integration testing with MT5

  - Test SMC module with live MT5 connection
  - Test pending order placement on demo account
  - Test multi-timeframe data fetching
  - Test signal generation with real market data
  - Test Hybrid mode with both strategies running
  - _Requirements: All_

- [x] 18. Implement Symbol Filter

  - Create `SymbolFilter` class in `src/smc_strategy.py`
  - Implement `initialize_symbol_mapping()` to discover broker symbols
  - Implement `get_broker_symbol()` to map standard names to broker symbols
  - Implement `is_symbol_whitelisted()` to check whitelist
  - Implement `get_tradeable_symbols()` to return available whitelisted symbols
  - Add symbol variation matching logic (case-insensitive, partial match)
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
- [x] 18.1 Write property test for symbol whitelist enforcement

  - **Property 40: Symbol Whitelist Enforcement**
  - **Validates: Requirements 11.1, 11.4**
- [x] 18.2 Write property test for symbol mapping completeness

  - **Property 41: Symbol Mapping Completeness**
  - **Validates: Requirements 11.2, 11.3**

- [x] 19. Implement Market Hours Manager

  - Create `MarketHoursManager` class in `src/smc_strategy.py`
  - Implement `load_trading_sessions()` to load session schedules from config
  - Implement `is_market_open()` to check if symbol is tradeable at current time
  - Implement `get_next_open_time()` to calculate when market opens
  - Implement `get_tradeable_symbols_now()` to filter by market hours
  - Handle GMT timezone conversions and daily breaks
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
- [x] 19.1 Write property test for market hours filtering

  - **Property 42: Market Hours Filtering**
  - **Validates: Requirements 12.1, 12.2, 12.3**
- [x] 19.2 Write property test for closed market signal suppression

  - **Property 43: Closed Market Signal Suppression**
  - **Validates: Requirements 12.3**

- [x] 20. Integrate Symbol Filter and Market Hours into SMC Strategy

  - Add SymbolFilter initialization to SMC strategy module
  - Add MarketHoursManager initialization to SMC strategy module
  - Filter symbols before analysis using whitelist
  - Check market hours before signal generation
  - Update status display to show tradeable symbols and market status
  - Log symbol mapping results and market hours status
  - _Requirements: 11.1, 11.4, 12.3, 12.5_

- [x] 21. Update configuration with symbol and market hours settings

  - Add whitelisted_symbols to SMC_CONFIG
  - Add symbol_variations dictionary to SMC_CONFIG
  - Add trading_sessions schedule to SMC_CONFIG
  - Document configuration options
  - _Requirements: 11.1, 12.1_

- [x] 22. Checkpoint - Ensure all tests pass

  - Run all unit tests and property-based tests
  - Verify symbol filtering works correctly
  - Verify market hours filtering works correctly
  - Verify integration with existing SMC components
  - Ask the user if questions arise

- [x] 23. Integration testing with MT5

  - Test SMC module with live MT5 connection
  - Test symbol mapping with real broker symbols
  - Test market hours detection with current time
  - Test pending order placement on demo account
  - Test multi-timeframe data fetching
  - Test signal generation with real market data
  - Test Hybrid mode with both strategies running
  - _Requirements: All_

- [x] 24. Create SMC documentation


  - Document FVG detection algorithm
  - Document Order Block identification rules
  - Document multi-timeframe confluence logic
  - Document pending order strategy
  - Document symbol filtering and mapping
  - Document market hours management
  - Add usage examples for each mode (Momentum, SMC, Hybrid)
  - _Requirements: All_
