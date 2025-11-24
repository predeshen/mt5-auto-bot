"""
SMC Strategy Auto Trader - Entry Point

This script runs the Smart Money Concepts (SMC) strategy exclusively.
It trades only whitelisted symbols (US30, XAUUSD, NASDAQ) during market hours
using pending orders at FVG and Order Block zones.
"""

import signal
import sys
import time
import json
import os
from datetime import datetime
import MetaTrader5 as mt5

from src.mt5_connection import MT5ConnectionManager
from src.display import DisplayManager
from src.smc_strategy import SMCStrategy
from src.models import Credentials, TradingParameters
from src.logger import logger


class SMCController:
    """Controller for SMC-only trading."""
    
    def __init__(self):
        self.connection_manager = MT5ConnectionManager()
        self.display = DisplayManager()
        self.smc_strategy = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.running = False
    
    def startup_sequence(self) -> bool:
        """Execute startup sequence."""
        self.display.show_welcome()
        
        print("\n" + "="*60)
        print("🎯 SMC STRATEGY MODE")
        print("="*60)
        print("Trading: US30, XAUUSD, NASDAQ (and futures)")
        print("Method: Pending orders at FVG/Order Block zones")
        print("Timeframes: H4, H1, M15, M5 confluence")
        print("="*60 + "\n")
        
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
        
        try:
            params.validate()
        except ValueError as e:
            self.display.display_error(f"Invalid parameters: {e}")
            return False
        
        # Display parameter summary
        if not self.display.display_parameter_summary(params):
            logger.info("User cancelled parameter confirmation")
            return False
        
        # Initialize SMC Strategy
        logger.info("Initializing SMC Strategy...")
        self.smc_strategy = SMCStrategy(self.connection_manager)
        
        # Store risk parameters
        self.risk_percent = params.risk_percent
        self.max_positions = params.max_open_positions
        
        logger.info("SMC Strategy initialized successfully")
        return True
    
    def main_loop(self) -> None:
        """Main SMC trading loop."""
        logger.info("Entering SMC trading loop")
        self.running = True
        
        # Get tradeable symbols (whitelisted + market hours check)
        tradeable_symbols = self.smc_strategy.get_tradeable_symbols()
        
        if not tradeable_symbols:
            print("\n⚠️  No tradeable symbols available right now.")
            print("Possible reasons:")
            print("  • Markets are closed (trading hours: Sun 23:00 - Fri 22:00 GMT)")
            print("  • Broker doesn't have whitelisted symbols (US30, XAUUSD, NASDAQ)")
            print("\nWaiting for markets to open...")
        else:
            print(f"\n✅ Tradeable symbols: {', '.join(tradeable_symbols)}")
        
        print(f"\n🤖 SMC STRATEGY ACTIVE")
        print(f"Press Ctrl+C to shutdown...\n")
        
        last_analysis_time = {}
        analysis_interval = 10  # Analyze every 10 seconds for active monitoring
        
        try:
            while self.running:
                current_time = time.time()
                
                # Refresh tradeable symbols every 10 minutes
                if not tradeable_symbols or (current_time % 600 < 30):
                    tradeable_symbols = self.smc_strategy.get_tradeable_symbols()
                    if tradeable_symbols:
                        print(f"\n✅ Tradeable symbols updated: {', '.join(tradeable_symbols)}")
                
                if not tradeable_symbols:
                    print("\n⏳ No tradeable symbols available. Waiting...")
                    time.sleep(60)  # Wait 1 minute if no symbols
                    continue
                
                # Analyze each tradeable symbol
                for symbol in tradeable_symbols:
                    # Check if it's time to analyze this symbol
                    last_time = last_analysis_time.get(symbol, 0)
                    if current_time - last_time < analysis_interval:
                        continue
                    
                    last_analysis_time[symbol] = current_time
                    print(f"\n🔍 Analyzing {symbol}...")
                    
                    try:
                        # Get multi-timeframe candles
                        candles_by_tf = {}
                        
                        # H4 candles
                        h4_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 100)
                        if h4_rates is not None:
                            candles_by_tf["H4"] = [
                                {'open': float(r['open']), 'high': float(r['high']),
                                 'low': float(r['low']), 'close': float(r['close'])}
                                for r in h4_rates
                            ]
                        
                        # H1 candles
                        h1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
                        if h1_rates is not None:
                            candles_by_tf["H1"] = [
                                {'open': float(r['open']), 'high': float(r['high']),
                                 'low': float(r['low']), 'close': float(r['close'])}
                                for r in h1_rates
                            ]
                        
                        # M15 candles
                        m15_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
                        if m15_rates is not None:
                            candles_by_tf["M15"] = [
                                {'open': float(r['open']), 'high': float(r['high']),
                                 'low': float(r['low']), 'close': float(r['close'])}
                                for r in m15_rates
                            ]
                        
                        # M5 candles
                        m5_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 100)
                        if m5_rates is not None:
                            candles_by_tf["M5"] = [
                                {'open': float(r['open']), 'high': float(r['high']),
                                 'low': float(r['low']), 'close': float(r['close'])}
                                for r in m5_rates
                            ]
                        
                        # Get current price
                        tick = mt5.symbol_info_tick(symbol)
                        if not tick:
                            continue
                        
                        current_price = (tick.bid + tick.ask) / 2
                        
                        # Analyze for signals
                        signal = self.smc_strategy.signal_generator.analyze_setup(
                            symbol,
                            candles_by_tf,
                            current_price
                        )
                        
                        if signal:
                            print(f"\n🎯 SMC Signal: {symbol} {signal.direction} ({signal.order_type})")
                            logger.info(f"SMC Signal: {symbol} {signal.direction}")
                            self.smc_strategy.log_signal(signal)
                            
                            # Check if we already have pending orders for this symbol
                            existing_orders = [o for o in self.smc_strategy.pending_order_manager.get_pending_orders() 
                                             if o.symbol == symbol]
                            
                            if len(existing_orders) >= self.smc_strategy.pending_order_manager.max_pending_per_symbol:
                                print(f"⚠️  Max pending orders reached for {symbol}")
                                logger.info(f"Max pending orders reached for {symbol}")
                            else:
                                # Calculate position size
                                account_info = self.connection_manager.get_account_info()
                                if account_info:
                                    # Simple position sizing (can be improved)
                                    risk_amount = account_info.equity * (self.risk_percent / 100)
                                    risk_pips = abs(signal.entry_price - signal.stop_loss)
                                    
                                    symbol_info = mt5.symbol_info(symbol)
                                    if symbol_info:
                                        # Calculate lot size based on risk
                                        pip_value = symbol_info.trade_tick_value
                                        if risk_pips > 0:
                                            lot_size = risk_amount / (risk_pips * pip_value * 10)
                                            lot_size = min(lot_size, symbol_info.volume_max)
                                            lot_size = max(lot_size, symbol_info.volume_min)
                                            
                                            # Round to step
                                            lot_size = round(lot_size / symbol_info.volume_step) * symbol_info.volume_step
                                            
                                            print(f"💰 Position size: {lot_size} lots (Risk: ${risk_amount:.2f})")
                                            logger.info(f"Calculated lot size: {lot_size} for {symbol}")
                                            
                                            # Place pending order
                                            ticket = None
                                            if signal.order_type == "BUY_LIMIT":
                                                ticket = self.smc_strategy.pending_order_manager.place_buy_limit(
                                                    symbol, signal.entry_price, signal.stop_loss,
                                                    signal.take_profit, lot_size
                                                )
                                            elif signal.order_type == "SELL_LIMIT":
                                                ticket = self.smc_strategy.pending_order_manager.place_sell_limit(
                                                    symbol, signal.entry_price, signal.stop_loss,
                                                    signal.take_profit, lot_size
                                                )
                                            elif signal.order_type == "BUY_STOP":
                                                ticket = self.smc_strategy.pending_order_manager.place_buy_stop(
                                                    symbol, signal.entry_price, signal.stop_loss,
                                                    signal.take_profit, lot_size
                                                )
                                            elif signal.order_type == "SELL_STOP":
                                                ticket = self.smc_strategy.pending_order_manager.place_sell_stop(
                                                    symbol, signal.entry_price, signal.stop_loss,
                                                    signal.take_profit, lot_size
                                                )
                                            
                                            if ticket:
                                                print(f"✅ Pending order placed: Ticket #{ticket}")
                                            else:
                                                print(f"❌ Failed to place pending order")
                                            
                                            self.smc_strategy.log_trade_execution(signal, ticket)
                                        else:
                                            logger.error(f"Invalid risk calculation for {symbol}")
                                    else:
                                        logger.error(f"Could not get symbol info for {symbol}")
                                else:
                                    logger.error("Could not get account info")
                        else:
                            logger.info(f"No signal generated for {symbol}")
                        
                        # Perform analysis and display status
                        if "H1" in candles_by_tf:
                            analysis = self.smc_strategy.analyze_symbol(symbol, candles_by_tf["H1"], "H1")
                            status = self.smc_strategy.display_status(symbol, analysis)
                            print(status)
                    
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
                
                # Manage pending orders
                if self.smc_strategy:
                    self.smc_strategy.pending_order_manager.manage_pending_orders()
                
                # Display pending orders
                pending_orders = self.smc_strategy.pending_order_manager.get_pending_orders()
                if pending_orders:
                    print(f"\n⏳ Active Pending Orders: {len(pending_orders)}")
                    for order in pending_orders:
                        print(f"   • {order.symbol} {order.order_type} @ {order.entry_price:.2f} (Ticket: {order.ticket})")
                else:
                    print(f"\n⏳ No pending orders")
                
                # Sleep before next iteration
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.running = False
    
    def shutdown_sequence(self) -> None:
        """Execute graceful shutdown."""
        logger.info("Starting shutdown sequence")
        
        # Get pending orders
        if self.smc_strategy:
            pending_orders = self.smc_strategy.pending_order_manager.get_pending_orders()
            
            if pending_orders:
                print(f"\n{len(pending_orders)} pending order(s) found:")
                for order in pending_orders:
                    print(f"  - {order.symbol} {order.order_type} @ {order.entry_price}")
                
                cancel_all = input("\nCancel all pending orders before exit? (yes/no): ").lower()
                
                if cancel_all in ['yes', 'y']:
                    logger.info("Cancelling all pending orders...")
                    for order in pending_orders:
                        self.smc_strategy.pending_order_manager.cancel_pending_order(order.ticket)
                    logger.info(f"Cancelled {len(pending_orders)} order(s)")
        
        # Disconnect from MT5
        self.connection_manager.disconnect()
        logger.info("Disconnected from MT5")
        logger.info("Shutdown complete")
    
    def run(self) -> None:
        """Main entry point."""
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


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SMC AUTO TRADER - Smart Money Concepts Strategy")
    print("="*60)
    
    controller = SMCController()
    controller.run()
