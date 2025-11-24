# Trading Errors Guide

## Common MT5 Order Errors

### Error: "Order send failed: No result"

This means `mt5.order_send()` returned `None` instead of a result object.

**Common Causes:**

1. **Market is Closed**
   - Symbol's trading session has ended
   - Weekend or holiday
   - Check symbol's trading hours

2. **Symbol Not in Market Watch**
   - Symbol needs to be visible in MT5
   - Solution: Auto-enabled by scalper now

3. **Insufficient Margin**
   - Account doesn't have enough free margin
   - With $23.73, GER40 at 0.1 lots needs ~$23+ margin
   - Solution: Reduce lot size or risk %

4. **Trading Disabled**
   - Broker has disabled trading for this symbol
   - Check symbol properties in MT5

### Your Current Situation

```
Account Equity: $23.73
GER40 Order: 0.1 lots
Estimated Margin: $23-25
Result: INSUFFICIENT MARGIN ❌
```

## Solutions

### Solution 1: Reduce Risk Percentage

Current: 4% risk per trade

```
Change to: 2% or 1%
```

This will calculate smaller lot sizes that fit your margin.

### Solution 2: Trade Only XAUUSD

XAUUSD has lower margin requirements:
- 0.01 lots XAUUSD ≈ $4-5 margin
- You can trade multiple positions

GER40 has higher margin requirements:
- 0.1 lots GER40 ≈ $23-25 margin
- You can barely afford 1 position

### Solution 3: Deposit More Funds

With $23.73, you're very limited:
- Can't trade GER40 effectively
- Can only trade tiny XAUUSD positions

Recommended minimum:
- $100 for comfortable scalping
- $500 for multiple positions
- $1000+ for proper diversification

### Solution 4: Adjust Symbol Selection

In `src/app_controller.py`, change forced symbols:

```python
# Current (includes GER40):
forced_symbols = ["XAUUSD", "US30.F", "USA30", "USA100", "US100.F", "GER40", "GER40.F"]

# Change to (XAUUSD only):
forced_symbols = ["XAUUSD"]
```

## Margin Requirements by Symbol

Approximate margin per 0.01 lots (varies by broker):

| Symbol | Margin per 0.01 lots | Your Account ($23.73) |
|--------|---------------------|----------------------|
| XAUUSD | $4-5 | ✅ Can trade 4-5 positions |
| EURUSD | $1-2 | ✅ Can trade 10+ positions |
| GBPUSD | $1-2 | ✅ Can trade 10+ positions |
| US30 | $20-25 | ⚠️  Can trade 1 position |
| GER40 | $23-25 | ❌ Can barely afford 1 |
| BTCUSD | $50-100 | ❌ Cannot trade |

## Recommended Settings for $23.73 Account

### Option A: Conservative (XAUUSD Only)
```
Maximum Open Positions: 3
Risk per Trade: 2%
Symbols: XAUUSD only
Progressive Sizing: Yes

Expected lot sizes:
- Trade 1: 0.01 lots ($4 margin)
- Trade 2: 0.01 lots ($4 margin)
- Trade 3: 0.01 lots ($4 margin)
Total: $12 margin used
```

### Option B: Aggressive (XAUUSD Only)
```
Maximum Open Positions: 5
Risk per Trade: 3%
Symbols: XAUUSD only
Progressive Sizing: Yes

Expected lot sizes:
- Trade 1: 0.01 lots
- Trade 2: 0.02 lots (after win)
- Trade 3: 0.04 lots (after 2 wins)
- Trade 4: 0.01 lots
- Trade 5: 0.01 lots
```

## How to Fix Right Now

### Quick Fix 1: Lower Risk %

When prompted:
```
Risk Percentage per Trade (%): 1
```

This will calculate smaller lot sizes.

### Quick Fix 2: Edit app_controller.py

Change line ~160:
```python
# OLD:
forced_symbols = ["XAUUSD", "US30.F", "USA30", "USA100", "US100.F", "GER40", "GER40.F"]

# NEW:
forced_symbols = ["XAUUSD"]  # Only trade XAUUSD with small account
```

### Quick Fix 3: Increase Account Balance

Deposit more funds to your demo account:
1. Open MT5 terminal
2. Right-click on account
3. Select "Deposit"
4. Add $100-500 for comfortable trading

## Error Messages Explained

### "⚠️  Insufficient margin"
- You don't have enough free margin
- Reduce lot size or risk %
- Or deposit more funds

### "⚠️  Market is closed"
- Symbol's trading session has ended
- Wait for market to open
- Check trading hours

### "⚠️  Symbol not visible in Market Watch"
- Symbol needs to be added to MT5
- Scalper will try to auto-enable
- Or add manually in MT5

### "⚠️  Trading is disabled"
- Broker has disabled trading for this symbol
- Choose different symbol
- Or contact broker

## Checking Margin Requirements

Run this in Python:
```python
import MetaTrader5 as mt5

mt5.initialize()
mt5.login(11324457, "your_password", "VantageInternational-Demo")

# Check margin for GER40
margin = mt5.order_calc_margin(
    mt5.ORDER_TYPE_SELL,
    "GER40",
    0.1,  # lot size
    23250  # price
)

print(f"GER40 0.1 lots requires: ${margin:.2f} margin")

# Check margin for XAUUSD
margin = mt5.order_calc_margin(
    mt5.ORDER_TYPE_BUY,
    "XAUUSD",
    0.01,  # lot size
    2000  # price
)

print(f"XAUUSD 0.01 lots requires: ${margin:.2f} margin")

mt5.shutdown()
```

## Summary

Your $23.73 account is too small for GER40 trading:
- GER40 minimum lot (0.1) requires ~$23-25 margin
- You can barely afford 1 position
- No room for progressive sizing

**Recommended Actions:**
1. ✅ Trade XAUUSD only (lower margin)
2. ✅ Reduce risk % to 1-2%
3. ✅ Deposit more funds ($100+)
4. ✅ Or use a larger demo account

**Quick Fix:**
```bash
# Edit app_controller.py line ~160:
forced_symbols = ["XAUUSD"]  # Remove GER40

# Or when prompted:
Risk Percentage per Trade (%): 1  # Lower risk
```

This will allow you to trade successfully with your current balance!
