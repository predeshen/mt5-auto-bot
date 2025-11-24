# Per-Symbol Progressive Lot Sizing

## What Changed

Your scalper now tracks progressive lot sizing **INDEPENDENTLY PER SYMBOL**!

### Before (Global Tracking):
```
XAUUSD wins → Lot doubles for ALL symbols
GER40 wins → Lot doubles for ALL symbols
XAUUSD loses → Lot resets for ALL symbols ❌
```

**Problem**: One symbol's loss resets the lot size for winning symbols!

### After (Per-Symbol Tracking):
```
XAUUSD wins → XAUUSD lot doubles (0.01 → 0.02 → 0.04)
GER40 wins → GER40 lot doubles (0.1 → 0.2 → 0.4)
XAUUSD loses → Only XAUUSD resets to 0.01 ✅
GER40 continues → Still at 0.4 ✅
```

**Benefit**: Each symbol has its own winning streak!

## How It Works

### Symbol 1: XAUUSD
```
Trade 1: BUY 0.01 lots → WIN (+$5)
Trade 2: BUY 0.02 lots → WIN (+$10)
Trade 3: BUY 0.04 lots → WIN (+$20)
Trade 4: BUY 0.08 lots → LOSS (-$8)
Trade 5: BUY 0.01 lots → Reset, start over
```

### Symbol 2: GER40 (Independent!)
```
Trade 1: SELL 0.1 lots → WIN (+$50)
Trade 2: SELL 0.2 lots → WIN (+$100)
Trade 3: SELL 0.4 lots → WIN (+$200)
Trade 4: SELL 0.8 lots → Still going!
```

**Even if XAUUSD loses, GER40 keeps its streak!**

## Example Scenario

### Simultaneous Trading:

```
Time: 10:00 AM
XAUUSD: 0.01 lots (starting)
GER40: 0.1 lots (starting)

Time: 10:15 AM
XAUUSD: WIN → Next: 0.02 lots
GER40: WIN → Next: 0.2 lots

Time: 10:30 AM
XAUUSD: WIN → Next: 0.04 lots
GER40: WIN → Next: 0.4 lots

Time: 10:45 AM
XAUUSD: LOSS → Next: 0.01 lots (reset)
GER40: WIN → Next: 0.8 lots (continues!)

Time: 11:00 AM
XAUUSD: 0.01 lots (fresh start)
GER40: 0.8 lots (still on streak!)
```

## What You'll See

### Console Output:

```
✅ Position opened: XAUUSD BUY 0.01 lots @ 2000.00
Position closed: XAUUSD @ 2015.00, Profit: 15.00 | XAUUSD Wins: 1, Next lot: 0.02

✅ Position opened: GER40 SELL 0.1 lots @ 23250.00
Position closed: GER40 @ 23230.00, Profit: 200.00 | GER40 Wins: 1, Next lot: 0.2

✅ Position opened: XAUUSD BUY 0.02 lots @ 2005.00
Position closed: XAUUSD @ 2020.00, Profit: 30.00 | XAUUSD Wins: 2, Next lot: 0.04

✅ Position opened: GER40 SELL 0.2 lots @ 23260.00
Position closed: GER40 @ 23240.00, Profit: 400.00 | GER40 Wins: 2, Next lot: 0.4

✅ Position opened: XAUUSD BUY 0.04 lots @ 2010.00
Position closed: XAUUSD @ 2005.00, Profit: -20.00 | XAUUSD Wins: 0, Next lot: 0.01

✅ Position opened: GER40 SELL 0.4 lots @ 23270.00
Position closed: GER40 @ 23250.00, Profit: 800.00 | GER40 Wins: 3, Next lot: 0.8
```

**Notice**: XAUUSD reset to 0.01, but GER40 continues at 0.8!

## Benefits

### 1. Independent Streaks
- Each symbol maintains its own winning streak
- One symbol's loss doesn't affect others
- Better risk distribution

### 2. Maximize Winners
- Hot symbols keep growing
- Cold symbols stay small
- Natural position sizing based on performance

### 3. Better Risk Management
- Losing symbols automatically reduce exposure
- Winning symbols automatically increase exposure
- Self-adjusting to market conditions

## Tracking

The system tracks for each symbol:
- **Multiplier**: Current lot size multiplier (1.0, 2.0, 4.0, 8.0, etc.)
- **Wins**: Consecutive wins for this symbol
- **Losses**: Consecutive losses for this symbol

### Internal State Example:

```python
_symbol_multipliers = {
    'XAUUSD': 4.0,   # 4x base lot (0.01 → 0.04)
    'GER40': 8.0,    # 8x base lot (0.1 → 0.8)
    'US30': 1.0      # Base lot (just started)
}

_symbol_wins = {
    'XAUUSD': 2,     # 2 consecutive wins
    'GER40': 3,      # 3 consecutive wins
    'US30': 0        # No wins yet
}
```

## Configuration

Base lot sizes are set per symbol based on broker requirements:

```python
# In trade_manager.py
self._base_lot_size = 0.01  # Default base

# But adjusted per symbol:
# XAUUSD: 0.01 (min lot)
# GER40: 0.1 (min lot)
# US30: 0.1 (min lot)
```

Progressive multiplier applies to the base:
```
XAUUSD: 0.01 × 4.0 = 0.04 lots
GER40: 0.1 × 4.0 = 0.4 lots
```

## Risk Example

### Scenario: 3 Symbols Trading

```
Account: $1000
Risk per trade: 5%
Max positions: 20

XAUUSD (Hot - 3 wins):
- Current lot: 0.08 (8x base)
- Risk: ~$40 per trade
- Potential profit: $120 per trade

GER40 (Hot - 2 wins):
- Current lot: 0.4 (4x base)
- Risk: ~$40 per trade
- Potential profit: $120 per trade

US30 (Cold - just lost):
- Current lot: 0.1 (1x base)
- Risk: ~$10 per trade
- Potential profit: $30 per trade

Total exposure: $90 (9% of account)
```

**Smart allocation**: More on winners, less on losers!

## Safety Features

### 1. Broker Limits
- Respects symbol min/max lot sizes
- Adjusts to broker's lot step requirements

### 2. Equity-Based Cap
- Won't exceed reasonable position size
- Scales with account growth

### 3. Automatic Reset
- Any loss resets that symbol to base
- Prevents runaway losses

## Comparison

### Global Progressive (Old):
```
Total trades: 10
XAUUSD: 5 wins, 2 losses
GER40: 3 wins, 0 losses

Result: Both reset to base after XAUUSD loss
GER40 streak wasted! ❌
```

### Per-Symbol Progressive (New):
```
Total trades: 10
XAUUSD: 5 wins, 2 losses → Reset to 0.01
GER40: 3 wins, 0 losses → Continue at 0.8

Result: GER40 keeps growing! ✅
```

## Expected Impact

### Before:
- One loss resets everything
- Difficult to build large positions
- Streaks easily broken

### After:
- Each symbol independent
- Hot symbols grow naturally
- Cold symbols stay small
- Better overall profitability

## Tips

1. **Monitor per-symbol performance**
   - Watch which symbols are hot
   - Consider trading more of the winners

2. **Adjust base lots**
   - If a symbol consistently wins, consider higher base
   - If a symbol consistently loses, consider lower base

3. **Set max positions per symbol**
   - Limit exposure to any single symbol
   - Diversify across multiple symbols

4. **Track symbol statistics**
   - Win rate per symbol
   - Average profit per symbol
   - Adjust strategy accordingly

## Summary

Your scalper now has **intelligent per-symbol position sizing**:
- ✅ Each symbol tracks its own winning streak
- ✅ Winners grow independently
- ✅ Losers reset independently
- ✅ Better risk distribution
- ✅ Maximize profitable symbols
- ✅ Minimize losing symbols

**Result**: More consistent growth, better risk management! 🚀
