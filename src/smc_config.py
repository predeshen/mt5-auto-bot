"""Configuration for Smart Money Concepts (SMC) Strategy Module."""

# Timeframes for multi-timeframe analysis
SMC_CONFIG = {
    # Analysis timeframes
    "timeframes": ["H4", "H1", "M15", "M5"],
    
    # FVG (Fair Value Gap) settings
    "fvg_min_size_pips": 5,  # Minimum gap size to consider
    
    # Order Block settings
    "order_block_min_move": 20,  # Minimum pips for significant move
    
    # Pending order settings
    "pending_order_expiry_hours": 4,  # Cancel orders after 4 hours
    "max_pending_orders_per_symbol": 3,  # Maximum pending orders per symbol
    
    # Confluence settings
    "confluence_min_components": 2,  # Minimum components for high-confidence zone
    
    # Liquidity settings
    "liquidity_sweep_threshold_pips": 10,  # Pips beyond swing for sweep detection
    
    # Risk management
    "risk_reward_min": 2.0,  # Minimum risk-reward ratio
    
    # Symbol filtering - only trade these instruments
    "whitelisted_symbols": ["US30", "XAUUSD", "US30 FT", "NASDAQ", "NASDAQ FT"],
    
    # Symbol variations for broker-specific mapping
    "symbol_variations": {
        "US30": ["US30", "US30.cash", "US30Cash", "USTEC", "DJ30", "DJI", "US30.","USA30"],
        "XAUUSD": ["XAUUSD", "XAUUSD.a", "GOLD", "Gold", "XAU", "XAUUSD."],
        "US30 FT": ["US30ft", "US30.f", "US30_FUT", "YM", "US30FT","USA30.F"],
        "NASDAQ": ["NAS100", "USTEC", "NDX", "NASDAQ", "US100", "NAS100.","US100"],
        "NASDAQ FT": ["NAS100ft", "NAS100.f", "USTEC_FUT", "NQ", "NAS100FT","US100.F"],
    },
    
    # Market hours (GMT) - Sunday 23:00 to Friday 22:00 with daily breaks
    "trading_sessions": {
        "US30": {
            "open": "23:00",
            "close": "22:00",
            "break_start": "22:00",
            "break_end": "23:00"
        },
        "XAUUSD": {
            "open": "23:00",
            "close": "22:00",
            "break_start": "22:00",
            "break_end": "23:00"
        },
        "NASDAQ": {
            "open": "23:00",
            "close": "22:00",
            "break_start": "22:00",
            "break_end": "23:00"
        },
        # Futures typically have same hours
        "US30 FT": {
            "open": "23:00",
            "close": "22:00",
            "break_start": "22:00",
            "break_end": "23:00"
        },
        "NASDAQ FT": {
            "open": "23:00",
            "close": "22:00",
            "break_start": "22:00",
            "break_end": "23:00"
        },
    },
}


# MT5 Timeframe mapping
MT5_TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 16385,
    "H4": 16388,
    "D1": 16408,
}
