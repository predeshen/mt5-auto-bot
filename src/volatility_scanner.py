"""Volatility Scanner for analyzing trading instruments."""

import MetaTrader5 as mt5
from typing import List, Optional
from datetime import datetime
from src.models import InstrumentVolatility


class VolatilityScanner:
    """Analyzes and ranks trading instruments by volatility."""
    
    def __init__(self, min_volatility_threshold: float = 0.001):
        self.min_volatility_threshold = min_volatility_threshold
    
    def get_available_symbols(self) -> List[str]:
        """
        Get list of available trading symbols from MT5.
        
        Returns:
            List of symbol names
        """
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
        
        # Filter for tradeable symbols (visible or not - we'll enable them if needed)
        available = []
        for s in symbols:
            if s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                # Try to enable symbol if not visible
                if not s.visible:
                    mt5.symbol_select(s.name, True)
                available.append(s.name)
        
        return available
    
    def calculate_volatility(self, symbol: str, periods: int = 20) -> float:
        """
        Calculate volatility using Average True Range (ATR).
        
        Args:
            symbol: Trading symbol
            periods: Number of periods for ATR calculation
            
        Returns:
            Normalized volatility score (ATR / current price)
        """
        # Get recent candle data
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, periods + 1)
        
        if rates is None or len(rates) < periods + 1:
            return 0.0
        
        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(rates)):
            high = rates[i]['high']
            low = rates[i]['low']
            prev_close = rates[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Calculate ATR (simple moving average of TR)
        if not true_ranges:
            return 0.0
        
        atr = sum(true_ranges) / len(true_ranges)
        current_price = rates[-1]['close']
        
        # Normalize by current price for cross-instrument comparison
        if current_price > 0:
            return atr / current_price
        
        return 0.0
    
    def scan_instruments(self, symbols: Optional[List[str]] = None, timeframe: str = "5m") -> List[InstrumentVolatility]:
        """
        Scan and analyze instruments for volatility.
        
        Args:
            symbols: List of symbols to scan (None = scan all available)
            timeframe: Timeframe for analysis (currently only 5m supported)
            
        Returns:
            List of InstrumentVolatility objects
        """
        if symbols is None:
            symbols = self.get_available_symbols()
        
        results = []
        
        for symbol in symbols:
            try:
                # Get current price
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    continue
                
                current_price = tick.ask
                if current_price == 0:
                    current_price = tick.bid
                if current_price == 0:
                    continue
                
                # Calculate volatility
                volatility = self.calculate_volatility(symbol, periods=20)
                
                # Filter out low volatility instruments
                if volatility < self.min_volatility_threshold:
                    continue
                
                # Calculate ATR for display
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 21)
                atr = 0.0
                if rates is not None and len(rates) >= 21:
                    true_ranges = []
                    for i in range(1, len(rates)):
                        high = rates[i]['high']
                        low = rates[i]['low']
                        prev_close = rates[i-1]['close']
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        true_ranges.append(tr)
                    atr = sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
                
                results.append(InstrumentVolatility(
                    symbol=symbol,
                    volatility_score=volatility,
                    current_price=current_price,
                    atr=atr,
                    last_update=datetime.now()
                ))
            except Exception as e:
                # Skip symbols that cause errors
                continue
        
        return results
    
    def rank_by_volatility(self, instruments: List[InstrumentVolatility]) -> List[InstrumentVolatility]:
        """
        Sort instruments by volatility score in descending order.
        
        Args:
            instruments: List of instruments to rank
            
        Returns:
            Sorted list (highest volatility first)
        """
        return sorted(instruments, key=lambda x: x.volatility_score, reverse=True)
