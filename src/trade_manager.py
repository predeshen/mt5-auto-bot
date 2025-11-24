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
        self._current_lot_multiplier = 1.0
        self._progressive_sizing_enabled = False
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
    
    def get_progressive_lot_size(self, calculated_lot: float) -> float:
        """
        Get lot size with progressive multiplier applied.
        
        Args:
            calculated_lot: Base calculated lot size (ignored if progressive sizing enabled)
            
        Returns:
            Adjusted lot size based on win/loss streak
        """
        if not self._progressive_sizing_enabled:
            return calculated_lot
        
        # Always use progressive lot when enabled (ignore calculated lot)
        progressive_lot = self._base_lot_size * self._current_lot_multiplier
        return progressive_lot
    
    def _update_progressive_multiplier(self, won: bool) -> None:
        """Update the progressive multiplier based on trade result."""
        if not self._progressive_sizing_enabled:
            return
        
        if won:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
            # Double the multiplier after each win (no cap - grows with equity)
            self._current_lot_multiplier = self._current_lot_multiplier * 2.0
        else:
            self._consecutive_losses += 1
            self._consecutive_wins = 0
            # Reset to base after loss
            self._current_lot_multiplier = 1.0
    
    def get_position_count(self) -> int:
        """Get current number of open positions."""
        return len(self._positions)
    
    def can_open_new_position(self) -> bool:
        """Check if new position can be opened."""
        return self.get_position_count() < self._max_positions
    
    def open_position(self, signal: Signal, size: float) -> Optional[Position]:
        """
        Open a new trading position.
        
        Args:
            signal: Trading signal with entry details
            size: Position size in lots
            
        Returns:
            Position object if successful, None otherwise
        """
        # Check if we can open new position
        if not self.can_open_new_position():
            print(f"Cannot open position: Maximum positions ({self._max_positions}) reached")
            return None
        
        # Apply progressive sizing if enabled
        size = self.get_progressive_lot_size(size)
        
        # Validate order parameters
        if size <= 0:
            print("Invalid position size")
            return None
        
        # Get symbol info for validation
        symbol_info = mt5.symbol_info(signal.symbol)
        if symbol_info is None:
            print(f"Failed to get symbol info for {signal.symbol}")
            return None
        
        # Validate volume against broker requirements
        if size < symbol_info.volume_min:
            print(f"Volume {size} below minimum {symbol_info.volume_min}, adjusting to minimum")
            size = symbol_info.volume_min
        elif size > symbol_info.volume_max:
            print(f"Volume {size} above maximum {symbol_info.volume_max}, adjusting to maximum")
            size = symbol_info.volume_max
        
        # Round to valid step
        if symbol_info.volume_step > 0:
            size = round(size / symbol_info.volume_step) * symbol_info.volume_step
        
        print(f"Opening position: {signal.symbol} {signal.direction} {size} lots (min: {symbol_info.volume_min}, max: {symbol_info.volume_max}, step: {symbol_info.volume_step})")
        
        # Prepare order request
        order_type = mt5.ORDER_TYPE_BUY if signal.direction == "BUY" else mt5.ORDER_TYPE_SELL
        
        # Determine appropriate filling mode for this symbol
        filling_type = symbol_info.filling_mode
        
        # Try different filling modes in order of preference
        if filling_type & mt5.SYMBOL_FILLING_FOK:
            type_filling = mt5.ORDER_FILLING_FOK
        elif filling_type & mt5.SYMBOL_FILLING_IOC:
            type_filling = mt5.ORDER_FILLING_IOC
        else:
            type_filling = mt5.ORDER_FILLING_RETURN
        
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
            "comment": f"Scalper: {signal.reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,
        }
        
        # Attempt to send order with retries
        for attempt in range(self._retry_attempts):
            result = mt5.order_send(request)
            
            if result is None:
                print(f"Order send failed (attempt {attempt + 1}): No result")
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
                
                print(f"Position opened: {signal.symbol} {signal.direction} {size} lots @ {result.price}")
                return position
            else:
                print(f"Order failed (attempt {attempt + 1}): {result.retcode} - {result.comment}")
        
        print(f"Failed to open position after {self._retry_attempts} attempts")
        return None
    
    def close_position(self, position: Position) -> Optional[TradeResult]:
        """
        Close an open position.
        
        Args:
            position: Position to close
            
        Returns:
            TradeResult if successful, None otherwise
        """
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
                
                # Update progressive multiplier
                self._update_progressive_multiplier(profit > 0)
                
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
                    print(f"Position auto-closed: {position.symbol} @ {close_price}, Profit: {profit:.2f} | "
                          f"Wins: {self._consecutive_wins}, Next lot: {self._base_lot_size * self._current_lot_multiplier:.2f}")
                else:
                    print(f"Position auto-closed: {position.symbol} @ {close_price}, Profit: {profit:.2f}")
                
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
            if filling_type & mt5.SYMBOL_FILLING_FOK:
                type_filling = mt5.ORDER_FILLING_FOK
            elif filling_type & mt5.SYMBOL_FILLING_IOC:
                type_filling = mt5.ORDER_FILLING_IOC
            else:
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
                
                # Update progressive multiplier based on result
                self._update_progressive_multiplier(profit > 0)
                
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
                
                # Show progressive sizing status
                if self._progressive_sizing_enabled:
                    print(f"Position closed: {position.symbol} @ {close_price}, Profit: {profit:.2f} | "
                          f"Wins: {self._consecutive_wins}, Next lot: {self._base_lot_size * self._current_lot_multiplier:.2f}")
                else:
                    print(f"Position closed: {position.symbol} @ {close_price}, Profit: {profit:.2f}")
                
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
                self._update_progressive_multiplier(profit > 0)
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
