"""Smart Money Concepts (SMC) Strategy Module.

This module implements institutional trading methodology based on:
- Fair Value Gaps (FVG)
- Order Blocks and Breaker Blocks
- Liquidity Sweeps
- Market Structure (BOS/CHoCH)
- Multi-timeframe Confluence
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional, Dict
from src.smc_config import SMC_CONFIG
from src.logger import logger


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class FVG:
    """Fair Value Gap - price imbalance zone."""
    timeframe: str  # "H4", "H1", "M15", "M5"
    direction: str  # "BULLISH" or "BEARISH"
    high: float
    low: float
    equilibrium: float  # 50% level
    created_at: datetime
    filled: bool
    candle_index: int


@dataclass
class OrderBlock:
    """Order Block - institutional supply/demand zone."""
    timeframe: str
    direction: str  # "BULLISH" or "BEARISH"
    high: float
    low: float
    entry_price: float  # 50% level
    created_at: datetime
    valid: bool
    strength: float  # Based on subsequent move size


@dataclass
class BreakerBlock:
    """Breaker Block - failed order block that becomes opposite zone."""
    original_ob: OrderBlock
    direction: str  # Opposite of original OB
    high: float
    low: float
    entry_price: float
    created_at: datetime


@dataclass
class LiquidityLevel:
    """Liquidity level - swing high/low where stops accumulate."""
    price: float
    type: str  # "BUYSIDE" or "SELLSIDE"
    strength: int  # Number of touches
    swept: bool
    sweep_time: Optional[datetime] = None


@dataclass
class MarketStructure:
    """Market structure - trend identification."""
    trend: str  # "UPTREND", "DOWNTREND", "RANGING"
    swing_highs: List[float] = field(default_factory=list)
    swing_lows: List[float] = field(default_factory=list)
    last_bos: Optional[datetime] = None
    last_choch: Optional[datetime] = None


@dataclass
class ConfluenceZone:
    """Confluence zone - multiple SMC components aligning."""
    high: float
    low: float
    entry_price: float
    components: List[str]  # ["H4_FVG", "H1_FVG", "ORDER_BLOCK"]
    confidence: float  # 0.0 to 1.0
    direction: str  # "BULLISH" or "BEARISH"


@dataclass
class SMCSignal:
    """SMC trading signal with pending order details."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    order_type: str  # "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    setup_type: str  # "FVG_ENTRY", "OB_ENTRY", "CONFLUENCE", "LIQUIDITY_SWEEP"
    timeframe_bias: Dict[str, str]  # {"H4": "BULLISH", "H1": "BULLISH"}
    zones: List[ConfluenceZone]
    timestamp: datetime


@dataclass
class PendingOrder:
    """Pending order placed at SMC zone."""
    ticket: int
    symbol: str
    order_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    volume: float
    placed_at: datetime
    expires_at: datetime
    smc_setup: str


@dataclass
class SymbolMapping:
    """Symbol mapping from standard name to broker-specific symbol."""
    standard_name: str  # "US30", "XAUUSD", etc.
    broker_symbol: str  # Actual broker symbol
    is_available: bool
    point_value: float  # For pip calculation
    min_lot: float
    max_lot: float


@dataclass
class TradingSession:
    """Trading session schedule for a symbol."""
    symbol: str
    open_time: time  # Daily open time (GMT)
    close_time: time  # Daily close time (GMT)
    break_start: Optional[time]  # Daily break start
    break_end: Optional[time]  # Daily break end
    trading_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 6])  # 0=Monday, 6=Sunday


# ============================================================================
# FVG DETECTOR
# ============================================================================

class FVGDetector:
    """Detects Fair Value Gaps across multiple timeframes."""
    
    def __init__(self):
        self.min_gap_size = SMC_CONFIG["fvg_min_size_pips"]
        self.cached_fvgs: Dict[str, List[FVG]] = {}  # Cache by symbol_timeframe
        logger.info("FVGDetector initialized")
    
    def detect_fvgs(self, candles: List[dict], timeframe: str) -> List[FVG]:
        """
        Detect Fair Value Gaps in price data.
        
        Args:
            candles: List of OHLC candles
            timeframe: Timeframe string (H4, H1, M15, M5)
            
        Returns:
            List of detected FVGs
        """
        fvgs = []
        
        if len(candles) < 3:
            return fvgs
        
        # Scan for 3-candle FVG patterns
        for i in range(len(candles) - 2):
            candle1 = candles[i]
            candle2 = candles[i + 1]
            candle3 = candles[i + 2]
            
            # Bullish FVG: Candle 1 low > Candle 3 high
            if candle1['low'] > candle3['high']:
                gap_size = candle1['low'] - candle3['high']
                
                fvg = FVG(
                    timeframe=timeframe,
                    direction="BULLISH",
                    high=candle1['low'],
                    low=candle3['high'],
                    equilibrium=(candle1['low'] + candle3['high']) / 2,
                    created_at=datetime.now(),
                    filled=False,
                    candle_index=i
                )
                fvgs.append(fvg)
            
            # Bearish FVG: Candle 1 high < Candle 3 low
            elif candle1['high'] < candle3['low']:
                gap_size = candle3['low'] - candle1['high']
                
                fvg = FVG(
                    timeframe=timeframe,
                    direction="BEARISH",
                    high=candle3['low'],
                    low=candle1['high'],
                    equilibrium=(candle3['low'] + candle1['high']) / 2,
                    created_at=datetime.now(),
                    filled=False,
                    candle_index=i
                )
                fvgs.append(fvg)
        
        logger.info(f"Detected {len(fvgs)} FVGs on {timeframe}")
        return fvgs
    
    def is_fvg_filled(self, fvg: FVG, current_price: float) -> bool:
        """
        Check if FVG has been filled by price.
        
        Args:
            fvg: FVG to check
            current_price: Current market price
            
        Returns:
            True if FVG is filled, False otherwise
        """
        if fvg.direction == "BULLISH":
            # Bullish FVG filled when price drops into/below the gap
            return current_price <= fvg.low
        else:  # BEARISH
            # Bearish FVG filled when price rises into/above the gap
            return current_price >= fvg.high
    
    def get_fvg_entry_price(self, fvg: FVG, direction: str) -> float:
        """
        Get entry price for FVG (typically at the edge).
        
        Args:
            fvg: FVG to get entry price for
            direction: Trade direction ("BUY" or "SELL")
            
        Returns:
            Entry price
        """
        if direction == "BUY":
            return fvg.low  # Enter at bottom of bullish FVG
        else:  # SELL
            return fvg.high  # Enter at top of bearish FVG
    
    def calculate_fvg_equilibrium(self, fvg: FVG) -> float:
        """
        Calculate 50% equilibrium level of FVG.
        
        Args:
            fvg: FVG to calculate equilibrium for
            
        Returns:
            Equilibrium price (50% level)
        """
        return (fvg.high + fvg.low) / 2
    
    def filter_valid_fvgs(self, fvgs: List[FVG]) -> List[FVG]:
        """
        Filter out filled or invalid FVGs.
        
        Args:
            fvgs: List of FVGs to filter
            
        Returns:
            List of valid (unfilled) FVGs
        """
        return [fvg for fvg in fvgs if not fvg.filled]
    
    def update_fvg_status(self, fvgs: List[FVG], current_price: float) -> None:
        """
        Update fill status of FVGs based on current price.
        
        Args:
            fvgs: List of FVGs to update
            current_price: Current market price
        """
        for fvg in fvgs:
            if not fvg.filled:
                fvg.filled = self.is_fvg_filled(fvg, current_price)
    
    def get_nearest_fvg(self, fvgs: List[FVG], current_price: float, 
                        direction: Optional[str] = None) -> Optional[FVG]:
        """
        Get nearest FVG to current price.
        
        Args:
            fvgs: List of FVGs
            current_price: Current market price
            direction: Optional filter by direction ("BULLISH" or "BEARISH")
            
        Returns:
            Nearest FVG or None
        """
        valid_fvgs = self.filter_valid_fvgs(fvgs)
        
        if direction:
            valid_fvgs = [fvg for fvg in valid_fvgs if fvg.direction == direction]
        
        if not valid_fvgs:
            return None
        
        # Find nearest by equilibrium distance
        nearest = min(valid_fvgs, key=lambda fvg: abs(fvg.equilibrium - current_price))
        return nearest
    
    def detect_volume_imbalances(self, candles: List[dict], timeframe: str) -> List[FVG]:
        """
        Detect Volume Imbalances (same as FVGs).
        
        Volume Imbalances are unfilled gaps that price tends to revisit.
        They are essentially the same as Fair Value Gaps.
        
        Args:
            candles: List of OHLC candles
            timeframe: Timeframe string
            
        Returns:
            List of Volume Imbalances (FVGs)
        """
        # Volume Imbalances are detected the same way as FVGs
        return self.detect_fvgs(candles, timeframe)
    
    def prioritize_by_distance(self, fvgs: List[FVG], current_price: float) -> List[FVG]:
        """
        Prioritize FVGs by distance to current price (nearest first).
        
        Args:
            fvgs: List of FVGs
            current_price: Current market price
            
        Returns:
            Sorted list of FVGs (nearest first)
        """
        return sorted(fvgs, key=lambda fvg: abs(fvg.equilibrium - current_price))


# ============================================================================
# ORDER BLOCK DETECTOR
# ============================================================================

class OrderBlockDetector:
    """Detects Order Blocks and Breaker Blocks."""
    
    def __init__(self):
        self.min_move_pips = SMC_CONFIG["order_block_min_move"]
        logger.info("OrderBlockDetector initialized")
    
    def detect_order_blocks(self, candles: List[dict]) -> List[OrderBlock]:
        """
        Detect Order Blocks in price data.
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            List of detected Order Blocks
        """
        order_blocks = []
        
        if len(candles) < 5:
            return order_blocks
        
        # Look for significant moves (3+ consecutive candles in same direction)
        for i in range(len(candles) - 4):
            # Check for bullish move (3+ green candles)
            bullish_move = all(
                candles[i + j + 1]['close'] > candles[i + j + 1]['open']
                for j in range(3)
            )
            
            if bullish_move:
                # Last red candle before move is the Order Block
                if candles[i]['close'] < candles[i]['open']:
                    ob = OrderBlock(
                        timeframe="",  # Will be set by caller
                        direction="BULLISH",
                        high=candles[i]['high'],
                        low=candles[i]['low'],
                        entry_price=(candles[i]['high'] + candles[i]['low']) / 2,
                        created_at=datetime.now(),
                        valid=True,
                        strength=candles[i + 3]['close'] - candles[i]['close']
                    )
                    order_blocks.append(ob)
            
            # Check for bearish move (3+ red candles)
            bearish_move = all(
                candles[i + j + 1]['close'] < candles[i + j + 1]['open']
                for j in range(3)
            )
            
            if bearish_move:
                # Last green candle before move is the Order Block
                if candles[i]['close'] > candles[i]['open']:
                    ob = OrderBlock(
                        timeframe="",  # Will be set by caller
                        direction="BEARISH",
                        high=candles[i]['high'],
                        low=candles[i]['low'],
                        entry_price=(candles[i]['high'] + candles[i]['low']) / 2,
                        created_at=datetime.now(),
                        valid=True,
                        strength=candles[i]['close'] - candles[i + 3]['close']
                    )
                    order_blocks.append(ob)
        
        logger.info(f"Detected {len(order_blocks)} Order Blocks")
        return order_blocks
    
    def detect_breaker_blocks(self, order_blocks: List[OrderBlock], 
                             candles: List[dict]) -> List[BreakerBlock]:
        """Detect Breaker Blocks (failed Order Blocks)."""
        breaker_blocks = []
        
        # Check if any Order Blocks have been broken
        for ob in order_blocks:
            if not ob.valid:
                continue
            
            # Check if price broke through the OB
            for candle in candles:
                if ob.direction == "BULLISH":
                    # Bullish OB broken if price closes below low
                    if candle['close'] < ob.low:
                        bb = BreakerBlock(
                            original_ob=ob,
                            direction="BEARISH",  # Opposite
                            high=ob.high,
                            low=ob.low,
                            entry_price=ob.entry_price,
                            created_at=datetime.now()
                        )
                        breaker_blocks.append(bb)
                        ob.valid = False
                        break
                
                elif ob.direction == "BEARISH":
                    # Bearish OB broken if price closes above high
                    if candle['close'] > ob.high:
                        bb = BreakerBlock(
                            original_ob=ob,
                            direction="BULLISH",  # Opposite
                            high=ob.high,
                            low=ob.low,
                            entry_price=ob.entry_price,
                            created_at=datetime.now()
                        )
                        breaker_blocks.append(bb)
                        ob.valid = False
                        break
        
        logger.info(f"Detected {len(breaker_blocks)} Breaker Blocks")
        return breaker_blocks
    
    def get_order_block_entry(self, ob: OrderBlock) -> float:
        """Get entry price for Order Block (50% level)."""
        return ob.entry_price
    
    def is_order_block_valid(self, ob: OrderBlock, current_price: float) -> bool:
        """Check if Order Block is still valid (not broken)."""
        if ob.direction == "BULLISH":
            return current_price >= ob.low
        else:  # BEARISH
            return current_price <= ob.high


# ============================================================================
# MARKET STRUCTURE ANALYZER
# ============================================================================

class MarketStructureAnalyzer:
    """Identifies market structure: BOS, CHoCH, and trend direction."""
    
    def __init__(self):
        self.swing_lookback = 5  # Candles to look back for swing points
        logger.info("MarketStructureAnalyzer initialized")
    
    def identify_structure(self, candles: List[dict]) -> MarketStructure:
        """
        Identify market structure from price data.
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            MarketStructure object
        """
        if len(candles) < self.swing_lookback * 2:
            return MarketStructure(
                trend="RANGING",
                swing_highs=[],
                swing_lows=[],
                last_bos=None,
                last_choch=None
            )
        
        # Find swing highs and lows
        swing_highs = self._find_swing_highs(candles)
        swing_lows = self._find_swing_lows(candles)
        
        # Determine trend
        trend = self._determine_trend(swing_highs, swing_lows)
        
        structure = MarketStructure(
            trend=trend,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            last_bos=None,
            last_choch=None
        )
        
        return structure
    
    def _find_swing_highs(self, candles: List[dict]) -> List[float]:
        """Find swing high points in price data."""
        swing_highs = []
        
        for i in range(self.swing_lookback, len(candles) - self.swing_lookback):
            current_high = candles[i]['high']
            
            # Check if this is a local high
            is_swing_high = True
            for j in range(1, self.swing_lookback + 1):
                if candles[i - j]['high'] >= current_high or candles[i + j]['high'] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append(current_high)
        
        return swing_highs
    
    def _find_swing_lows(self, candles: List[dict]) -> List[float]:
        """Find swing low points in price data."""
        swing_lows = []
        
        for i in range(self.swing_lookback, len(candles) - self.swing_lookback):
            current_low = candles[i]['low']
            
            # Check if this is a local low
            is_swing_low = True
            for j in range(1, self.swing_lookback + 1):
                if candles[i - j]['low'] <= current_low or candles[i + j]['low'] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append(current_low)
        
        return swing_lows
    
    def _determine_trend(self, swing_highs: List[float], swing_lows: List[float]) -> str:
        """
        Determine trend from swing points.
        
        Uptrend: Higher Highs (HH) and Higher Lows (HL)
        Downtrend: Lower Highs (LH) and Lower Lows (LL)
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "RANGING"
        
        # Check for higher highs
        higher_highs = all(swing_highs[i] > swing_highs[i-1] for i in range(1, min(3, len(swing_highs))))
        
        # Check for higher lows
        higher_lows = all(swing_lows[i] > swing_lows[i-1] for i in range(1, min(3, len(swing_lows))))
        
        # Check for lower highs
        lower_highs = all(swing_highs[i] < swing_highs[i-1] for i in range(1, min(3, len(swing_highs))))
        
        # Check for lower lows
        lower_lows = all(swing_lows[i] < swing_lows[i-1] for i in range(1, min(3, len(swing_lows))))
        
        if higher_highs and higher_lows:
            return "UPTREND"
        elif lower_highs and lower_lows:
            return "DOWNTREND"
        else:
            return "RANGING"
    
    def detect_bos(self, candles: List[dict]) -> Optional[datetime]:
        """
        Detect Break of Structure.
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            Datetime of BOS or None
        """
        structure = self.identify_structure(candles)
        
        if structure.trend == "RANGING":
            return None
        
        if len(candles) < 2:
            return None
        
        current_price = candles[-1]['close']
        
        if structure.trend == "UPTREND" and structure.swing_highs:
            # BOS in uptrend: break above previous high
            previous_high = max(structure.swing_highs[:-1]) if len(structure.swing_highs) > 1 else structure.swing_highs[0]
            if current_price > previous_high:
                return datetime.now()
        
        elif structure.trend == "DOWNTREND" and structure.swing_lows:
            # BOS in downtrend: break below previous low
            previous_low = min(structure.swing_lows[:-1]) if len(structure.swing_lows) > 1 else structure.swing_lows[0]
            if current_price < previous_low:
                return datetime.now()
        
        return None
    
    def detect_choch(self, candles: List[dict]) -> Optional[datetime]:
        """
        Detect Change of Character.
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            Datetime of CHoCH or None
        """
        structure = self.identify_structure(candles)
        
        if structure.trend == "RANGING":
            return None
        
        if len(candles) < 2:
            return None
        
        current_price = candles[-1]['close']
        
        if structure.trend == "UPTREND" and structure.swing_lows:
            # CHoCH in uptrend: break below previous HL
            if len(structure.swing_lows) >= 2:
                previous_hl = structure.swing_lows[-2]
                if current_price < previous_hl:
                    return datetime.now()
        
        elif structure.trend == "DOWNTREND" and structure.swing_highs:
            # CHoCH in downtrend: break above previous LH
            if len(structure.swing_highs) >= 2:
                previous_lh = structure.swing_highs[-2]
                if current_price > previous_lh:
                    return datetime.now()
        
        return None
    
    def get_trend_direction(self, structure: MarketStructure) -> str:
        """Get trend direction from market structure."""
        return structure.trend


# ============================================================================
# LIQUIDITY ANALYZER
# ============================================================================

class LiquidityAnalyzer:
    """Detects liquidity sweeps and key liquidity levels."""
    
    def __init__(self):
        self.sweep_threshold_pips = SMC_CONFIG["liquidity_sweep_threshold_pips"]
        logger.info("LiquidityAnalyzer initialized")
    
    def identify_liquidity_levels(self, candles: List[dict]) -> List[LiquidityLevel]:
        """
        Identify liquidity levels (swing highs/lows).
        
        Args:
            candles: List of OHLC candles
            
        Returns:
            List of liquidity levels
        """
        levels = []
        lookback = 5
        
        if len(candles) < lookback * 2:
            return levels
        
        # Find swing highs (buyside liquidity)
        for i in range(lookback, len(candles) - lookback):
            current_high = candles[i]['high']
            
            is_swing_high = True
            for j in range(1, lookback + 1):
                if candles[i - j]['high'] >= current_high or candles[i + j]['high'] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                level = LiquidityLevel(
                    price=current_high,
                    type="BUYSIDE",
                    strength=1,
                    swept=False
                )
                levels.append(level)
        
        # Find swing lows (sellside liquidity)
        for i in range(lookback, len(candles) - lookback):
            current_low = candles[i]['low']
            
            is_swing_low = True
            for j in range(1, lookback + 1):
                if candles[i - j]['low'] <= current_low or candles[i + j]['low'] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                level = LiquidityLevel(
                    price=current_low,
                    type="SELLSIDE",
                    strength=1,
                    swept=False
                )
                levels.append(level)
        
        return levels
    
    def detect_sweep(self, candles: List[dict], level: LiquidityLevel) -> Optional[datetime]:
        """
        Detect if liquidity level has been swept.
        
        Args:
            candles: List of OHLC candles
            level: Liquidity level to check
            
        Returns:
            Datetime of sweep or None
        """
        if len(candles) < 2:
            return None
        
        recent_candles = candles[-5:]  # Check last 5 candles
        
        for candle in recent_candles:
            if level.type == "BUYSIDE":
                # Buyside sweep: price breaks above level then reverses
                if candle['high'] > level.price + (self.sweep_threshold_pips / 10000):
                    # Check if reversed
                    if candle['close'] < level.price:
                        return datetime.now()
            
            elif level.type == "SELLSIDE":
                # Sellside sweep: price breaks below level then reverses
                if candle['low'] < level.price - (self.sweep_threshold_pips / 10000):
                    # Check if reversed
                    if candle['close'] > level.price:
                        return datetime.now()
        
        return None
    
    def is_buyside_liquidity_swept(self, candles: List[dict]) -> bool:
        """Check if buyside liquidity has been swept recently."""
        levels = self.identify_liquidity_levels(candles)
        buyside_levels = [l for l in levels if l.type == "BUYSIDE"]
        
        for level in buyside_levels:
            if self.detect_sweep(candles, level):
                return True
        
        return False
    
    def is_sellside_liquidity_swept(self, candles: List[dict]) -> bool:
        """Check if sellside liquidity has been swept recently."""
        levels = self.identify_liquidity_levels(candles)
        sellside_levels = [l for l in levels if l.type == "SELLSIDE"]
        
        for level in sellside_levels:
            if self.detect_sweep(candles, level):
                return True
        
        return False


# ============================================================================
# MULTI-TIMEFRAME ANALYZER
# ============================================================================

@dataclass
class TimeframeAnalysis:
    """Analysis results for all timeframes."""
    h4_fvgs: List[FVG] = field(default_factory=list)
    h1_fvgs: List[FVG] = field(default_factory=list)
    m15_fvgs: List[FVG] = field(default_factory=list)
    m5_fvgs: List[FVG] = field(default_factory=list)
    h4_structure: Optional[MarketStructure] = None
    h1_structure: Optional[MarketStructure] = None
    h4_bias: str = "NEUTRAL"
    h1_bias: str = "NEUTRAL"


class MultiTimeframeAnalyzer:
    """Coordinates analysis across H4, H1, M15, M5 timeframes."""
    
    def __init__(self, fvg_detector: FVGDetector, structure_analyzer: MarketStructureAnalyzer):
        self.fvg_detector = fvg_detector
        self.structure_analyzer = structure_analyzer
        self.timeframes = SMC_CONFIG["timeframes"]
        logger.info("MultiTimeframeAnalyzer initialized")
    
    def analyze_all_timeframes(self, symbol: str, candles_by_tf: Dict[str, List[dict]]) -> TimeframeAnalysis:
        """
        Analyze all timeframes for a symbol.
        
        Args:
            symbol: Trading symbol
            candles_by_tf: Dictionary mapping timeframe to candles
            
        Returns:
            TimeframeAnalysis object
        """
        analysis = TimeframeAnalysis()
        
        # Analyze H4
        if "H4" in candles_by_tf and candles_by_tf["H4"]:
            analysis.h4_fvgs = self.fvg_detector.detect_fvgs(candles_by_tf["H4"], "H4")
            analysis.h4_structure = self.structure_analyzer.identify_structure(candles_by_tf["H4"])
            analysis.h4_bias = analysis.h4_structure.trend if analysis.h4_structure else "NEUTRAL"
        
        # Analyze H1
        if "H1" in candles_by_tf and candles_by_tf["H1"]:
            analysis.h1_fvgs = self.fvg_detector.detect_fvgs(candles_by_tf["H1"], "H1")
            analysis.h1_structure = self.structure_analyzer.identify_structure(candles_by_tf["H1"])
            analysis.h1_bias = analysis.h1_structure.trend if analysis.h1_structure else "NEUTRAL"
        
        # Analyze M15
        if "M15" in candles_by_tf and candles_by_tf["M15"]:
            analysis.m15_fvgs = self.fvg_detector.detect_fvgs(candles_by_tf["M15"], "M15")
        
        # Analyze M5
        if "M5" in candles_by_tf and candles_by_tf["M5"]:
            analysis.m5_fvgs = self.fvg_detector.detect_fvgs(candles_by_tf["M5"], "M5")
        
        logger.info(f"Multi-timeframe analysis complete for {symbol}")
        return analysis
    
    def get_htf_bias(self, h4_data: Optional[MarketStructure], h1_data: Optional[MarketStructure]) -> str:
        """
        Get higher timeframe bias from H4 and H1.
        
        Priority order:
        1. Both timeframes agree → return agreed direction
        2. H4 has clear trend → return H4 direction (takes priority)
        3. H1 has clear trend while H4 ranging → return H1 direction
        4. Both ranging → return NEUTRAL
        
        Args:
            h4_data: H4 market structure
            h1_data: H1 market structure
            
        Returns:
            "BULLISH", "BEARISH", or "NEUTRAL"
        """
        if not h4_data or not h1_data:
            logger.info("HTF Bias: Missing data (H4 or H1) - returning NEUTRAL")
            return "NEUTRAL"
        
        h4_trend = h4_data.trend
        h1_trend = h1_data.trend
        
        logger.info(f"HTF Bias Calculation: H4={h4_trend}, H1={h1_trend}")
        
        # Both timeframes agree
        if h4_trend == "UPTREND" and h1_trend == "UPTREND":
            logger.info("HTF Bias Decision: BULLISH (both timeframes agree on UPTREND)")
            return "BULLISH"
        elif h4_trend == "DOWNTREND" and h1_trend == "DOWNTREND":
            logger.info("HTF Bias Decision: BEARISH (both timeframes agree on DOWNTREND)")
            return "BEARISH"
        
        # H4 takes priority if it has a clear trend
        if h4_trend == "UPTREND":
            logger.info("HTF Bias Decision: BULLISH (H4 priority - H4 UPTREND)")
            return "BULLISH"
        elif h4_trend == "DOWNTREND":
            logger.info("HTF Bias Decision: BEARISH (H4 priority - H4 DOWNTREND)")
            return "BEARISH"
        
        # H1 fallback: if H4 is ranging but H1 has a clear trend
        if h4_trend == "RANGING":
            if h1_trend == "UPTREND":
                logger.info("HTF Bias Decision: BULLISH (H1 fallback - H4 RANGING, H1 UPTREND)")
                return "BULLISH"
            elif h1_trend == "DOWNTREND":
                logger.info("HTF Bias Decision: BEARISH (H1 fallback - H4 RANGING, H1 DOWNTREND)")
                return "BEARISH"
        
        # Both ranging or no clear direction
        logger.info("HTF Bias Decision: NEUTRAL (both timeframes ranging or unclear)")
        return "NEUTRAL"
    
    def find_confluence_zones(self, tf_analysis: TimeframeAnalysis) -> List[ConfluenceZone]:
        """
        Find confluence zones where multiple timeframe FVGs overlap.
        
        Args:
            tf_analysis: Timeframe analysis results
            
        Returns:
            List of confluence zones
        """
        confluence_zones = []
        
        # Check H4 and H1 FVG alignment
        for h4_fvg in tf_analysis.h4_fvgs:
            for h1_fvg in tf_analysis.h1_fvgs:
                if self.check_fvg_alignment(h4_fvg, h1_fvg):
                    # Create confluence zone
                    zone = ConfluenceZone(
                        high=min(h4_fvg.high, h1_fvg.high),
                        low=max(h4_fvg.low, h1_fvg.low),
                        entry_price=(min(h4_fvg.high, h1_fvg.high) + max(h4_fvg.low, h1_fvg.low)) / 2,
                        components=["H4_FVG", "H1_FVG"],
                        confidence=0.8,
                        direction=h4_fvg.direction
                    )
                    confluence_zones.append(zone)
        
        logger.info(f"Found {len(confluence_zones)} confluence zones")
        return confluence_zones
    
    def check_fvg_alignment(self, h4_fvg: FVG, h1_fvg: FVG) -> bool:
        """
        Check if H4 and H1 FVGs align (overlap).
        
        Args:
            h4_fvg: H4 FVG
            h1_fvg: H1 FVG
            
        Returns:
            True if FVGs overlap
        """
        # Check if same direction
        if h4_fvg.direction != h1_fvg.direction:
            return False
        
        # Check if price ranges overlap
        overlap = not (h4_fvg.high < h1_fvg.low or h1_fvg.high < h4_fvg.low)
        return overlap
    
    def calculate_equilibrium(self, high: float, low: float) -> float:
        """Calculate 50% equilibrium level."""
        return (high + low) / 2
    
    def classify_zone(self, current_price: float, equilibrium: float) -> str:
        """
        Classify current price as Premium or Discount.
        
        Args:
            current_price: Current market price
            equilibrium: 50% equilibrium level
            
        Returns:
            "PREMIUM" or "DISCOUNT"
        """
        if current_price > equilibrium:
            return "PREMIUM"
        else:
            return "DISCOUNT"
    
    def get_bias_from_zone(self, zone: str) -> str:
        """
        Get trading bias from zone classification.
        
        Args:
            zone: "PREMIUM" or "DISCOUNT"
            
        Returns:
            "SELL" or "BUY"
        """
        if zone == "PREMIUM":
            return "SELL"
        else:  # DISCOUNT
            return "BUY"


# ============================================================================
# PENDING ORDER MANAGER
# ============================================================================

class PendingOrderManager:
    """Manages pending orders at SMC zones."""
    
    def __init__(self, mt5_connection=None):
        self.mt5_connection = mt5_connection
        self.pending_orders: Dict[int, PendingOrder] = {}
        self.max_pending_per_symbol = SMC_CONFIG["max_pending_orders_per_symbol"]
        self.expiry_hours = SMC_CONFIG["pending_order_expiry_hours"]
        logger.info("PendingOrderManager initialized")
    
    def place_buy_limit(self, symbol: str, price: float, sl: float, tp: float, volume: float) -> Optional[int]:
        """
        Place Buy Limit order (buy when price drops to level).
        
        Args:
            symbol: Trading symbol
            price: Entry price (below current price)
            sl: Stop loss
            tp: Take profit
            volume: Lot size
            
        Returns:
            Order ticket or None
        """
        import MetaTrader5 as mt5
        from datetime import timedelta
        
        if not self.mt5_connection:
            logger.error("No MT5 connection available")
            return None
        
        # Check if we can place more orders for this symbol
        symbol_orders = [o for o in self.pending_orders.values() if o.symbol == symbol]
        if len(symbol_orders) >= self.max_pending_per_symbol:
            logger.warning(f"Max pending orders reached for {symbol}")
            return None
        
        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "SMC Buy Limit",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": int((datetime.now() + timedelta(hours=self.expiry_hours)).timestamp())
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            # Store pending order
            pending_order = PendingOrder(
                ticket=result.order,
                symbol=symbol,
                order_type="BUY_LIMIT",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                volume=volume,
                placed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.expiry_hours),
                smc_setup="FVG_ENTRY"
            )
            self.pending_orders[result.order] = pending_order
            logger.info(f"Buy Limit placed: {symbol} @ {price}, ticket {result.order}")
            return result.order
        else:
            logger.error(f"Failed to place Buy Limit: {result.comment if result else 'No result'}")
            return None
    
    def place_sell_limit(self, symbol: str, price: float, sl: float, tp: float, volume: float) -> Optional[int]:
        """
        Place Sell Limit order (sell when price rises to level).
        
        Args:
            symbol: Trading symbol
            price: Entry price (above current price)
            sl: Stop loss
            tp: Take profit
            volume: Lot size
            
        Returns:
            Order ticket or None
        """
        import MetaTrader5 as mt5
        from datetime import timedelta
        
        if not self.mt5_connection:
            logger.error("No MT5 connection available")
            return None
        
        # Check if we can place more orders for this symbol
        symbol_orders = [o for o in self.pending_orders.values() if o.symbol == symbol]
        if len(symbol_orders) >= self.max_pending_per_symbol:
            logger.warning(f"Max pending orders reached for {symbol}")
            return None
        
        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "SMC Sell Limit",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": int((datetime.now() + timedelta(hours=self.expiry_hours)).timestamp())
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            # Store pending order
            pending_order = PendingOrder(
                ticket=result.order,
                symbol=symbol,
                order_type="SELL_LIMIT",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                volume=volume,
                placed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.expiry_hours),
                smc_setup="FVG_ENTRY"
            )
            self.pending_orders[result.order] = pending_order
            logger.info(f"Sell Limit placed: {symbol} @ {price}, ticket {result.order}")
            return result.order
        else:
            logger.error(f"Failed to place Sell Limit: {result.comment if result else 'No result'}")
            return None
    
    def place_buy_stop(self, symbol: str, price: float, sl: float, tp: float, volume: float) -> Optional[int]:
        """
        Place Buy Stop order (buy when price breaks above level).
        
        Args:
            symbol: Trading symbol
            price: Entry price (above current price)
            sl: Stop loss
            tp: Take profit
            volume: Lot size
            
        Returns:
            Order ticket or None
        """
        import MetaTrader5 as mt5
        from datetime import timedelta
        
        if not self.mt5_connection:
            logger.error("No MT5 connection available")
            return None
        
        symbol_orders = [o for o in self.pending_orders.values() if o.symbol == symbol]
        if len(symbol_orders) >= self.max_pending_per_symbol:
            logger.warning(f"Max pending orders reached for {symbol}")
            return None
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "SMC Buy Stop",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": int((datetime.now() + timedelta(hours=self.expiry_hours)).timestamp())
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            pending_order = PendingOrder(
                ticket=result.order,
                symbol=symbol,
                order_type="BUY_STOP",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                volume=volume,
                placed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.expiry_hours),
                smc_setup="BOS_BREAKOUT"
            )
            self.pending_orders[result.order] = pending_order
            logger.info(f"Buy Stop placed: {symbol} @ {price}, ticket {result.order}")
            return result.order
        else:
            logger.error(f"Failed to place Buy Stop: {result.comment if result else 'No result'}")
            return None
    
    def place_sell_stop(self, symbol: str, price: float, sl: float, tp: float, volume: float) -> Optional[int]:
        """
        Place Sell Stop order (sell when price breaks below level).
        
        Args:
            symbol: Trading symbol
            price: Entry price (below current price)
            sl: Stop loss
            tp: Take profit
            volume: Lot size
            
        Returns:
            Order ticket or None
        """
        import MetaTrader5 as mt5
        from datetime import timedelta
        
        if not self.mt5_connection:
            logger.error("No MT5 connection available")
            return None
        
        symbol_orders = [o for o in self.pending_orders.values() if o.symbol == symbol]
        if len(symbol_orders) >= self.max_pending_per_symbol:
            logger.warning(f"Max pending orders reached for {symbol}")
            return None
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL_STOP,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "SMC Sell Stop",
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": int((datetime.now() + timedelta(hours=self.expiry_hours)).timestamp())
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            pending_order = PendingOrder(
                ticket=result.order,
                symbol=symbol,
                order_type="SELL_STOP",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                volume=volume,
                placed_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.expiry_hours),
                smc_setup="BOS_BREAKOUT"
            )
            self.pending_orders[result.order] = pending_order
            logger.info(f"Sell Stop placed: {symbol} @ {price}, ticket {result.order}")
            return result.order
        else:
            logger.error(f"Failed to place Sell Stop: {result.comment if result else 'No result'}")
            return None
    
    def cancel_pending_order(self, ticket: int) -> bool:
        """
        Cancel a pending order.
        
        Args:
            ticket: Order ticket
            
        Returns:
            True if cancelled successfully
        """
        import MetaTrader5 as mt5
        
        if not self.mt5_connection:
            logger.error("No MT5 connection available")
            return False
        
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if ticket in self.pending_orders:
                del self.pending_orders[ticket]
            logger.info(f"Cancelled pending order {ticket}")
            return True
        else:
            logger.error(f"Failed to cancel order {ticket}: {result.comment if result else 'No result'}")
            return False
    
    def get_pending_orders(self) -> List[PendingOrder]:
        """Get list of active pending orders."""
        return list(self.pending_orders.values())
    
    def manage_pending_orders(self) -> None:
        """
        Manage pending orders: cancel expired or invalid orders.
        """
        import MetaTrader5 as mt5
        
        if not self.mt5_connection:
            return
        
        current_time = datetime.now()
        orders_to_cancel = []
        
        # Check for expired orders
        for ticket, order in self.pending_orders.items():
            if current_time >= order.expires_at:
                orders_to_cancel.append(ticket)
                logger.info(f"Order {ticket} expired")
        
        # Cancel expired orders
        for ticket in orders_to_cancel:
            self.cancel_pending_order(ticket)
        
        # Sync with MT5 (remove filled/cancelled orders from tracking)
        mt5_orders = mt5.orders_get()
        mt5_tickets = {o.ticket for o in mt5_orders} if mt5_orders else set()
        
        for ticket in list(self.pending_orders.keys()):
            if ticket not in mt5_tickets:
                # Order no longer exists in MT5 (filled or cancelled)
                del self.pending_orders[ticket]
                logger.info(f"Order {ticket} removed from tracking (filled or cancelled)")


# ============================================================================
# SYMBOL FILTER
# ============================================================================

class SymbolFilter:
    """Manages symbol whitelist and broker-specific symbol mapping."""
    
    def __init__(self, mt5_connection=None):
        self.whitelisted_symbols = SMC_CONFIG["whitelisted_symbols"]
        self.symbol_variations = SMC_CONFIG["symbol_variations"]
        self.symbol_map: Dict[str, SymbolMapping] = {}
        self.mt5_connection = mt5_connection
        logger.info(f"SymbolFilter initialized with whitelist: {self.whitelisted_symbols}")
    
    def initialize_symbol_mapping(self) -> None:
        """
        Discover and map broker-specific symbols.
        
        This method queries the broker for available symbols and maps
        standard names to broker-specific symbols.
        """
        if not self.mt5_connection:
            logger.warning("No MT5 connection provided for symbol mapping")
            return
        
        import MetaTrader5 as mt5
        
        # Get all available symbols from broker
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            logger.error("Failed to get symbols from broker")
            return
        
        broker_symbol_names = [s.name for s in all_symbols]
        logger.info(f"Found {len(broker_symbol_names)} symbols on broker")
        
        # Log potential matches for debugging
        us30_candidates = [s for s in broker_symbol_names if 'US30' in s.upper() or 'USA30' in s.upper() or 'DJ' in s.upper() or 'DOW' in s.upper()]
        xau_candidates = [s for s in broker_symbol_names if 'XAU' in s.upper() or 'GOLD' in s.upper()]
        nas_candidates = [s for s in broker_symbol_names if 'NAS' in s.upper() or 'NDX' in s.upper() or 'US100' in s.upper() or 'USA100' in s.upper()]
        
        logger.info(f"US30 candidates: {us30_candidates[:10]}")
        logger.info(f"XAUUSD candidates: {xau_candidates[:10]}")
        logger.info(f"NASDAQ candidates: {nas_candidates[:10]}")
        
        # Map each whitelisted symbol
        for standard_name in self.whitelisted_symbols:
            variations = self.symbol_variations.get(standard_name, [standard_name])
            
            # Try to find matching broker symbol
            broker_symbol = None
            for variation in variations:
                # Exact match (case-insensitive) - highest priority
                for bs in broker_symbol_names:
                    if bs.upper() == variation.upper():
                        broker_symbol = bs
                        break
                
                if broker_symbol:
                    break
                
                # Partial match (case-insensitive) - but avoid single-letter matches
                for bs in broker_symbol_names:
                    # Skip if broker symbol is too short (likely incorrect match)
                    if len(bs) < 3:
                        continue
                    
                    # Check if variation is contained in broker symbol
                    if len(variation) >= 3 and variation.upper() in bs.upper():
                        broker_symbol = bs
                        break
                    
                    # Check if broker symbol is contained in variation
                    if len(bs) >= 3 and bs.upper() in variation.upper():
                        broker_symbol = bs
                        break
                
                if broker_symbol:
                    break
            
            if broker_symbol:
                # Get symbol info
                symbol_info = mt5.symbol_info(broker_symbol)
                if symbol_info:
                    mapping = SymbolMapping(
                        standard_name=standard_name,
                        broker_symbol=broker_symbol,
                        is_available=True,
                        point_value=symbol_info.point,
                        min_lot=symbol_info.volume_min,
                        max_lot=symbol_info.volume_max
                    )
                    self.symbol_map[standard_name] = mapping
                    logger.info(f"Mapped {standard_name} -> {broker_symbol}")
                else:
                    logger.warning(f"Could not get info for {broker_symbol}")
            else:
                logger.warning(f"Could not find broker symbol for {standard_name}")
    
    def get_broker_symbol(self, standard_name: str) -> Optional[str]:
        """Get broker-specific symbol name from standard name."""
        mapping = self.symbol_map.get(standard_name)
        return mapping.broker_symbol if mapping else None
    
    def is_symbol_whitelisted(self, symbol: str) -> bool:
        """Check if symbol is in whitelist."""
        # Check standard names
        if symbol in self.whitelisted_symbols:
            return True
        
        # Check broker symbols
        for mapping in self.symbol_map.values():
            if mapping.broker_symbol == symbol:
                return True
        
        return False
    
    def get_tradeable_symbols(self) -> List[str]:
        """Get list of available whitelisted symbols (broker names)."""
        return [m.broker_symbol for m in self.symbol_map.values() if m.is_available]


# ============================================================================
# MARKET HOURS MANAGER
# ============================================================================

class MarketHoursManager:
    """Tracks trading sessions and determines if markets are open."""
    
    def __init__(self):
        self.trading_sessions: Dict[str, TradingSession] = {}
        logger.info("MarketHoursManager initialized")
    
    def load_trading_sessions(self) -> None:
        """Load trading session schedules from config."""
        sessions_config = SMC_CONFIG["trading_sessions"]
        
        for symbol, schedule in sessions_config.items():
            # Parse time strings
            open_time = datetime.strptime(schedule["open"], "%H:%M").time()
            close_time = datetime.strptime(schedule["close"], "%H:%M").time()
            break_start = datetime.strptime(schedule["break_start"], "%H:%M").time() if schedule.get("break_start") else None
            break_end = datetime.strptime(schedule["break_end"], "%H:%M").time() if schedule.get("break_end") else None
            
            session = TradingSession(
                symbol=symbol,
                open_time=open_time,
                close_time=close_time,
                break_start=break_start,
                break_end=break_end,
                trading_days=[0, 1, 2, 3, 4, 6]  # Mon-Fri + Sunday
            )
            
            self.trading_sessions[symbol] = session
            logger.info(f"Loaded session for {symbol}: {open_time} - {close_time}")
    
    def is_market_open(self, symbol: str, current_time: datetime) -> bool:
        """
        Check if market is open for symbol at current time.
        
        Args:
            symbol: Standard symbol name (US30, XAUUSD, etc.)
            current_time: Current datetime (should be in GMT)
            
        Returns:
            True if market is open, False otherwise
        """
        session = self.trading_sessions.get(symbol)
        if not session:
            logger.warning(f"No session schedule for {symbol}")
            return False
        
        # Check if current day is a trading day
        current_day = current_time.weekday()  # 0=Monday, 6=Sunday
        if current_day not in session.trading_days:
            return False
        
        current_time_only = current_time.time()
        
        # Handle 24-hour markets (open > close means crosses midnight)
        if session.open_time > session.close_time:
            # Market is open if time >= open OR time < close
            is_open = current_time_only >= session.open_time or current_time_only < session.close_time
        else:
            # Normal case: open < close
            is_open = session.open_time <= current_time_only < session.close_time
        
        # Check if in daily break
        if is_open and session.break_start and session.break_end:
            if session.break_start > session.break_end:
                # Break crosses midnight
                in_break = current_time_only >= session.break_start or current_time_only < session.break_end
            else:
                in_break = session.break_start <= current_time_only < session.break_end
            
            if in_break:
                return False
        
        return is_open
    
    def get_next_open_time(self, symbol: str) -> Optional[datetime]:
        """Calculate when market opens next for symbol."""
        # TODO: Implement next open time calculation
        return None
    
    def get_tradeable_symbols_now(self) -> List[str]:
        """Get list of symbols that are currently tradeable."""
        current_time = datetime.utcnow()  # Use UTC/GMT
        tradeable = []
        
        for symbol in self.trading_sessions.keys():
            if self.is_market_open(symbol, current_time):
                tradeable.append(symbol)
        
        return tradeable


# ============================================================================
# SMC SIGNAL GENERATOR
# ============================================================================

class SMCSignalGenerator:
    """Generates high-probability SMC trade signals."""
    
    def __init__(self, fvg_detector: FVGDetector, order_block_detector: OrderBlockDetector,
                 structure_analyzer: MarketStructureAnalyzer, mtf_analyzer: MultiTimeframeAnalyzer):
        self.fvg_detector = fvg_detector
        self.order_block_detector = order_block_detector
        self.structure_analyzer = structure_analyzer
        self.mtf_analyzer = mtf_analyzer
        self.min_rr = SMC_CONFIG["risk_reward_min"]
        logger.info("SMCSignalGenerator initialized")
    
    def analyze_setup(self, symbol: str, candles_by_tf: Dict[str, List[dict]], 
                     current_price: float) -> Optional[SMCSignal]:
        """
        Analyze complete SMC setup for a symbol.
        
        Args:
            symbol: Trading symbol
            candles_by_tf: Candles for each timeframe
            current_price: Current market price
            
        Returns:
            SMCSignal or None
        """
        # Multi-timeframe analysis
        tf_analysis = self.mtf_analyzer.analyze_all_timeframes(symbol, candles_by_tf)
        
        # Get HTF bias
        htf_bias = self.mtf_analyzer.get_htf_bias(tf_analysis.h4_structure, tf_analysis.h1_structure)
        
        logger.info(f"HTF Bias for {symbol}: {htf_bias}")
        
        if htf_bias == "NEUTRAL":
            logger.info(f"Skipping {symbol}: Neutral bias")
            return None
        
        # Find confluence zones
        confluence_zones = self.mtf_analyzer.find_confluence_zones(tf_analysis)
        
        if not confluence_zones:
            logger.info(f"No confluence zones found for {symbol}")
            
            # Fallback: Use H1 FVGs if available
            if tf_analysis.h1_fvgs:
                logger.info(f"Using H1 FVGs as fallback for {symbol}")
                
                # Filter FVGs by direction matching bias
                matching_fvgs = [fvg for fvg in tf_analysis.h1_fvgs 
                                if (htf_bias == "BULLISH" and fvg.direction == "BULLISH") or
                                   (htf_bias == "BEARISH" and fvg.direction == "BEARISH")]
                
                if not matching_fvgs:
                    logger.info(f"No matching FVGs for {symbol}")
                    return None
                
                # Get nearest FVG
                nearest_fvg = min(matching_fvgs, key=lambda fvg: abs(fvg.equilibrium - current_price))
                
                # Create signal from FVG
                if htf_bias == "BULLISH":
                    entry_price = nearest_fvg.equilibrium
                    stop_loss = nearest_fvg.low * 0.999
                    risk = entry_price - stop_loss
                    take_profit = entry_price + (risk * 2.5)
                    
                    order_type = "BUY_LIMIT" if current_price > entry_price else "BUY_STOP"
                    
                    signal = SMCSignal(
                        symbol=symbol,
                        direction="BUY",
                        order_type=order_type,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=0.6,
                        setup_type="FVG_ENTRY",
                        timeframe_bias={"H4": tf_analysis.h4_bias, "H1": tf_analysis.h1_bias},
                        zones=[],
                        timestamp=datetime.now()
                    )
                    
                    if self.validate_signal(signal):
                        logger.info(f"Generated BUY signal for {symbol} from FVG")
                        return signal
                
                else:  # BEARISH
                    entry_price = nearest_fvg.equilibrium
                    stop_loss = nearest_fvg.high * 1.001
                    risk = stop_loss - entry_price
                    take_profit = entry_price - (risk * 2.5)
                    
                    order_type = "SELL_LIMIT" if current_price < entry_price else "SELL_STOP"
                    
                    signal = SMCSignal(
                        symbol=symbol,
                        direction="SELL",
                        order_type=order_type,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=0.6,
                        setup_type="FVG_ENTRY",
                        timeframe_bias={"H4": tf_analysis.h4_bias, "H1": tf_analysis.h1_bias},
                        zones=[],
                        timestamp=datetime.now()
                    )
                    
                    if self.validate_signal(signal):
                        logger.info(f"Generated SELL signal for {symbol} from FVG")
                        return signal
            
            return None
        
        # Get nearest confluence zone
        nearest_zone = min(confluence_zones, key=lambda z: abs(z.entry_price - current_price))
        
        logger.info(f"Nearest confluence zone for {symbol}: {nearest_zone.direction} @ {nearest_zone.entry_price:.2f}")
        
        # Determine if we should enter
        if htf_bias == "BULLISH" and nearest_zone.direction == "BULLISH":
            # Look for buy setup
            entry_price = nearest_zone.entry_price
            stop_loss = nearest_zone.low - (nearest_zone.high - nearest_zone.low) * 0.1
            take_profit = nearest_zone.high + (nearest_zone.high - nearest_zone.low) * 2
            
            # Determine order type
            if current_price > entry_price:
                order_type = "BUY_LIMIT"  # Price needs to pull back
            else:
                order_type = "BUY_STOP"  # Price needs to break up
            
            signal = SMCSignal(
                symbol=symbol,
                direction="BUY",
                order_type=order_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=nearest_zone.confidence,
                setup_type="CONFLUENCE",
                timeframe_bias={"H4": tf_analysis.h4_bias, "H1": tf_analysis.h1_bias},
                zones=[nearest_zone],
                timestamp=datetime.now()
            )
            
            if self.validate_signal(signal):
                logger.info(f"Generated BUY signal for {symbol} from confluence")
                return signal
            else:
                logger.info(f"Signal validation failed for {symbol}")
        
        elif htf_bias == "BEARISH" and nearest_zone.direction == "BEARISH":
            # Look for sell setup
            entry_price = nearest_zone.entry_price
            stop_loss = nearest_zone.high + (nearest_zone.high - nearest_zone.low) * 0.1
            take_profit = nearest_zone.low - (nearest_zone.high - nearest_zone.low) * 2
            
            # Determine order type
            if current_price < entry_price:
                order_type = "SELL_LIMIT"  # Price needs to rally
            else:
                order_type = "SELL_STOP"  # Price needs to break down
            
            signal = SMCSignal(
                symbol=symbol,
                direction="SELL",
                order_type=order_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=nearest_zone.confidence,
                setup_type="CONFLUENCE",
                timeframe_bias={"H4": tf_analysis.h4_bias, "H1": tf_analysis.h1_bias},
                zones=[nearest_zone],
                timestamp=datetime.now()
            )
            
            if self.validate_signal(signal):
                logger.info(f"Generated SELL signal for {symbol} from confluence")
                return signal
            else:
                logger.info(f"Signal validation failed for {symbol}")
        
        return None
    
    def calculate_entry_price(self, fvg: FVG, order_block: Optional[OrderBlock] = None) -> float:
        """Calculate entry price from FVG and/or Order Block."""
        if order_block:
            # Use Order Block 50% level
            return order_block.entry_price
        else:
            # Use FVG equilibrium
            return fvg.equilibrium
    
    def calculate_stop_loss(self, direction: str, order_block: Optional[OrderBlock] = None,
                           fvg: Optional[FVG] = None) -> float:
        """Calculate stop loss beyond invalidation point."""
        if direction == "BUY":
            if order_block:
                return order_block.low * 0.999  # Just below OB low
            elif fvg:
                return fvg.low * 0.999  # Just below FVG low
        else:  # SELL
            if order_block:
                return order_block.high * 1.001  # Just above OB high
            elif fvg:
                return fvg.high * 1.001  # Just above FVG high
        
        return 0.0
    
    def calculate_take_profit(self, direction: str, entry: float, stop_loss: float,
                             rr_ratio: float = 2.0) -> float:
        """Calculate take profit based on risk-reward ratio."""
        risk = abs(entry - stop_loss)
        
        if direction == "BUY":
            return entry + (risk * rr_ratio)
        else:  # SELL
            return entry - (risk * rr_ratio)
    
    def get_order_type(self, direction: str, current_price: float, entry_price: float) -> str:
        """Determine order type based on price position."""
        if direction == "BUY":
            if current_price > entry_price:
                return "BUY_LIMIT"  # Buy on pullback
            else:
                return "BUY_STOP"  # Buy on breakout
        else:  # SELL
            if current_price < entry_price:
                return "SELL_LIMIT"  # Sell on rally
            else:
                return "SELL_STOP"  # Sell on breakdown
    
    def validate_signal(self, signal: SMCSignal) -> bool:
        """
        Validate signal meets minimum requirements.
        
        Args:
            signal: SMC signal to validate
            
        Returns:
            True if valid
        """
        # Check all required fields are populated
        if not signal.entry_price or not signal.stop_loss or not signal.take_profit:
            logger.warning(f"Signal rejected: Missing required fields (entry={signal.entry_price}, sl={signal.stop_loss}, tp={signal.take_profit})")
            return False
        
        # Check risk-reward ratio
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        
        if risk <= 0:
            logger.warning(f"Signal rejected: Invalid risk {risk}")
            return False
        
        rr_ratio = reward / risk
        
        logger.info(f"Signal validation: RR={rr_ratio:.2f}, Confidence={signal.confidence:.2%}")
        
        if rr_ratio < self.min_rr:
            logger.info(f"Signal rejected: RR {rr_ratio:.2f} < minimum {self.min_rr}")
            return False
        
        # Check confidence
        if signal.confidence < 0.5:
            logger.info(f"Signal rejected: Low confidence {signal.confidence}")
            return False
        
        logger.info(f"Signal validated: {signal.symbol} {signal.direction} @ {signal.entry_price:.2f}")
        return True


# ============================================================================
# MAIN SMC STRATEGY CLASS
# ============================================================================

class SMCStrategy:
    """Main Smart Money Concepts strategy coordinator."""
    
    def __init__(self, mt5_connection=None):
        self.fvg_detector = FVGDetector()
        self.order_block_detector = OrderBlockDetector()
        self.market_structure_analyzer = MarketStructureAnalyzer()
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.multi_timeframe_analyzer = MultiTimeframeAnalyzer(
            self.fvg_detector,
            self.market_structure_analyzer
        )
        self.signal_generator = SMCSignalGenerator(
            self.fvg_detector,
            self.order_block_detector,
            self.market_structure_analyzer,
            self.multi_timeframe_analyzer
        )
        self.pending_order_manager = PendingOrderManager(mt5_connection)
        self.symbol_filter = SymbolFilter(mt5_connection)
        self.market_hours_manager = MarketHoursManager()
        
        # Initialize components
        self.symbol_filter.initialize_symbol_mapping()
        self.market_hours_manager.load_trading_sessions()
        
        logger.info("SMCStrategy initialized")
    
    def get_tradeable_symbols(self) -> List[str]:
        """Get symbols that are both whitelisted and market is open."""
        available_symbols = self.symbol_filter.get_tradeable_symbols()
        open_standard_symbols = self.market_hours_manager.get_tradeable_symbols_now()
        
        # Filter available symbols by market hours
        # available_symbols contains broker symbols, open_standard_symbols contains standard names
        tradeable = []
        for broker_symbol in available_symbols:
            # Find the standard name for this broker symbol
            for standard_name, mapping in self.symbol_filter.symbol_map.items():
                if mapping.broker_symbol == broker_symbol:
                    # Check if this standard symbol's market is open
                    if standard_name in open_standard_symbols:
                        tradeable.append(broker_symbol)
                    break
        
        logger.info(f"Tradeable symbols: {tradeable}")
        return tradeable
    
    def analyze_symbol(self, symbol: str, candles: List[dict], timeframe: str = "H1") -> Dict:
        """
        Perform complete SMC analysis on a symbol.
        
        Args:
            symbol: Trading symbol
            candles: OHLC candles
            timeframe: Timeframe string
            
        Returns:
            Dictionary with analysis results
        """
        # Detect FVGs
        fvgs = self.fvg_detector.detect_fvgs(candles, timeframe)
        valid_fvgs = self.fvg_detector.filter_valid_fvgs(fvgs)
        
        # Detect Order Blocks
        order_blocks = self.order_block_detector.detect_order_blocks(candles)
        
        # Analyze market structure
        structure = self.market_structure_analyzer.identify_structure(candles)
        
        # Identify liquidity levels
        liquidity_levels = self.liquidity_analyzer.identify_liquidity_levels(candles)
        
        analysis = {
            "symbol": symbol,
            "timeframe": timeframe,
            "fvgs": valid_fvgs,
            "order_blocks": order_blocks,
            "market_structure": structure,
            "liquidity_levels": liquidity_levels,
            "trend": structure.trend
        }
        
        # Log analysis results
        self.log_analysis(analysis)
        
        return analysis
    
    def log_analysis(self, analysis: Dict) -> None:
        """
        Log SMC analysis results.
        
        Args:
            analysis: Analysis dictionary
        """
        symbol = analysis["symbol"]
        timeframe = analysis["timeframe"]
        
        logger.info(f"=== SMC Analysis: {symbol} ({timeframe}) ===")
        
        # Log FVGs
        fvgs = analysis["fvgs"]
        logger.info(f"FVGs detected: {len(fvgs)}")
        for i, fvg in enumerate(fvgs[:3]):  # Log first 3
            logger.info(f"  FVG {i+1}: {fvg.direction} [{fvg.low:.2f} - {fvg.high:.2f}] EQ: {fvg.equilibrium:.2f}")
        
        # Log Order Blocks
        obs = analysis["order_blocks"]
        logger.info(f"Order Blocks detected: {len(obs)}")
        for i, ob in enumerate(obs[:3]):  # Log first 3
            logger.info(f"  OB {i+1}: {ob.direction} [{ob.low:.2f} - {ob.high:.2f}] Entry: {ob.entry_price:.2f}")
        
        # Log Market Structure
        structure = analysis["market_structure"]
        logger.info(f"Market Structure: {structure.trend}")
        logger.info(f"  Swing Highs: {len(structure.swing_highs)}, Swing Lows: {len(structure.swing_lows)}")
        
        # Log Liquidity Levels
        liq_levels = analysis["liquidity_levels"]
        logger.info(f"Liquidity Levels: {len(liq_levels)}")
    
    def log_signal(self, signal: SMCSignal) -> None:
        """
        Log SMC signal generation.
        
        Args:
            signal: SMC signal
        """
        logger.info(f"=== SMC Signal Generated ===")
        logger.info(f"Symbol: {signal.symbol}")
        logger.info(f"Direction: {signal.direction} ({signal.order_type})")
        logger.info(f"Entry: {signal.entry_price:.2f}")
        logger.info(f"Stop Loss: {signal.stop_loss:.2f}")
        logger.info(f"Take Profit: {signal.take_profit:.2f}")
        logger.info(f"Confidence: {signal.confidence:.2%}")
        logger.info(f"Setup Type: {signal.setup_type}")
        logger.info(f"Timeframe Bias: {signal.timeframe_bias}")
        logger.info(f"Confluence Zones: {len(signal.zones)}")
    
    def display_status(self, symbol: str, analysis: Dict) -> str:
        """
        Display current SMC status for a symbol.
        
        Args:
            symbol: Trading symbol
            analysis: Analysis dictionary
            
        Returns:
            Status string
        """
        structure = analysis["market_structure"]
        fvgs = analysis["fvgs"]
        obs = analysis["order_blocks"]
        
        # Determine bias
        bias = "BULLISH" if structure.trend == "UPTREND" else "BEARISH" if structure.trend == "DOWNTREND" else "NEUTRAL"
        
        status = f"\n📊 SMC Status: {symbol}\n"
        status += f"{'='*50}\n"
        status += f"Bias: {bias} ({structure.trend})\n"
        status += f"\nActive Zones:\n"
        status += f"  • FVGs: {len(fvgs)}\n"
        status += f"  • Order Blocks: {len(obs)}\n"
        
        if fvgs:
            status += f"\nNearest FVGs:\n"
            for i, fvg in enumerate(fvgs[:2]):
                status += f"  {i+1}. {fvg.direction} FVG: {fvg.low:.2f} - {fvg.high:.2f}\n"
        
        if obs:
            status += f"\nNearest Order Blocks:\n"
            for i, ob in enumerate(obs[:2]):
                status += f"  {i+1}. {ob.direction} OB: {ob.low:.2f} - {ob.high:.2f}\n"
        
        return status
    
    def log_trade_execution(self, signal: SMCSignal, ticket: Optional[int]) -> None:
        """
        Log trade execution.
        
        Args:
            signal: SMC signal that triggered trade
            ticket: Order ticket (None if failed)
        """
        if ticket:
            logger.info(f"Trade Executed: {signal.symbol} {signal.direction}")
            logger.info(f"   Ticket: {ticket}")
            logger.info(f"   Setup: {signal.setup_type}")
            logger.info(f"   Entry: {signal.entry_price:.2f}")
        else:
            logger.error(f"Trade Failed: {signal.symbol} {signal.direction}")
            logger.error(f"   Setup: {signal.setup_type}")
