"""Data models for MT5 Auto Scalper application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AccountInfo:
    """Account information from MT5."""
    account_number: int
    equity: float
    balance: float
    margin: float
    free_margin: float
    currency: str


@dataclass
class InstrumentVolatility:
    """Volatility information for a trading instrument."""
    symbol: str
    volatility_score: float
    current_price: float
    atr: float
    last_update: datetime


@dataclass
class Signal:
    """Trading signal with entry/exit information."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime
    confidence: float  # 0.0 to 1.0
    reason: str  # e.g., "RSI_OVERSOLD_BREAKOUT"


@dataclass
class Position:
    """Open trading position."""
    ticket: int
    symbol: str
    direction: str
    volume: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    profit: float
    open_time: datetime


@dataclass
class TradeResult:
    """Result of a closed trade."""
    ticket: int
    symbol: str
    direction: str
    volume: float
    entry_price: float
    exit_price: float
    profit: float
    open_time: datetime
    close_time: datetime
    exit_reason: str


@dataclass
class Credentials:
    """MT5 connection credentials."""
    account: int
    password: str
    server: str


@dataclass
class TradingParameters:
    """Trading configuration parameters."""
    max_open_positions: int
    risk_percent: float
    profit_target_atr_multiplier: float = 1.5
    stop_loss_atr_multiplier: float = 1.0
    trailing_stop_enabled: bool = True

    def validate(self) -> bool:
        """Validate trading parameters."""
        if self.max_open_positions <= 0:
            raise ValueError("max_open_positions must be a positive integer")
        if self.risk_percent <= 0 or self.risk_percent > 100:
            raise ValueError("risk_percent must be between 0 and 100")
        if self.profit_target_atr_multiplier <= 0:
            raise ValueError("profit_target_atr_multiplier must be positive")
        if self.stop_loss_atr_multiplier <= 0:
            raise ValueError("stop_loss_atr_multiplier must be positive")
        return True
