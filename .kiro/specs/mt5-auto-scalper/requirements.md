# Requirements Document

## Introduction

This document specifies the requirements for an automated scalp trading console application that connects to MetaTrader 5 (MT5) accounts, identifies high-volatility markets, and executes automated scalping trades using 5-minute timeframes.

## Glossary

- **MT5 System**: The MetaTrader 5 trading platform and API
- **Console Application**: The command-line interface application being developed
- **Account Equity**: The current total value of the trading account including open positions
- **Volatility Scanner**: The component that identifies high-volatility trading instruments
- **Trade Manager**: The component responsible for opening and closing trades automatically
- **Scalping Strategy**: A trading approach using 5-minute timeframes to capture small price movements
- **Connection Credentials**: MT5 account number, password, and server information required for authentication

## Requirements

### Requirement 1

**User Story:** As a trader, I want to provide my MT5 connection credentials at startup, so that the Console Application can authenticate with my trading account.

#### Acceptance Criteria

1. WHEN the Console Application starts, THEN the Console Application SHALL prompt the user for MT5 account number, password, and server address
2. WHEN the user submits connection credentials, THEN the Console Application SHALL attempt to establish a connection to the MT5 System
3. IF the connection to the MT5 System fails, THEN the Console Application SHALL display a clear error message and SHALL prompt the user to re-enter credentials
4. WHEN the connection to the MT5 System succeeds, THEN the Console Application SHALL display a success confirmation message
5. WHEN the connection to the MT5 System succeeds, THEN the Console Application SHALL proceed to the main application flow

### Requirement 2

**User Story:** As a trader, I want to view my current account equity after connecting, so that I can verify my account status before trading.

#### Acceptance Criteria

1. WHEN the MT5 System connection is established, THEN the Console Application SHALL retrieve the current account equity from the MT5 System
2. WHEN account equity is retrieved, THEN the Console Application SHALL display the equity value in the account's base currency
3. IF the equity retrieval fails, THEN the Console Application SHALL display an error message and SHALL retry the retrieval operation
4. WHEN the account equity is displayed, THEN the Console Application SHALL format the value with appropriate decimal precision for currency

### Requirement 3

**User Story:** As a trader, I want to configure trading parameters before starting automated trading, so that I can control risk and position limits.

#### Acceptance Criteria

1. WHEN the account equity is displayed, THEN the Console Application SHALL prompt the user for maximum open positions allowed
2. WHEN the user enters maximum open positions, THEN the Console Application SHALL validate the input is a positive integer
3. WHEN the user enters trading parameters, THEN the Console Application SHALL prompt for risk percentage per trade
4. WHEN all trading parameters are collected, THEN the Console Application SHALL display a summary of the configuration for user confirmation
5. WHEN the user confirms trading parameters, THEN the Console Application SHALL proceed to instrument selection

### Requirement 4

**User Story:** As a trader, I want to see a list of high-volatility markets currently available for trading, so that I can select the most promising scalping opportunities.

#### Acceptance Criteria

1. WHEN trading parameters are confirmed, THEN the Volatility Scanner SHALL analyze available trading instruments using 5-minute timeframe data
2. WHEN analyzing instruments, THEN the Volatility Scanner SHALL calculate volatility metrics based on recent price movements
3. WHEN volatility analysis is complete, THEN the Console Application SHALL display a ranked list of high-volatility instruments
4. WHEN displaying instrument options, THEN the Console Application SHALL show the instrument symbol, current volatility metric, and current price
5. WHEN the instrument list is displayed, THEN the Console Application SHALL prompt the user to select one or more instruments for automated trading

### Requirement 5

**User Story:** As a trader, I want the system to automatically open trades on selected high-volatility instruments, so that I can capture scalping opportunities without manual intervention.

#### Acceptance Criteria

1. WHEN the user selects instruments for trading, THEN the Trade Manager SHALL monitor those instruments continuously using 5-minute timeframe data
2. WHEN the Scalping Strategy identifies an entry signal, THEN the Trade Manager SHALL calculate appropriate position size based on account equity and risk parameters
3. WHEN position size is calculated, THEN the Trade Manager SHALL submit a market order to the MT5 System
4. WHEN a trade order is submitted, THEN the Trade Manager SHALL verify the order execution and SHALL store the trade details
5. IF an order submission fails, THEN the Trade Manager SHALL log the error and SHALL continue monitoring for the next opportunity
6. WHEN the number of open positions reaches the maximum configured limit, THEN the Trade Manager SHALL not open new positions until existing positions are closed

### Requirement 6

**User Story:** As a trader, I want the system to automatically close trades based on the scalping strategy, so that I can lock in profits and limit losses without constant monitoring.

#### Acceptance Criteria

1. WHILE a trade is open, THEN the Trade Manager SHALL monitor the position continuously using real-time price data
2. WHEN the Scalping Strategy identifies an exit signal, THEN the Trade Manager SHALL submit a close order to the MT5 System
3. WHEN a position reaches a predefined profit target, THEN the Trade Manager SHALL close the position automatically
4. WHEN a position reaches a predefined stop loss level, THEN the Trade Manager SHALL close the position automatically
5. WHEN a close order is executed, THEN the Trade Manager SHALL log the trade result including entry price, exit price, and profit or loss

### Requirement 7

**User Story:** As a trader, I want to see real-time updates of trading activity in the console, so that I can monitor the system's performance and current positions.

#### Acceptance Criteria

1. WHILE the Console Application is running, THEN the Console Application SHALL display real-time updates of open positions
2. WHEN a new trade is opened, THEN the Console Application SHALL display the trade details including instrument, direction, size, and entry price
3. WHEN a trade is closed, THEN the Console Application SHALL display the close details including exit price and profit or loss
4. WHEN displaying trade information, THEN the Console Application SHALL include timestamps for all events
5. WHILE monitoring markets, THEN the Console Application SHALL display current account equity updates at regular intervals
6. WHEN displaying position count, THEN the Console Application SHALL show current open positions versus the configured maximum

### Requirement 8

**User Story:** As a trader, I want the system to handle connection interruptions gracefully, so that my trading activity is not disrupted by temporary network issues.

#### Acceptance Criteria

1. WHEN the connection to the MT5 System is lost, THEN the Console Application SHALL detect the disconnection within 10 seconds
2. WHEN a disconnection is detected, THEN the Console Application SHALL attempt to reconnect automatically
3. WHILE attempting reconnection, THEN the Console Application SHALL pause new trade entries but SHALL continue monitoring open positions
4. WHEN reconnection succeeds, THEN the Console Application SHALL resume normal trading operations
5. IF reconnection fails after 5 attempts, THEN the Console Application SHALL alert the user and SHALL wait for manual intervention

### Requirement 9

**User Story:** As a trader, I want to be able to stop the automated trading gracefully, so that I can exit the application safely without leaving orphaned positions.

#### Acceptance Criteria

1. WHILE the Console Application is running, THEN the Console Application SHALL monitor for user shutdown commands
2. WHEN the user initiates shutdown, THEN the Console Application SHALL stop opening new positions immediately
3. WHEN shutdown is initiated, THEN the Console Application SHALL display the current open positions and SHALL prompt the user for close instructions
4. WHEN the user confirms position closure, THEN the Trade Manager SHALL close all open positions before terminating
5. WHEN all positions are closed or the user chooses to leave them open, THEN the Console Application SHALL disconnect from the MT5 System and SHALL terminate cleanly
