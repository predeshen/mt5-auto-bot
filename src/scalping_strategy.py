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
        self.profit_target_multiplier = 1.5
        self.stop_loss_multiplier = 1.0
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
        
        # Check for sufficient volatility
        if atr / current_price < 0.0005:  # Relaxed from 0.001
            return None
        
        # Calculate average volume
        if 'tick_volume' in candles[-1]:
            avg_volume = sum([c.get('tick_volume', 0) for c in candles[-20:]]) / 20
            current_volume = candles[-1].get('tick_volume', 0)
            volume_confirmed = current_volume > avg_volume * 0.8  # Relaxed from 1.0
        else:
            volume_confirmed = True
        
        # MOMENTUM-BASED BUY: Upward momentum + RSI rising + price rising
        if (momentum > 0.05 and  # Positive momentum (relaxed for scalping)
            rsi > 40 and rsi < 75 and  # RSI in middle-upper range
            current_price > prev_price and  # Price rising
            volume_confirmed):
            
            return Signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr * self.stop_loss_multiplier),
                take_profit=current_price + (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=0.75,
                reason="MOMENTUM_BUY"
            )
        
        # MOMENTUM-BASED SELL: Downward momentum + RSI falling + price falling
        if (momentum < -0.05 and  # Negative momentum (relaxed for scalping)
            rsi < 60 and rsi > 25 and  # RSI in middle-lower range
            current_price < prev_price and  # Price falling
            volume_confirmed):
            
            return Signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr * self.stop_loss_multiplier),
                take_profit=current_price - (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=0.75,
                reason="MOMENTUM_SELL"
            )
        
        # REVERSAL BUY: Oversold bounce (keep for extreme conditions)
        if (rsi < self.rsi_oversold and 
            current_price > prev_price and  # Starting to bounce
            volume_confirmed):
            
            return Signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr * self.stop_loss_multiplier),
                take_profit=current_price + (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=0.65,
                reason="REVERSAL_BUY"
            )
        
        # REVERSAL SELL: Overbought reversal (keep for extreme conditions)
        if (rsi > self.rsi_overbought and
            current_price < prev_price and  # Starting to fall
            volume_confirmed):
            
            return Signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr * self.stop_loss_multiplier),
                take_profit=current_price - (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=0.65,
                reason="REVERSAL_SELL"
            )
        
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
        
        # Check time-based exit (5 minutes for scalping)
        time_open = (datetime.now() - position.open_time).total_seconds() / 60
        if time_open >= 5:
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
