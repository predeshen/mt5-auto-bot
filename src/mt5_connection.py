"""MT5 Connection Manager for handling MT5 API connections."""

import MetaTrader5 as mt5
import time
import asyncio
from typing import Optional, Callable, List
from datetime import datetime
from src.models import AccountInfo, Credentials


class MT5ConnectionManager:
    """Manages MT5 connection lifecycle and reconnection logic."""
    
    def __init__(self):
        self._connected = False
        self._credentials: Optional[Credentials] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._connection_listeners: List[Callable[[bool], None]] = []
        self._last_heartbeat: Optional[datetime] = None
    
    def connect(self, account: int, password: str, server: str) -> bool:
        """
        Establish connection to MT5.
        
        Args:
            account: MT5 account number
            password: MT5 account password
            server: MT5 server address
            
        Returns:
            True if connection successful, False otherwise
        """
        # Store credentials for reconnection
        self._credentials = Credentials(account=account, password=password, server=server)
        
        # Initialize MT5
        if not mt5.initialize():
            print(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Attempt login
        if not mt5.login(account, password=password, server=server):
            print(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        self._connected = True
        self._last_heartbeat = datetime.now()
        self._notify_connection_state(True)
        return True
    
    def disconnect(self) -> None:
        """Disconnect from MT5."""
        if self._connected:
            self.stop_heartbeat_monitor()
            mt5.shutdown()
            self._connected = False
            self._notify_connection_state(False)
    
    def is_connected(self) -> bool:
        """Check if currently connected to MT5."""
        return self._connected and mt5.terminal_info() is not None
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """
        Retrieve account information from MT5.
        
        Returns:
            AccountInfo object or None if retrieval fails
        """
        if not self.is_connected():
            return None
        
        account_info = mt5.account_info()
        if account_info is None:
            return None
        
        return AccountInfo(
            account_number=account_info.login,
            equity=account_info.equity,
            balance=account_info.balance,
            margin=account_info.margin,
            free_margin=account_info.margin_free,
            currency=account_info.currency
        )
    
    def reconnect(self, max_attempts: int = 5) -> bool:
        """
        Attempt to reconnect to MT5 with exponential backoff.
        
        Args:
            max_attempts: Maximum number of reconnection attempts
            
        Returns:
            True if reconnection successful, False otherwise
        """
        if self._credentials is None:
            return False
        
        for attempt in range(max_attempts):
            print(f"Reconnection attempt {attempt + 1}/{max_attempts}...")
            
            # Disconnect first
            self.disconnect()
            
            # Wait with exponential backoff
            if attempt > 0:
                wait_time = min(2 ** attempt, 30)  # Cap at 30 seconds
                time.sleep(wait_time)
            
            # Attempt reconnection
            if self.connect(
                self._credentials.account,
                self._credentials.password,
                self._credentials.server
            ):
                print("Reconnection successful!")
                return True
        
        print(f"Reconnection failed after {max_attempts} attempts")
        return False
    
    def add_connection_listener(self, listener: Callable[[bool], None]) -> None:
        """
        Add a listener for connection state changes.
        
        Args:
            listener: Callback function that receives connection state (True/False)
        """
        self._connection_listeners.append(listener)
    
    def _notify_connection_state(self, connected: bool) -> None:
        """Notify all listeners of connection state change."""
        for listener in self._connection_listeners:
            try:
                listener(connected)
            except Exception as e:
                print(f"Error notifying connection listener: {e}")
    
    async def _heartbeat_loop(self, interval: int = 5) -> None:
        """
        Monitor connection health with periodic checks.
        
        Args:
            interval: Seconds between heartbeat checks
        """
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Check if still connected
                if self._connected:
                    if not self.is_connected():
                        print("Connection lost! Attempting reconnection...")
                        self._connected = False
                        self._notify_connection_state(False)
                        
                        # Attempt automatic reconnection
                        if self.reconnect():
                            self._notify_connection_state(True)
                    else:
                        self._last_heartbeat = datetime.now()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Heartbeat monitor error: {e}")
    
    def start_heartbeat_monitor(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """
        Start monitoring connection health in background.
        
        Args:
            loop: Event loop to run the heartbeat monitor in
        """
        if self._heartbeat_task is None or self._heartbeat_task.done():
            if loop is None:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No running loop, create task when loop starts
                    return
            
            self._heartbeat_task = loop.create_task(self._heartbeat_loop())
    
    def stop_heartbeat_monitor(self) -> None:
        """Stop the heartbeat monitoring task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
