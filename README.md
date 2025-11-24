# MT5 Auto Scalper

An automated scalping trading application for MetaTrader 5 that identifies high-volatility markets and executes trades automatically using a 5-minute timeframe strategy.

## Features

- **Automated Trading**: Executes scalping trades based on RSI and volatility breakout signals
- **Risk Management**: Configurable position sizing, stop loss, and take profit levels
- **High-Volatility Scanner**: Identifies the best trading opportunities using ATR analysis
- **Position Management**: Automatic position monitoring and closure
- **Graceful Shutdown**: Safe exit with option to close all positions
- **Comprehensive Logging**: Full trade history and system events

## Requirements

- Python 3.10 or higher
- Windows OS (MT5 API limitation)
- Active MetaTrader 5 installation
- MT5 trading account (demo or live)
- Internet connection

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure MetaTrader 5 is installed and running on your system

## Usage

Run the application:
```bash
python main.py
```

The application will prompt you for:
1. **MT5 Credentials**: Account number, password, and server
2. **Trading Parameters**: Maximum open positions and risk percentage per trade
3. **Confirmation**: Review and confirm your settings

## Configuration

### Trading Parameters

- **Maximum Open Positions**: Number of concurrent trades (recommended: 1-5)
- **Risk Percentage**: Percentage of equity to risk per trade (recommended: 0.5-2%)
- **Profit Target**: 1.5x ATR (configurable in code)
- **Stop Loss**: 1.0x ATR (configurable in code)

### Strategy Logic

**Entry Signals:**
- **BUY**: RSI < 30 (oversold) + price breakout above recent high + volume confirmation
- **SELL**: RSI > 70 (overbought) + price breakdown below recent low + volume confirmation

**Exit Conditions:**
- Take Profit: 1.5x ATR from entry
- Stop Loss: 1.0x ATR from entry
- Time-based: 30 minutes maximum hold time

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest --cov=src tests/
```

The project includes 32+ property-based tests using Hypothesis for robust validation.

## Project Structure

```
mt5-auto-scalper/
├── src/
│   ├── models.py              # Data models
│   ├── mt5_connection.py      # MT5 connection management
│   ├── display.py             # Console UI
│   ├── volatility_scanner.py  # Market analysis
│   ├── scalping_strategy.py   # Trading strategy
│   ├── trade_manager.py       # Trade execution
│   ├── logger.py              # Logging system
│   └── app_controller.py      # Main controller
├── tests/                     # Property-based tests
├── logs/                      # Application logs
├── main.py                    # Entry point
└── requirements.txt           # Dependencies
```

## Safety & Disclaimers

⚠️ **IMPORTANT WARNINGS:**

1. **Use at Your Own Risk**: Automated trading involves substantial risk of loss
2. **Test First**: Always test on a demo account before using real money
3. **Monitor Actively**: Never leave the system completely unattended
4. **Start Small**: Begin with minimum position sizes and low risk percentages
5. **Understand the Code**: Review and understand the strategy before using
6. **No Guarantees**: Past performance does not guarantee future results

## Troubleshooting

### Connection Issues
- Ensure MT5 is running and logged in
- Verify server address is correct
- Check firewall settings

### No Instruments Found
- Market may be closed
- Volatility threshold may be too high
- Check MT5 symbol availability

### Order Failures
- Insufficient margin
- Market closed for symbol
- Invalid order parameters
- Check MT5 terminal for error messages

## Logs

Application logs are stored in the `logs/` directory with daily rotation:
- Trade events (open/close)
- Connection status
- Errors and warnings
- System events

## Development

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_scalping_strategy.py -v

# With coverage
pytest --cov=src --cov-report=html tests/
```

### Code Structure
- **Property-Based Testing**: Uses Hypothesis for comprehensive test coverage
- **Modular Design**: Separated concerns for easy maintenance
- **Type Hints**: Full type annotations for better IDE support
- **Logging**: Comprehensive logging for debugging and monitoring

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `logs/` directory
3. Ensure all requirements are met
4. Test with demo account first

---

**Remember**: Trading involves risk. Only trade with money you can afford to lose.
