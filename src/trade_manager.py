"""Trade Manager for executing and monitoring trades."""

import MetaTrader5 as mt5
from typing import List, Optional, Dict
from datetime import datetime
from src.models import Signal, Position, TradeResult


class TradeManager:
    """Manages trade execution, monitoring, and position lifecycle."""
    
    def __init__(self):
        self._positions: Dict[int, Position] = {}
        self._max_positions = 3
        self._retry_attempts = 3
        self._base_lot_size = 0.01
        self._progressive_sizing_enabled = False
        
        # Per-symbol progressive sizing tracking
        self._symbol_multipliers: Dict[str, float] = {}  # Track multiplier per symbol
        self._symbol_wins: Dict[str, int] = {}  # Track consecutive wins per symbol
        self._symbol_losses: Dict[str, int] = {}  # Track consecutive losses per symbol
        
        # Global tracking (for display purposes)
        self._consecutive_wins = 0
        self._consecutive_losses = 0
        self._max_multiplier = None  # No cap - grows based on equity
    
    def set_max_positions(self, max_positions: int) -> None:
        """Set maximum number of open positions allowed."""
        self._max_positions = max_positions
    
    def enable_progressive_sizing(self, enabled: bool = True, base_lot: float = 0.01) -> None:
        """
        Enable progressive lot sizing (martingale-style).
        After each win, lot size doubles: 0.01 -> 0.02 -> 0.04 -> 0.08
        After a loss, resets to base lot size.
        
        Args:
            enabled: Enable/disable progressive sizing
            base_lot: Base lot size to start with
        """
        self._progressive_sizing_enabled = enabled
        self._base_lot_size = base_lot
        self._current_lot_multiplier = 1.0
        self._consecutive_wins = 0
        self._consecutive_losses = 0
    
    def get_progressive_lot_size(self, symbol: str, calculated_lot: float) -> float:
        """
        Get lot size with progressive multiplier applied PER SYMBOL.
        
        Args:
            symbol: Trading symbol
            calculated_lot: Base calculated lot size (ignored if progressive sizing enabled)
            
        Returns:
            Adjusted lot size based on win/loss streak for this symbol
        """
        if not self._progressive_sizing_enabled:
            return calculated_lot
        
        # Initialize symbol tracking if not exists
        if symbol not in self._symbol_multipliers:
            self._symbol_multipliers[symbol] = 1.0
            self._symbol_wins[symbol] = 0
            self._symbol_losses[symbol] = 0
        
        # Get symbol-specific multiplier
        progressive_lot = self._base_lot_size * self._symbol_multipliers[symbol]
        return progressive_lot
    
    def _update_progressive_multiplier(self, symbol: str, won: bool) -> None:
        """Update the progressive multiplier based on trade result PER SYMBOL."""
        if not self._progressive_sizing_enabled:
            return
        
        # Initialize symbol tracking if not exists
        if symbol not in self._symbol_multipliers:
            self._symbol_multipliers[symbol] = 1.0
            self._symbol_wins[symbol] = 0
            self._symbol_losses[symbol] = 0
        
        if won:
            # Update symbol-specific tracking
            self._symbol_wins[symbol] += 1
            self._symbol_losses[symbol] = 0
            # Double the multiplier after each win (no cap - grows with equity)
            self._symbol_multipliers[symbol] = self._symbol_multipliers[symbol] * 2.0
            
            # Update global tracking
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        else:
            # Update symbol-specific tracking
            self._symbol_losses[symbol] += 1
            self._symbol_wins[symbol] = 0
            # Reset to base after loss
            self._symbol_multipliers[symbol] = 1.0
            
            # Update global tracking
            self._consecutive_losses += 1
            self._consecutive_wins = 0
    
    def get_position_count(self) -> int:
        """Get current number of open positions."""
        return len(self._positions)
    
    def can_open_new_position(self) -> bool:
        """Check if new position can be opened."""
        return self.get_position_count() < self._max_positions
    
    def open_position(self, signal: Signal, size: float, skip_progressive: bool = False) -> Optional[Position]:
        """
        Open a new trading position.
        
        Args:
            signal: Trading signal with entry details
            size: Position size in lots
            skip_progressive: Skip progressive sizing (used when pyramiding)
            
        Returns:
            Position object if successful, None otherwise
        """
        from src.logger import logger
        
        # Check if we can open new position
        if not self.can_open_new_position():
            msg = f"Cannot open position: Maximum positions ({self._max_positions}) reached"
            print(msg)
            logger.warning(msg)
            return None
        
        # Apply progressive sizing if enabled (per symbol) - unless pyramiding
        if not skip_progressive:
            size = self.get_progressive_lot_size(signal.symbol, size)
        
        # Validate order parameters
        if size <= 0:
            msg = "Invalid position size"
            print(msg)
            logger.error(msg)
            return None
        
        # Get symbol info for validation
        symbol_info = mt5.symbol_info(signal.symbol)
        if symbol_info is None:
            msg = f"Failed to get symbol info for {signal.symbol}"
            print(msg)
            logger.error(msg)
            return None
        
        # Check if symbol is visible and tradeable
        if not symbol_info.visible:
            print(f"⚠️  Symbol {signal.symbol} is not visible in Market Watch")
            logger.warning(f"Symbol {signal.symbol} is not visible - attempting to enable")
            # Try to enable it
            if not mt5.symbol_select(signal.symbol, True):
                logger.error(f"Failed to enable {signal.symbol} in Market Watch")
                return None
            # Refresh symbol info
            symbol_info = mt5.symbol_info(signal.symbol)
        
        # Check if trading is allowed
        if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
            print(f"⚠️  Trading is disabled for {signal.symbol} (trade_mode: {symbol_info.trade_mode})")
            logger.warning(f"Trading disabled for {signal.symbol}")
            return None
        
        # Check if market is open
        if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            print(f"⚠️  Market is closed for {signal.symbol}")
            logger.warning(f"Market closed for {signal.symbol}")
            return None
        
        # Validate volume against broker requirements
        if size < symbol_info.volume_min:
            msg = f"Volume {size} below minimum {symbol_info.volume_min}, adjusting to minimum"
            print(msg)
            logger.info(msg)
            size = symbol_info.volume_min
        elif size > symbol_info.volume_max:
            msg = f"Volume {size} above maximum {symbol_info.volume_max}, adjusting to maximum"
            print(msg)
            logger.warning(msg)
            size = symbol_info.volume_max
        
        # Round to valid step
        if symbol_info.volume_step > 0:
            size = round(size / symbol_info.volume_step) * symbol_info.volume_step
        
        # Check margin requirement
        account_info = mt5.account_info()
        if account_info:
            # Calculate required margin
            margin_required = mt5.order_calc_margin(
                mt5.ORDER_TYPE_BUY if signal.direction == "BUY" else mt5.ORDER_TYPE_SELL,
                signal.symbol,
                size,
                signal.entry_price
            )
            
            if margin_required is not None:
                if margin_required > account_info.margin_free:
                    print(f"⚠️  Insufficient margin for {signal.symbol}: Need ${margin_required:.2f}, Have ${account_info.margin_free:.2f}")
                    logger.warning(f"Insufficient margin: need {margin_required:.2f}, have {account_info.margin_free:.2f}")
                    return None
                else:
                    print(f"💰 Margin OK: Need ${margin_required:.2f}, Have ${account_info.margin_free:.2f}")
        
        msg = f"Opening position: {signal.symbol} {signal.direction} {size} lots (min: {symbol_info.volume_min}, max: {symbol_info.volume_max}, step: {symbol_info.volume_step})"
        print(msg)
        logger.info(msg)
        
        # Prepare order request
        order_type = mt5.ORDER_TYPE_BUY if signal.direction == "BUY" else mt5.ORDER_TYPE_SELL
        
        # Determine appropriate filling mode for this symbol
        filling_type = symbol_info.filling_mode
        
        # Try different filling modes in order of preference
        # Check which filling modes are supported (bit flags)
        if filling_type & 1:  # FOK (Fill or Kill)
            type_filling = mt5.ORDER_FILLING_FOK
        elif filling_type & 2:  # IOC (Immediate or Cancel)
            type_filling = mt5.ORDER_FILLING_IOC
        else:  # Return
            type_filling = mt5.ORDER_FILLING_RETURN
        
        # Prepare comment (max 31 characters, ASCII only)
        comment = signal.reason[:20] if signal.reason else "Scalper"
        # Remove any special characters that might cause issues
        comment = ''.join(c for c in comment if c.isalnum() or c in ['_', '-', ' '])
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": size,
            "type": order_type,
            "price": signal.entry_price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,
        }
        
        # Attempt to send order with retries
        for attempt in range(self._retry_attempts):
            result = mt5.order_send(request)
            
            if result is None:
                # Get detailed error from MT5
                error = mt5.last_error()
                msg = f"Order send failed (attempt {attempt + 1}): No result - MT5 Error: {error}"
                print(msg)
                logger.error(msg)
                
                # Check specific error conditions
                if error[0] == 10018:  # Market is closed
                    print(f"⚠️  Market is closed for {signal.symbol}")
                    logger.warning(f"Market is closed for {signal.symbol}")
                    return None  # Don't retry if market is closed
                elif error[0] == 10019:  # No prices
                    print(f"⚠️  No prices available for {signal.symbol}")
                    logger.warning(f"No prices available for {signal.symbol}")
                    return None
                elif error[0] == 10013:  # Invalid request
                    print(f"⚠️  Invalid request for {signal.symbol}")
                    logger.warning(f"Invalid request for {signal.symbol}")
                    return None
                
                continue
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # Order successful - create position object
                position = Position(
                    ticket=result.order,
                    symbol=signal.symbol,
                    direction=signal.direction,
                    volume=size,
                    entry_price=result.price,
                    current_price=result.price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    profit=0.0,
                    open_time=datetime.now()
                )
                
                # Store position
                self._positions[result.order] = position
                
                print(f"✅ Position opened: {signal.symbol} {signal.direction} {size} lots @ {result.price}")
                logger.info(f"Position opened: {signal.symbol} {signal.direction} {size} lots @ {result.price}")
                return position
            else:
                msg = f"Order failed (attempt {attempt + 1}): {result.retcode} - {result.comment}"
                print(msg)
                logger.error(msg)
        
        print(f"❌ Failed to open position after {self._retry_attempts} attempts")
        logger.error(f"Failed to open position after {self._retry_attempts} attempts")
        return None
    
    def close_position(self, position: Position) -> Optional[TradeResult]:
        """
        Close an open position.
        
        Args:
            position: Position to close
            
        Returns:
            TradeResult if successful, None otherwise
        """
        from src.logger import logger
        
        # First check if position still exists in MT5
        mt5_position = mt5.positions_get(ticket=position.ticket)
        if mt5_position is None or len(mt5_position) == 0:
            # Position already closed (probably by SL/TP)
            print(f"Position {position.ticket} already closed by broker")
            
            # Get the actual close info from history
            from_date = position.open_time
            to_date = datetime.now()
            deals = mt5.history_deals_get(position=position.ticket)
            
            if deals and len(deals) > 0:
                # Find the closing deal
                close_deal = deals[-1]  # Last deal is the close
                close_price = close_deal.price
                profit = close_deal.profit
                
                # Update progressive multiplier (per symbol)
                self._update_progressive_multiplier(position.symbol, profit > 0)
                
                # Remove from our tracking
                if position.ticket in self._positions:
                    del self._positions[position.ticket]
                
                # Create trade result
                trade_result = TradeResult(
                    ticket=position.ticket,
                    symbol=position.symbol,
                    direction=position.direction,
                    volume=position.volume,
                    entry_price=position.entry_price,
                    exit_price=close_price,
                    profit=profit,
                    open_time=position.open_time,
                    close_time=datetime.now(),
                    exit_reason="Broker SL/TP"
                )
                
                if self._progressive_sizing_enabled:
                    symbol_wins = self._symbol_wins.get(position.symbol, 0)
                    next_lot = self._base_lot_size * self._symbol_multipliers.get(position.symbol, 1.0)
                    msg = f"Position auto-closed: {position.symbol} @ {close_price}, Profit: {profit:.2f} | {position.symbol} Wins: {symbol_wins}, Next lot: {next_lot:.2f}"
                    print(msg)
                    logger.info(msg)
                else:
                    msg = f"Position auto-closed: {position.symbol} @ {close_price}, Profit: {profit:.2f}"
                    print(msg)
                    logger.info(msg)
                
                return trade_result
            else:
                # Can't find close info, just remove from tracking
                if position.ticket in self._positions:
                    del self._positions[position.ticket]
                return None
        
        # Position still exists, close it manually
        order_type = mt5.ORDER_TYPE_SELL if position.direction == "BUY" else mt5.ORDER_TYPE_BUY
        
        # Get current price
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            print(f"Failed to get current price for {position.symbol}")
            return None
        
        close_price = tick.bid if position.direction == "BUY" else tick.ask
        
        # Get symbol info for filling mode
        symbol_info = mt5.symbol_info(position.symbol)
        if symbol_info:
            filling_type = symbol_info.filling_mode
            # Check which filling modes are supported (bit flags)
            if filling_type & 1:  # FOK (Fill or Kill)
                type_filling = mt5.ORDER_FILLING_FOK
            elif filling_type & 2:  # IOC (Immediate or Cancel)
                type_filling = mt5.ORDER_FILLING_IOC
            else:  # Return
                type_filling = mt5.ORDER_FILLING_RETURN
        else:
            type_filling = mt5.ORDER_FILLING_RETURN
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": close_price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Scalper close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,
        }
        
        # Attempt to close with retries
        for attempt in range(self._retry_attempts):
            result = mt5.order_send(request)
            
            if result is None:
                print(f"Close order failed (attempt {attempt + 1}): No result")
                continue
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # Calculate profit
                if position.direction == "BUY":
                    profit = (close_price - position.entry_price) * position.volume * 100000  # Simplified
                else:
                    profit = (position.entry_price - close_price) * position.volume * 100000
                
                # Update progressive multiplier based on result (per symbol)
                self._update_progressive_multiplier(position.symbol, profit > 0)
                
                # Create trade result
                trade_result = TradeResult(
                    ticket=position.ticket,
                    symbol=position.symbol,
                    direction=position.direction,
                    volume=position.volume,
                    entry_price=position.entry_price,
                    exit_price=close_price,
                    profit=profit,
                    open_time=position.open_time,
                    close_time=datetime.now(),
                    exit_reason="Manual close"
                )
                
                # Remove from positions
                if position.ticket in self._positions:
                    del self._positions[position.ticket]
                
                # Show progressive sizing status (per symbol)
                if self._progressive_sizing_enabled:
                    symbol_wins = self._symbol_wins.get(position.symbol, 0)
                    next_lot = self._base_lot_size * self._symbol_multipliers.get(position.symbol, 1.0)
                    msg = f"Position closed: {position.symbol} @ {close_price}, Profit: {profit:.2f} | {position.symbol} Wins: {symbol_wins}, Next lot: {next_lot:.2f}"
                    print(msg)
                    logger.info(msg)
                else:
                    msg = f"Position closed: {position.symbol} @ {close_price}, Profit: {profit:.2f}"
                    print(msg)
                    logger.info(msg)
                
                return trade_result
            else:
                print(f"Close failed (attempt {attempt + 1}): {result.retcode} - {result.comment}")
        
        print(f"Failed to close position after {self._retry_attempts} attempts")
        return None
    
    def get_open_positions(self) -> List[Position]:
        """Get list of all open positions and sync with MT5."""
        # Get actual positions from MT5
        mt5_positions = mt5.positions_get()
        
        if mt5_positions is None:
            mt5_positions = []
        
        # Create set of MT5 ticket numbers
        mt5_tickets = {pos.ticket for pos in mt5_positions}
        
        # Remove positions from our tracking that no longer exist in MT5
        closed_tickets = []
        for ticket in list(self._positions.keys()):
            if ticket not in mt5_tickets:
                closed_tickets.append(ticket)
        
        # Handle positions that were closed by broker
        for ticket in closed_tickets:
            position = self._positions[ticket]
            # Try to get close info from history
            deals = mt5.history_deals_get(position=ticket)
            if deals and len(deals) > 0:
                close_deal = deals[-1]
                profit = close_deal.profit
                self._update_progressive_multiplier(position.symbol, profit > 0)
                print(f"Position {ticket} was closed by broker, Profit: {profit:.2f}")
            
            del self._positions[ticket]
        
        # Update current prices and profits for existing positions
        for mt5_pos in mt5_positions:
            if mt5_pos.ticket in self._positions:
                position = self._positions[mt5_pos.ticket]
                position.current_price = mt5_pos.price_current
                position.profit = mt5_pos.profit
        
        return list(self._positions.values())
    
    def monitor_positions(self) -> None:
        """
        Monitor open positions and update their status.
        This is called periodically by the main loop.
        """
        # Refresh positions from MT5
        self.get_open_positions()
    
    def update_stop_loss(self, position: Position, new_stop_loss: float) -> bool:
        """
        Update the stop loss for an open position (trailing stop).
        
        Args:
            position: Position to update
            new_stop_loss: New stop loss level
            
        Returns:
            True if successful, False otherwise
        """
        from src.logger import logger
        
        # Verify position still exists
        mt5_position = mt5.positions_get(ticket=position.ticket)
        if mt5_position is None or len(mt5_position) == 0:
            logger.warning(f"Cannot update stop - position {position.ticket} not found")
            return False
        
        # Get symbol info for filling mode
        symbol_info = mt5.symbol_info(position.symbol)
        if symbol_info:
            filling_type = symbol_info.filling_mode
            if filling_type & 1:
                type_filling = mt5.ORDER_FILLING_FOK
            elif filling_type & 2:
                type_filling = mt5.ORDER_FILLING_IOC
            else:
                type_filling = mt5.ORDER_FILLING_RETURN
        else:
            type_filling = mt5.ORDER_FILLING_RETURN
        
        # Prepare modification request
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": position.ticket,
            "sl": new_stop_loss,
            "tp": position.take_profit,
            "type_filling": type_filling,
        }
        
        # Send modification request
        result = mt5.order_send(request)
        
        if result is None:
            logger.error(f"Failed to update stop loss for {position.ticket}: No result")
            return False
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            # Update our local tracking
            position.stop_loss = new_stop_loss
            if position.ticket in self._positions:
                self._positions[position.ticket].stop_loss = new_stop_loss
            
            logger.info(f"Stop loss updated for {position.symbol}: {new_stop_loss:.5f}")
            return True
        else:
            logger.error(f"Failed to update stop loss: {result.retcode} - {result.comment}")
            return False
    
    def close_all_positions(self) -> List[TradeResult]:
        """
        Close all open positions.
        
        Returns:
            List of TradeResult objects
        """
        results = []
        positions = list(self._positions.values())
        
        for position in positions:
            result = self.close_position(position)
            if result:
                results.append(result)
        
        return results
