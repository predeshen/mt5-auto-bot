"""Application Controller - orchestrates the trading workflow."""

import signal
import sys
from typing import Optional
from src.mt5_connection import MT5ConnectionManager
from src.display import DisplayManager
from src.volatility_scanner import VolatilityScanner
from src.scalping_strategy import ScalpingStrategy
from src.trade_manager import TradeManager
from src.models import Credentials
from src.logger import logger


class ApplicationController:
    """Main application controller coordinating all components."""
    
    def __init__(self):
        self.connection_manager = MT5ConnectionManager()
        self.display = DisplayManager()
        # Lower threshold to 0.0005 for better instrument discovery
        self.scanner = VolatilityScanner(min_volatility_threshold=0.0005)
        self.strategy = ScalpingStrategy()
        self.trade_manager = TradeManager()
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.running = False
    
    def startup_sequence(self) -> bool:
        """
        Execute startup sequence: credentials → connect → equity → parameters.
        
        Returns:
            True if startup successful, False otherwise
        """
        import json
        import os
        
        self.display.show_welcome()
        
        # Load saved accounts
        config_path = "config.json"
        saved_accounts = {}
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    saved_accounts = config.get('accounts', {})
            except Exception as e:
                logger.warning(f"Could not load config: {e}")
        
        # Get credentials
        if saved_accounts:
            account_choice = self.display.prompt_account_selection(saved_accounts)
            
            if account_choice == 'custom':
                credentials = self.display.prompt_credentials()
            else:
                # Use saved account
                acc = saved_accounts[account_choice]
                credentials = Credentials(
                    account=acc['account'],
                    password=acc['password'],
                    server=acc['server']
                )
                print(f"\nUsing: {acc['name']}")
        else:
            credentials = self.display.prompt_credentials()
        
        # Connect to MT5
        logger.info(f"Connecting to MT5 account {credentials.account}...")
        if not self.connection_manager.connect(
            credentials.account,
            credentials.password,
            credentials.server
        ):
            self.display.display_error("Failed to connect to MT5")
            return False
        
        logger.info("Connected to MT5 successfully")
        
        # Display account info
        account_info = self.connection_manager.get_account_info()
        if account_info:
            self.display.display_account_info(account_info)
        else:
            self.display.display_error("Failed to retrieve account information")
            return False
        
        # Get trading parameters
        params = self.display.prompt_trading_parameters()
        
        # Validate parameters
        try:
            params.validate()
        except ValueError as e:
            self.display.display_error(f"Invalid parameters: {e}")
            return False
        
        # Display parameter summary and get confirmation
        if not self.display.display_parameter_summary(params):
            logger.info("User cancelled parameter confirmation")
            return False
        
        # Store risk percent for position sizing
        self.risk_percent = params.risk_percent
        
        # Configure components
        self.trade_manager.set_max_positions(params.max_open_positions)
        self.strategy.set_parameters(
            profit_target_multiplier=params.profit_target_atr_multiplier,
            stop_loss_multiplier=params.stop_loss_atr_multiplier,
            trailing_stop_enabled=params.trailing_stop_enabled
        )
        
        # Enable progressive sizing if requested
        if getattr(params, 'progressive_sizing', False):
            self.trade_manager.enable_progressive_sizing(enabled=True, base_lot=0.01)
        
        logger.info("Startup sequence completed successfully")
        return True
    
    def main_loop(self) -> None:
        """Main trading loop with automated monitoring."""
        import time
        import MetaTrader5 as mt5
        
        logger.info("Entering main trading loop")
        self.running = True
        
        # Force specific symbols regardless of volatility
        forced_symbols = ["XAUUSD", "US30.F", "USA30", "USA100", "US100.F", "GER40", "GER40.F"]
        
        logger.info(f"Forcing monitoring of: {', '.join(forced_symbols)}")
        
        # Verify symbols exist on broker
        available_symbols = self.scanner.get_available_symbols()
        logger.info(f"Found {len(available_symbols)} available symbols on broker")
        
        # Filter to only symbols available on this broker
        selected_symbols = [s for s in forced_symbols if s in available_symbols]
        
        if not selected_symbols:
            self.display.display_error(f"None of the forced symbols {forced_symbols} are available on this broker")
            logger.error(f"Available symbols: {available_symbols[:20]}")
            return
        
        logger.info(f"Selected instruments for trading: {', '.join(selected_symbols)}")
        
        print(f"\n🤖 AUTOMATED TRADING ACTIVE")
        print(f"Monitoring: {', '.join(selected_symbols)}")
        print(f"Press Ctrl+C to shutdown...\n")
        
        last_scan_time = time.time()
        scan_interval = 3  # Scan every 3 seconds for scalping
        
        try:
            while self.running:
                current_time = time.time()
                
                # Monitor existing positions
                self.trade_manager.monitor_positions()
                positions = self.trade_manager.get_open_positions()
                
                # Display position count
                if positions:
                    self.display.display_position_count(
                        len(positions),
                        self.trade_manager._max_positions
                    )
                
                # Check exit conditions for open positions
                for position in positions:
                    # Get current price
                    tick = mt5.symbol_info_tick(position.symbol)
                    if tick:
                        current_price = tick.bid if position.direction == "BUY" else tick.ask
                        
                        # Check if exit signal generated
                        exit_signal = self.strategy.analyze_exit(position, current_price)
                        if exit_signal:
                            logger.info(f"Exit signal for {position.symbol}: {exit_signal.reason}")
                            result = self.trade_manager.close_position(position)
                            if result:
                                self.display.display_trade_closed(result)
                
                # Look for new entry signals (only if we can open more positions)
                if self.trade_manager.can_open_new_position() and (current_time - last_scan_time) >= scan_interval:
                    last_scan_time = current_time
                    
                    for symbol in selected_symbols:
                        # Allow 1 position per symbol at a time
                        symbol_positions = [p for p in positions if p.symbol == symbol]
                        if len(symbol_positions) >= 1:
                            continue
                        
                        # Get recent candles (M1 for scalping)
                        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50)
                        if rates is not None and len(rates) >= 30:
                            candles = [
                                {
                                    'open': float(r['open']),
                                    'high': float(r['high']),
                                    'low': float(r['low']),
                                    'close': float(r['close']),
                                    'tick_volume': int(r['tick_volume']) if 'tick_volume' in r.dtype.names else 0
                                }
                                for r in rates
                            ]
                            
                            # Check for entry signal
                            signal = self.strategy.analyze_entry(symbol, candles)
                            if signal:
                                logger.info(f"Entry signal: {signal.symbol} {signal.direction} - {signal.reason}")
                                
                                # Calculate position size
                                account_info = self.connection_manager.get_account_info()
                                if account_info:
                                    lot_size = self.strategy.calculate_position_size(
                                        signal.symbol,
                                        account_info.equity,
                                        self.risk_percent,  # Use configured risk percent
                                        signal.entry_price,
                                        signal.stop_loss
                                    )
                                    
                                    logger.info(f"Calculated lot size: {lot_size} for {signal.symbol}")
                                    
                                    # Open position
                                    position = self.trade_manager.open_position(signal, lot_size)
                                    if position:
                                        self.display.display_trade_opened(position)
                
                # Update status
                self.display.update_status_line(
                    f"Monitoring {len(selected_symbols)} instruments | "
                    f"Open positions: {len(positions)}/{self.trade_manager._max_positions}"
                )
                
                # Sleep before next iteration
                time.sleep(2)  # Check every 2 seconds for scalping
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.running = False
    
    def shutdown_sequence(self) -> None:
        """Execute graceful shutdown sequence."""
        logger.info("Starting shutdown sequence")
        
        # Get open positions
        positions = self.trade_manager.get_open_positions()
        
        if positions:
            print(f"\n{len(positions)} open position(s) found:")
            for pos in positions:
                print(f"  - {pos.symbol} {pos.direction} {pos.volume} lots")
            
            close_all = input("\nClose all positions before exit? (yes/no): ").lower()
            
            if close_all in ['yes', 'y']:
                logger.info("Closing all positions...")
                results = self.trade_manager.close_all_positions()
                logger.info(f"Closed {len(results)} position(s)")
        
        # Disconnect from MT5
        self.connection_manager.disconnect()
        logger.info("Disconnected from MT5")
        logger.info("Shutdown complete")
    
    def run(self) -> None:
        """Main entry point - run the application."""
        try:
            # Startup
            if not self.startup_sequence():
                logger.error("Startup failed")
                sys.exit(1)
            
            # Main loop
            self.main_loop()
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            self.display.display_error(f"Fatal error: {e}")
        
        finally:
            # Shutdown
            self.shutdown_sequence()
