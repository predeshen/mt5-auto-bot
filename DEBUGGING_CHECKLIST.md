# Debugging Checklist - Why No Winning Trades?

## Step 1: Are Signals Being Generated?

Look for these in your logs:
```
Entry signal: ETHUSD BUY - MOMENTUM_BUY
Entry signal: XAUUSD SELL - RSI_OVERBOUGHT_REVERSAL
```

✅ **If YES**: Strategy is working, move to Step 2
❌ **If NO**: Market conditions too calm, try different symbols or timeframes

## Step 2: Are Lot Sizes Being Calculated?

Look for:
```
Calculated lot size: 0.01 for ETHUSD
```

✅ **If YES**: Position sizing working, move to Step 3
❌ **If NO**: Check account equity and risk percentage

## Step 3: Are Positions Actually Opening?

Look for:
```
✅ Position opened: ETHUSD BUY 0.01 lots @ 3500.00
```

✅ **If YES**: Trades are executing! Move to Step 4
❌ **If NO**: This is the problem! Check for error messages:

### Common Errors:

**"not enough money"**
- Your account doesn't have enough margin
- Solution: Reduce risk % or lot size

**"invalid stops"**
- Stop loss too close to entry price
- Solution: Broker requires minimum stop distance (e.g., 10 pips)
- Fix: Increase `stop_loss_multiplier` in strategy

**"trade is disabled"**
- Symbol not available for trading
- Solution: Check broker's tradeable symbols

**"market is closed"**
- Trading outside market hours
- Solution: Trade during active sessions

**"invalid volume"**
- Lot size doesn't meet broker requirements
- Solution: Check symbol's min/max/step volume

## Step 4: Are Positions Closing?

Look for:
```
💰 Position closed: ETHUSD @ 3515.00, Profit: 15.00
Exit signal for ETHUSD: TAKE_PROFIT
Exit signal for ETHUSD: STOP_LOSS
```

✅ **If YES**: Full cycle working!
❌ **If NO**: Positions stuck open

## Step 5: Win Rate Analysis

After 10+ trades, calculate:
```
Win Rate = Wins / Total Trades
```

With 3:1 R:R, you need:
- **25% win rate** to break even
- **30% win rate** for small profit
- **40% win rate** for good profit

## Your Previous Logs Showed:

❌ **Problem**: Signals generated but NO positions opened
- Saw: "Entry signal: ETHUSD BUY - MOMENTUM_BUY"
- Saw: "Calculated lot size: 0.31 for ETHUSD"
- **Missing**: "✅ Position opened" messages

❌ **Problem**: Exit signals firing with no open positions
- Saw: "Exit signal for ETHUSD: STOP_LOSS" (repeated)
- But no corresponding open position

## What I Fixed:

1. **Added logging** to see WHY positions aren't opening
2. **Relaxed strategy** to generate more valid signals
3. **Improved R:R** to 3:1 for better profitability

## Next Run - What to Check:

1. **Start the scalper**
2. **Wait for first signal**: "Entry signal: SYMBOL DIRECTION - REASON"
3. **Check for opening attempt**: "Opening position: SYMBOL DIRECTION X lots"
4. **Look for result**:
   - ✅ Success: "Position opened"
   - ❌ Failure: Error message with reason

## If Still No Trades Opening:

Share these from your logs:
```
1. Entry signal line
2. Calculated lot size line
3. Any error messages
4. Your broker name
5. Symbol being traded
```

## Quick Test:

Run this to see if MT5 connection works:
```python
import MetaTrader5 as mt5
mt5.initialize()
print(mt5.account_info())
print(mt5.symbol_info("EURUSD"))
mt5.shutdown()
```

If this fails, MT5 connection is the issue.

## Emergency Fix:

If you need trades NOW, make strategy even more relaxed:

In `src/scalping_strategy.py`, change:
```python
if (momentum > 0.08 and  # Change to 0.05
    rsi > 40 and rsi < 75 and
    current_price > prev_price and
    volume_confirmed):
```

This will generate MANY more signals (maybe too many).
