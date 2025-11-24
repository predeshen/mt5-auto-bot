"""Scalping Strategy for generating entry and exit signals."""

import MetaTrader5 as mt5
from typing import Optional, List
from datetime import datetime, timedelta
from src.models import Signal, Position


class ScalpingStrategy:
    """Implements scalping trading logic using RSI and volatility breakout."""
    
    def __init__(self):
        # RSI settings - dual periods for confirmation
        self.rsi_period_fast = 9  # Fast RSI for quick signals
        self.rsi_period_slow = 14  # Slow RSI for confirmation
        self.rsi_oversold = 40
        self.rsi_overbought = 60
        
        # Momentum settings - dual periods for confirmation
        self.momentum_period_fast = 15  # Fast momentum
        self.momentum_period_slow = 18  # Slow momentum
        
        # ADX settings for trend strength
        self.adx_period = 14
        self.adx_threshold = 20  # Minimum ADX to confirm trend (20-25 = weak, 25-50 = strong, 50+ = very strong)
        
        # ATR and risk settings
        self.atr_period = 20
        self.profit_target_multiplier = 3.0
        self.stop_loss_multiplier = 1.0
        self.trailing_stop_enabled = True
    
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
    
    def calculate_adx(self, candles: List[dict], period: int = 14) -> tuple:
        """
        Calculate Average Directional Index (ADX) and directional indicators.
        
        Args:
            candles: List of OHLC candles
            period: ADX period
            
        Returns:
            Tuple of (ADX, +DI, -DI) values
        """
        if len(candles) < period + 1:
            return 0.0, 0.0, 0.0
        
        # Calculate True Range and Directional Movement
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(candles)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_high = candles[i-1]['high']
            prev_low = candles[i-1]['low']
            prev_close = candles[i-1]['close']
            
            # True Range
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(tr)
            
            # Directional Movement
            plus_dm = high - prev_high
            minus_dm = prev_low - low
            
            # Only count if movement is significant
            if plus_dm > minus_dm and plus_dm > 0:
                plus_dm_list.append(plus_dm)
                minus_dm_list.append(0)
            elif minus_dm > plus_dm and minus_dm > 0:
                plus_dm_list.append(0)
                minus_dm_list.append(minus_dm)
            else:
                plus_dm_list.append(0)
                minus_dm_list.append(0)
        
        if len(tr_list) < period:
            return 0.0, 0.0, 0.0
        
        # Smooth the values
        atr = sum(tr_list[-period:]) / period
        plus_dm_smooth = sum(plus_dm_list[-period:]) / period
        minus_dm_smooth = sum(minus_dm_list[-period:]) / period
        
        if atr == 0:
            return 0.0, 0.0, 0.0
        
        # Calculate Directional Indicators
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)
        
        # Calculate DX and ADX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0.0, plus_di, minus_di
        
        dx = 100 * abs(plus_di - minus_di) / di_sum
        
        # ADX is smoothed DX (simplified - using last period average)
        adx = dx  # In a full implementation, this would be smoothed over multiple periods
        
        return adx, plus_di, minus_di
    
    def analyze_entry(self, symbol: str, candles: List[dict]) -> Optional[Signal]:
        """
        Analyze market conditions for entry signal using multiple indicators.
        Uses: Dual RSI (9 & 14), Dual Momentum (15 & 18), ADX for trend strength.
        
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
        
        # Calculate ALL indicators
        rsi_fast = self.calculate_rsi(closes, self.rsi_period_fast)  # RSI 9
        rsi_slow = self.calculate_rsi(closes, self.rsi_period_slow)  # RSI 14
        momentum_fast = self.calculate_momentum(closes, self.momentum_period_fast)  # Momentum 15
        momentum_slow = self.calculate_momentum(closes, self.momentum_period_slow)  # Momentum 18
        adx, plus_di, minus_di = self.calculate_adx(candles, self.adx_period)  # ADX 14
        atr = self.calculate_atr(candles, self.atr_period)
        current_price = candles[-1]['close']
        prev_price = candles[-2]['close']
        
        # Check for sufficient volatility - VERY RELAXED
        if atr / current_price < 0.0001:  # Very low threshold to allow most instruments
            return None
        
        # Check for trending market - VERY RELAXED
        recent_highs = [c['high'] for c in candles[-10:]]
        recent_lows = [c['low'] for c in candles[-10:]]
        price_range = max(recent_highs) - min(recent_lows)
        avg_price = sum(closes[-10:]) / 10
        
        # If range is too small relative to price, market is choppy - VERY RELAXED
        if price_range / avg_price < 0.0005:  # Very low threshold
            return None
        
        # Calculate average volume
        if 'tick_volume' in candles[-1]:
            avg_volume = sum([c.get('tick_volume', 0) for c in candles[-20:]]) / 20
            current_volume = candles[-1].get('tick_volume', 0)
            volume_confirmed = current_volume > avg_volume * 0.5
        else:
            volume_confirmed = True
        
        # === STRONG TREND BUY SIGNAL ===
        # All indicators aligned for strong uptrend
        if (adx > self.adx_threshold and  # Trend is strong enough
            plus_di > minus_di and  # Bullish directional movement
            momentum_fast > 0.05 and  # Fast momentum positive (relaxed from 0.08)
            momentum_slow > 0.03 and  # Slow momentum confirms (relaxed from 0.05)
            rsi_fast > 35 and rsi_fast < 80 and  # Fast RSI in range (wider)
            rsi_slow > 35 and rsi_slow < 80 and  # Slow RSI confirms (wider)
            current_price > prev_price and  # Price rising
            volume_confirmed):
            
            # Calculate confidence based on indicator alignment
            confidence = 0.85  # High confidence - all indicators aligned
            if adx > 30:  # Very strong trend
                confidence = 0.90
            
            return Signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr * self.stop_loss_multiplier),
                take_profit=current_price + (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=confidence,
                reason=f"STRONG_TREND_BUY (ADX:{adx:.1f}, RSI9:{rsi_fast:.0f}, RSI14:{rsi_slow:.0f})"
            )
        
        # === STRONG TREND SELL SIGNAL ===
        # All indicators aligned for strong downtrend
        if (adx > self.adx_threshold and  # Trend is strong enough
            minus_di > plus_di and  # Bearish directional movement
            momentum_fast < -0.05 and  # Fast momentum negative (relaxed from -0.08)
            momentum_slow < -0.03 and  # Slow momentum confirms (relaxed from -0.05)
            rsi_fast < 65 and rsi_fast > 20 and  # Fast RSI in range (wider)
            rsi_slow < 65 and rsi_slow > 20 and  # Slow RSI confirms (wider)
            current_price < prev_price and  # Price falling
            volume_confirmed):
            
            # Calculate confidence based on indicator alignment
            confidence = 0.85  # High confidence - all indicators aligned
            if adx > 30:  # Very strong trend
                confidence = 0.90
            
            return Signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr * self.stop_loss_multiplier),
                take_profit=current_price - (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=confidence,
                reason=f"STRONG_TREND_SELL (ADX:{adx:.1f}, RSI9:{rsi_fast:.0f}, RSI14:{rsi_slow:.0f})"
            )
        
        # === MODERATE MOMENTUM BUY ===
        # Relaxed conditions when ADX is lower (ranging/weak trend)
        if (momentum_fast > 0.05 and  # Fast momentum positive (relaxed from 0.08)
            (momentum_slow > 0.02 or adx < 20) and  # Slow momentum OR weak trend
            rsi_fast > 30 and rsi_fast < 85 and  # Fast RSI in range (wider)
            current_price > prev_price and  # Price rising
            volume_confirmed):
            
            confidence = 0.70
            if rsi_fast > 40 and rsi_slow > 40:  # Both RSI confirm
                confidence = 0.75
            
            return Signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr * self.stop_loss_multiplier),
                take_profit=current_price + (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=confidence,
                reason=f"MOMENTUM_BUY (M15:{momentum_fast:.2f}, M18:{momentum_slow:.2f})"
            )
        
        # === MODERATE MOMENTUM SELL ===
        # Relaxed conditions when ADX is lower (ranging/weak trend)
        if (momentum_fast < -0.05 and  # Fast momentum negative (relaxed from -0.08)
            (momentum_slow < -0.02 or adx < 20) and  # Slow momentum OR weak trend
            rsi_fast < 70 and rsi_fast > 15 and  # Fast RSI in range (wider)
            current_price < prev_price and  # Price falling
            volume_confirmed):
            
            confidence = 0.70
            if rsi_fast < 60 and rsi_slow < 60:  # Both RSI confirm
                confidence = 0.75
            
            return Signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr * self.stop_loss_multiplier),
                take_profit=current_price - (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=confidence,
                reason=f"MOMENTUM_SELL (M15:{momentum_fast:.2f}, M18:{momentum_slow:.2f})"
            )
        
        # === RSI DIVERGENCE/REVERSAL TRADES ===
        # Oversold bounce with confirmation
        if (rsi_fast < 30 and  # Fast RSI oversold
            rsi_slow < 35 and  # Slow RSI confirms oversold
            current_price > prev_price and  # Starting to bounce
            momentum_fast > -0.05 and  # Fast momentum turning positive
            adx < 40):  # Not in strong downtrend (avoid catching falling knife)
            
            confidence = 0.65
            if momentum_slow > -0.03:  # Slow momentum also turning
                confidence = 0.70
            
            return Signal(
                symbol=symbol,
                direction="BUY",
                entry_price=current_price,
                stop_loss=current_price - (atr * self.stop_loss_multiplier),
                take_profit=current_price + (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=confidence,
                reason=f"RSI_OVERSOLD_BOUNCE (RSI9:{rsi_fast:.0f}, RSI14:{rsi_slow:.0f})"
            )
        
        # Overbought reversal with confirmation
        if (rsi_fast > 70 and  # Fast RSI overbought
            rsi_slow > 65 and  # Slow RSI confirms overbought
            current_price < prev_price and  # Starting to reverse
            momentum_fast < 0.05 and  # Fast momentum turning negative
            adx < 40):  # Not in strong uptrend (avoid fighting trend)
            
            confidence = 0.65
            if momentum_slow < 0.03:  # Slow momentum also turning
                confidence = 0.70
            
            return Signal(
                symbol=symbol,
                direction="SELL",
                entry_price=current_price,
                stop_loss=current_price + (atr * self.stop_loss_multiplier),
                take_profit=current_price - (atr * self.profit_target_multiplier),
                timestamp=datetime.now(),
                confidence=confidence,
                reason=f"RSI_OVERBOUGHT_REVERSAL (RSI9:{rsi_fast:.0f}, RSI14:{rsi_slow:.0f})"
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
        
        # Implement AGGRESSIVE trailing stop if enabled
        if self.trailing_stop_enabled:
            # Calculate profit in pips/points
            if position.direction == "BUY":
                profit_distance = current_price - position.entry_price
                atr_estimate = abs(position.take_profit - position.entry_price) / self.profit_target_multiplier
                
                # STAGE 1: Move to breakeven after 0.5x ATR profit (QUICK)
                if profit_distance >= (atr_estimate * 0.5):
                    new_stop = position.entry_price + (atr_estimate * 0.1)  # Breakeven + small buffer
                    if new_stop > position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "BREAKEVEN")
                
                # STAGE 2: Trail at 60% of profit after 1x ATR profit
                elif profit_distance >= atr_estimate:
                    new_stop = position.entry_price + (profit_distance * 0.6)
                    if new_stop > position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "TRAIL_60")
                
                # STAGE 3: Trail at 70% of profit after 1.5x ATR profit
                elif profit_distance >= (atr_estimate * 1.5):
                    new_stop = position.entry_price + (profit_distance * 0.7)
                    if new_stop > position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "TRAIL_70")
                
                # STAGE 4: Trail at 80% of profit after 2x ATR profit (let it run!)
                elif profit_distance >= (atr_estimate * 2.0):
                    new_stop = position.entry_price + (profit_distance * 0.8)
                    if new_stop > position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "TRAIL_80")
            
            elif position.direction == "SELL":
                profit_distance = position.entry_price - current_price
                atr_estimate = abs(position.entry_price - position.take_profit) / self.profit_target_multiplier
                
                # STAGE 1: Move to breakeven after 0.5x ATR profit (QUICK)
                if profit_distance >= (atr_estimate * 0.5):
                    new_stop = position.entry_price - (atr_estimate * 0.1)  # Breakeven + small buffer
                    if new_stop < position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "BREAKEVEN")
                
                # STAGE 2: Trail at 60% of profit after 1x ATR profit
                elif profit_distance >= atr_estimate:
                    new_stop = position.entry_price - (profit_distance * 0.6)
                    if new_stop < position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "TRAIL_60")
                
                # STAGE 3: Trail at 70% of profit after 1.5x ATR profit
                elif profit_distance >= (atr_estimate * 1.5):
                    new_stop = position.entry_price - (profit_distance * 0.7)
                    if new_stop < position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "TRAIL_70")
                
                # STAGE 4: Trail at 80% of profit after 2x ATR profit (let it run!)
                elif profit_distance >= (atr_estimate * 2.0):
                    new_stop = position.entry_price - (profit_distance * 0.8)
                    if new_stop < position.stop_loss:
                        return self._create_trailing_stop_update(position, new_stop, "TRAIL_80")
        
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
    
    def _create_trailing_stop_update(self, position: Position, new_stop: float, stage: str) -> Signal:
        """
        Create a signal to update trailing stop.
        
        Args:
            position: Current position
            new_stop: New stop loss level
            stage: Stage name for logging
            
        Returns:
            Signal indicating stop should be updated
        """
        # This is a special signal type that tells the trade manager to update the stop
        # but NOT close the position
        return Signal(
            symbol=position.symbol,
            direction="UPDATE_STOP",  # Special direction
            entry_price=new_stop,  # New stop loss value
            stop_loss=new_stop,
            take_profit=position.take_profit,
            timestamp=datetime.now(),
            confidence=1.0,
            reason=f"TRAILING_STOP_{stage}"
        )
    
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
        
        # CRITICAL: Cap based on available margin
        # Check if we can actually afford this lot size
        account_info = mt5.account_info()
        if account_info and account_info.margin_free > 0:
            # Calculate margin required for this lot size
            order_type = mt5.ORDER_TYPE_BUY  # Doesn't matter for margin calc
            margin_required = mt5.order_calc_margin(order_type, symbol, lot_size, entry_price)
            
            if margin_required is not None and margin_required > 0:
                # If we don't have enough margin, reduce lot size
                if margin_required > account_info.margin_free:
                    # Calculate max affordable lot size (use 80% of free margin for safety)
                    affordable_margin = account_info.margin_free * 0.8
                    affordable_lot = (lot_size * affordable_margin) / margin_required
                    
                    # Round down to valid lot step
                    if lot_step > 0:
                        affordable_lot = int(affordable_lot / lot_step) * lot_step
                    
                    # Ensure still above minimum
                    if affordable_lot >= min_lot:
                        lot_size = affordable_lot
                    else:
                        # Can't afford even minimum lot
                        return 0.0  # Signal that we can't trade
        
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
