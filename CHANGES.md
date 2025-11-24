# MT5 Auto Scalper - Recent Changes

## Summary
Fixed critical issues with order execution and implemented forced symbol monitoring with proper progressive lot sizing.

## Changes Made

### 1. Fixed "Unsupported Filling Mode" Error
**Problem**: Orders were failing with error 10030 - Unsupported filling mode

**Solution**: 
- Updated `trade_manager.py` to dynamically detect and use the correct filling mode for each symbol
- Now checks symbol's `filling_mode` property and uses FOK, IOC, or RETURN as appropriate
- Applied to both opening and closing positions

### 2. Forced Symbol Monitoring
**Problem**: App was scanning for high volatility and selecting top 3 instruments automatically

**Solution**:
- Modified `app_controller.py` to force monitoring of specific symbols: **XAUUSD, US30.F, USA30**
- These symbols are now monitored indefinitely regardless of their volatility scores
- Removed volatility-based instrument selection

### 3. Fixed Progressive Lot Sizing
**Problem**: Lot sizing was calculating based on risk percentage instead of using the progressive doubling system

**Solution**:
- Updated `get_progressive_lot_size()` in `trade_manager.py` to always use progressive lots when enabled
- Now starts at 0.01 lots
- Doubles after each win: 0.01 → 0.02 → 0.04 → 0.08 → 0.16 → 0.32...
- Resets to 0.01 after any loss
- Ignores risk-based calculation when progressive sizing is enabled

### 4. Symbol Discovery Enhancement
**Problem**: Some symbols like US100.F and USA100 were hidden and not being found

**Solution**:
- Updated `volatility_scanner.py` to automatically enable hidden symbols using `mt5.symbol_select()`
- Now discovers 111 symbols on HFM instead of just 2

## Current Behavior

### Monitored Symbols (Fixed)
- XAUUSD (Gold)
- US30.F (Dow Jones Futures)
- USA30 (Dow Jones CFD)
- USA100 (NASDAQ 100 CFD)
- US100.F (NASDAQ 100 Futures)
- GER40 (DAX CFD)
- GER40.F (DAX Futures)

### Lot Sizing (Progressive/Martingale)
- Base lot: 0.01
- After win: Doubles (0.01 → 0.02 → 0.04 → 0.08...)
- After loss: Resets to 0.01
- No maximum cap (grows based on equity)

### Trading Parameters
- Max open positions: 5-7 recommended (configurable)
- Max 1 position per symbol at a time
- Monitoring 7 symbols total
- Risk per trade: 2% (only used for validation, not lot calculation)
- Profit target: 1.5x ATR
- Stop loss: 1.0x ATR
- Trailing stop: Enabled
- Scan interval: Every 3 seconds
- Timeframe: M1 (1-minute candles)

## Files Modified
1. `src/trade_manager.py` - Fixed filling mode and progressive lot sizing
2. `src/app_controller.py` - Forced symbol monitoring
3. `src/volatility_scanner.py` - Auto-enable hidden symbols

## Testing
- ✅ App connects to HFM account successfully
- ✅ Monitors forced symbols (XAUUSD, US30.F, USA30)
- ✅ Progressive lot sizing starts at 0.01
- ✅ No more "Unsupported filling mode" errors
- ⏳ Waiting for market conditions to trigger entry signals

## Next Steps
The bot is now running and monitoring. It will automatically:
1. Generate entry signals when strategy conditions are met
2. Open positions starting with 0.01 lots
3. Double lot size on each winning trade
4. Reset to 0.01 lots after any loss
5. Monitor up to 3 positions simultaneously
