"""Display Manager for console output and user input."""

import getpass
from datetime import datetime
from typing import List
from src.models import (
    AccountInfo, Credentials, TradingParameters,
    InstrumentVolatility, Position, TradeResult
)


class DisplayManager:
    """Handles all console output formatting and user input."""
    
    def show_welcome(self) -> None:
        """Display welcome banner."""
        print("=" * 60)
        print("MT5 AUTO SCALPER".center(60))
        print("Automated Scalping Trading System".center(60))
        print("=" * 60)
        print()
    
    def prompt_account_selection(self, accounts: dict) -> str:
        """
        Prompt user to select from saved accounts or enter custom.
        
        Args:
            accounts: Dictionary of saved accounts
            
        Returns:
            Selected account key or 'custom'
        """
        print("\nMT5 Account Selection")
        print("-" * 40)
        
        # Display saved accounts
        account_keys = list(accounts.keys())
        for idx, key in enumerate(account_keys, 1):
            acc = accounts[key]
            print(f"{idx}. {acc['name']} (Account: {acc['account']})")
        
        print(f"{len(account_keys) + 1}. Enter custom credentials")
        print("-" * 40)
        
        while True:
            try:
                choice = int(input("Select account (number): "))
                if 1 <= choice <= len(account_keys):
                    return account_keys[choice - 1]
                elif choice == len(account_keys) + 1:
                    return 'custom'
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def prompt_credentials(self) -> Credentials:
        """
        Prompt user for MT5 credentials.
        
        Returns:
            Credentials object with user input
        """
        print("\nMT5 Connection Setup")
        print("-" * 40)
        
        account = int(input("Account Number: "))
        password = getpass.getpass("Password: ")
        server = input("Server: ")
        
        return Credentials(account=account, password=password, server=server)
    
    def prompt_trading_parameters(self) -> TradingParameters:
        """
        Prompt user for trading configuration parameters.
        
        Returns:
            TradingParameters object with user input
        """
        print("\nTrading Parameters Configuration")
        print("-" * 40)
        
        max_positions = int(input("Maximum Open Positions: "))
        risk_percent = float(input("Risk Percentage per Trade (%): "))
        
        # Ask about progressive sizing
        print("\nProgressive Lot Sizing (Martingale)")
        print("After each win: 0.01 -> 0.02 -> 0.04 -> 0.08 -> 0.16 -> 0.32...")
        print("Grows unlimited based on equity until a loss")
        print("After a loss: Reset to 0.01 lots")
        progressive = input("Enable progressive sizing? (yes/no): ").lower() in ['yes', 'y']
        
        params = TradingParameters(
            max_open_positions=max_positions,
            risk_percent=risk_percent
        )
        params.progressive_sizing = progressive
        
        return params
    
    def display_parameter_summary(self, params: TradingParameters) -> bool:
        """
        Display trading parameters summary and request confirmation.
        
        Args:
            params: Trading parameters to display
            
        Returns:
            True if user confirms, False otherwise
        """
        print("\nTrading Parameters Summary")
        print("-" * 40)
        print(f"Maximum Open Positions: {params.max_open_positions}")
        print(f"Risk per Trade: {params.risk_percent}%")
        print(f"Profit Target: 2.0x ATR (wider targets)")
        print(f"Stop Loss: 1.5x ATR (wider stops)")
        print(f"Trailing Stop: Enabled")
        print(f"Progressive Sizing: {'Enabled' if getattr(params, 'progressive_sizing', False) else 'Disabled'}")
        print(f"Strategy: Momentum-only (no reversals)")
        print("-" * 40)
        
        confirmation = input("Confirm parameters? (yes/no): ").lower()
        return confirmation in ['yes', 'y']
    
    def display_account_info(self, info: AccountInfo) -> None:
        """
        Display account information with formatted equity.
        
        Args:
            info: Account information to display
        """
        print("\nAccount Information")
        print("-" * 40)
        print(f"Account: {info.account_number}")
        print(f"Equity: {info.equity:,.2f} {info.currency}")
        print(f"Balance: {info.balance:,.2f} {info.currency}")
        print(f"Free Margin: {info.free_margin:,.2f} {info.currency}")
        print("-" * 40)
    
    def display_instruments(self, instruments: List[InstrumentVolatility]) -> None:
        """
        Display ranked list of high-volatility instruments.
        
        Args:
            instruments: List of instruments with volatility data
        """
        print("\nHigh Volatility Instruments")
        print("-" * 60)
        print(f"{'Rank':<6} {'Symbol':<12} {'Volatility':<12} {'Price':<12}")
        print("-" * 60)
        
        for idx, inst in enumerate(instruments, 1):
            print(f"{idx:<6} {inst.symbol:<12} {inst.volatility_score:<12.4f} {inst.current_price:<12.5f}")
        
        print("-" * 60)
    
    def display_trade_opened(self, position: Position) -> None:
        """
        Display trade opening details.
        
        Args:
            position: Opened position details
        """
        timestamp = position.open_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] TRADE OPENED")
        print(f"  Symbol: {position.symbol}")
        print(f"  Direction: {position.direction}")
        print(f"  Volume: {position.volume}")
        print(f"  Entry Price: {position.entry_price:.5f}")
        print(f"  Stop Loss: {position.stop_loss:.5f}")
        print(f"  Take Profit: {position.take_profit:.5f}")
    
    def display_trade_closed(self, result: TradeResult) -> None:
        """
        Display trade closing details.
        
        Args:
            result: Closed trade result
        """
        timestamp = result.close_time.strftime("%Y-%m-%d %H:%M:%S")
        profit_sign = "+" if result.profit >= 0 else ""
        print(f"\n[{timestamp}] TRADE CLOSED")
        print(f"  Symbol: {result.symbol}")
        print(f"  Direction: {result.direction}")
        print(f"  Entry: {result.entry_price:.5f}")
        print(f"  Exit: {result.exit_price:.5f}")
        print(f"  Profit: {profit_sign}{result.profit:.2f}")
        print(f"  Reason: {result.exit_reason}")
    
    def display_position_count(self, current: int, maximum: int) -> None:
        """
        Display current position count vs maximum.
        
        Args:
            current: Current number of open positions
            maximum: Maximum allowed positions
        """
        print(f"Open Positions: {current}/{maximum}")
    
    def display_error(self, message: str) -> None:
        """
        Display error message.
        
        Args:
            message: Error message to display
        """
        print(f"\n[ERROR] {message}")
    
    def update_status_line(self, status: str) -> None:
        """
        Update status line (for real-time updates).
        
        Args:
            status: Status message to display
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status}", end='\r')
