"""Scalping Strategy for generating entry and exit signals."""

import MetaTrader5 as mt5
from typing import Optional, List
from datetime import datetime, timedelta
from src.models import Signal, Position


class ScalpingStrategy:
    """Implements scalping trading logic using RSI and volatility breakout."""
    
    def __init__(self):
        self.rsi_period = 14
        self.rsi_oversold = 40  # More aggressive - was 30
        self.rsi_overbought = 60  # More aggressive - was 70
        self.atr_period = 20
        self.profit_target_multiplier = 2.0  # Increased from 1.5 for better R:R
        self.stop_loss_multiplier = 1.5  # Increased from 1.0 to give more room
        self.trailing_stop_enabled = True
        self.momentum_period = 10  # For momentum calculation
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index.
        
        Args:
            prices: List of closing prices
            period: RSI period
            
        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Calculate average gain and loss
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_atr(self, candles: List[dict], period: int = 20) -> float:
        """
        Calculate Average True Range.
        
        Args:
            candles: List of OHLC candles
            period: ATR period
            
        Returns:
            ATR value
        """
        if len(candles) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_close = candles[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / min(period, len(true_ranges))
    
    def calculate_momentum(self, prices: List[float], period: int = 10) -> float:
        """
        Calculate price momentum (rate of change).
        
        Args:
            prices: List of closing prices
            period: Lookback period
            
        Returns:
            Momentum value (positive = uptrend, negative = downtrend)
        """
        if len(prices) < period + 1:
            return 0.0
        
        current = prices[-1]
        past = prices[-period]
        
        return (current - past) / past * 100  # Percentage change
    
    def analyze_entry(self, symbol: str, candles: List[dict]) -> Optional[Signal]:
        """
        Analyze market conditions for entry signal using momentum + RSI.
        
        Args:
            symbol: Trading symbol
            candles: Recent OHLC candles
            
        Returns:
            Signal object if conditions met, None otherwise
        """
        if len(candles) < 30:
            return None
        
        # Extract closing prices
        closes = [c['close'] for c in candles]
        
        # Calculate indicators
        rsi = self.calculate_rsi(closes, self.rsi_period)
        atr = self.calculate_atr(candles, self.atr_period)
        momentum = self.calculate_momentum(closes, self.momentum_period)
        current_price = candles[-1]['close']
        prev_price = candles[-2]['close']
        
        # Check for sufficient volatility - be more selective
        if atr / current_price < 0.0008:  # Increased to filter low volatility
            return None
        
        # Check for trending market (avoid choppy/ranging markets)
        # Calculate if price is trending by checking recent highs/lows
        recent_highs = [c['high'] for c in candles[-10:]]
        recent_lows = [c['low'] for c in candles[-10:]]
        price_range = max(recent_highs) - min(recent_lows)
        avg_price = sum(closes[-10:]) / 10
        
        # If range is too small relative to price, market is choppy
        if price_range / avg_price < 0.003:  # Less than 0.3% range = choppy
            return None
        
        # Calculate average volume
        if 'tick_volume' in candles[-1]:
            avg_volume = sum([c.get('tick_volume', 0) for c in candles[-20:]]) / 20
            current_volume = candles[-1].get('tick_volume', 0)
            volume_confirmed = current_volume > avg_volume * 0.8  # Relaxed from 1.0
        else:
            volume_confirmed = True
        
        # MOMENTUM-BASED BUY: Strong upward momentum + RSI confirmation + volume
        if (momentum > 0.15 and  # Stronger momentum required (was 0.05)
            rsi > 45 and rsi < 70 and  # RSI in favorable range
            current_price > prev_price and  # Price rising
            current_price > closes[-3] and  # Confirm uptrend (3 candles)
            volume_confirmed):
            
            return Signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr * self.stop_loss_multiplier),
                take_profit=current_price + (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=0.80,
                reason="MOMENTUM_BUY"
            )
        
        # MOMENTUM-BASED SELL: Strong downward momentum + RSI confirmation + volume
        if (momentum < -0.15 and  # Stronger momentum required (was -0.05)
            rsi < 55 and rsi > 30 and  # RSI in favorable range
            current_price < prev_price and  # Price falling
            current_price < closes[-3] and  # Confirm downtrend (3 candles)
            volume_confirmed):
            
            return Signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr * self.stop_loss_multiplier),
                take_profit=current_price - (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=0.80,
                reason="MOMENTUM_SELL"
            )
        
        # No reversal signals - only trade with momentum in trending markets
        return None
    
    def analyze_exit(self, position: Position, current_price: float) -> Optional[Signal]:
        """
        Analyze if position should be closed.
        
        Args:
            position: Open position
            current_price: Current market price
            
        Returns:
            Exit signal if conditions met, None otherwise
        """
        # Check take profit
        if position.direction == "BUY":
            if current_price >= position.take_profit:
                return Signal(
                    symbol=position.symbol,
                    direction="SELL",
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    timestamp=datetime.now(),
                    confidence=1.0,
                    reason="TAKE_PROFIT"
                )
            
            # Check stop loss
            if current_price <= position.stop_loss:
                return Signal(
                    symbol=position.symbol,
                    direction="SELL",
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    timestamp=datetime.now(),
                    confidence=1.0,
                    reason="STOP_LOSS"
                )
        
        elif position.direction == "SELL":
            if current_price <= position.take_profit:
                return Signal(
                    symbol=position.symbol,
                    direction="BUY",
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    timestamp=datetime.now(),
                    confidence=1.0,
                    reason="TAKE_PROFIT"
                )
            
            if current_price >= position.stop_loss:
                return Signal(
                    symbol=position.symbol,
                    direction="BUY",
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    timestamp=datetime.now(),
                    confidence=1.0,
                    reason="STOP_LOSS"
                )
        
        # Implement trailing stop if enabled
        if self.trailing_stop_enabled:
            # Calculate profit in pips/points
            if position.direction == "BUY":
                profit_distance = current_price - position.entry_price
                # If in profit by at least 1x ATR, trail stop to breakeven + 50%
                atr_estimate = abs(position.take_profit - position.entry_price) / self.profit_target_multiplier
                if profit_distance >= atr_estimate:
                    # Move stop to breakeven + 50% of profit
                    new_stop = position.entry_price + (profit_distance * 0.5)
                    if new_stop > position.stop_loss:
                        # Update position stop loss (this would need to be done via MT5)
                        pass  # Trailing stop logic - position.stop_loss would be updated
            
            elif position.direction == "SELL":
                profit_distance = position.entry_price - current_price
                atr_estimate = abs(position.entry_price - position.take_profit) / self.profit_target_multiplier
                if profit_distance >= atr_estimate:
                    new_stop = position.entry_price - (profit_distance * 0.5)
                    if new_stop < position.stop_loss:
                        pass  # Trailing stop logic
        
        # Check time-based exit (30 minutes for scalping) - only if NOT in profit
        time_open = (datetime.now() - position.open_time).total_seconds() / 60
        if time_open >= 30:
            # Check if position is in profit
            is_profitable = False
            if position.direction == "BUY":
                is_profitable = current_price > position.entry_price
            else:
                is_profitable = current_price < position.entry_price
            
            # Only close on time if not profitable or very small profit
            if not is_profitable or abs(position.profit) < 1.0:
                exit_direction = "SELL" if position.direction == "BUY" else "BUY"
                return Signal(
                    symbol=position.symbol,
                    direction=exit_direction,
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    timestamp=datetime.now(),
                    confidence=0.5,
                    reason="TIME_EXIT"
                )
        
        return None
    
    def calculate_position_size(self, symbol: str, equity: float, risk_percent: float, 
                               entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size based on risk parameters using actual symbol specifications.
        
        Args:
            symbol: Trading symbol
            equity: Account equity
            risk_percent: Percentage of equity to risk
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size (lots)
        """
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.01  # Minimum lot size
        
        # Calculate risk amount
        risk_amount = equity * (risk_percent / 100)
        
        # Calculate stop loss distance in price
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return 0.01
        
        # Get contract size (for forex it's typically 100,000, for crypto varies)
        contract_size = symbol_info.trade_contract_size
        
        # Calculate lot size based on risk
        # Risk = Lot Size × Contract Size × Price Distance
        lot_size = risk_amount / (sl_distance * contract_size)
        
        # Apply symbol constraints
        min_lot = symbol_info.volume_min
        max_lot = symbol_info.volume_max
        lot_step = symbol_info.volume_step
        
        # Ensure lot size is at least minimum
        lot_size = max(min_lot, lot_size)
        
        # Round to valid lot step
        if lot_step > 0:
            lot_size = round(lot_size / lot_step) * lot_step
        
        # Ensure we're still above minimum after rounding
        if lot_size < min_lot:
            lot_size = min_lot
        
        # Cap at maximum
        lot_size = min(max_lot, lot_size)
        
        # Additional safety cap based on equity (very generous for growth)
        # Allow up to 20% of equity per 1% price move
        max_reasonable_lot = min(max_lot, equity / 20)
        lot_size = min(lot_size, max_reasonable_lot)
        
        # Final validation - ensure it's a valid number
        if lot_size <= 0 or lot_size < min_lot:
            return min_lot
        
        return lot_size
    
    def set_parameters(self, profit_target_multiplier: float = None,
                      stop_loss_multiplier: float = None,
                      trailing_stop_enabled: bool = None):
        """
        Update strategy parameters.
        
        Args:
            profit_target_multiplier: Multiplier for take profit
            stop_loss_multiplier: Multiplier for stop loss
            trailing_stop_enabled: Enable/disable trailing stop
        """
        if profit_target_multiplier is not None:
            self.profit_target_multiplier = profit_target_multiplier
        if stop_loss_multiplier is not None:
            self.stop_loss_multiplier = stop_loss_multiplier
        if trailing_stop_enabled is not None:
            self.trailing_stop_enabled = trailing_stop_enabled
