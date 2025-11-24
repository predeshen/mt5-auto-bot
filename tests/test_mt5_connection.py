"""Property-based tests for MT5 Connection Manager."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, settings
from hypothesis import strategies as st

from src.mt5_connection import MT5ConnectionManager


# Custom strategies for generating test data
@st.composite
def credentials_strategy(draw):
    """Generate random MT5 credentials."""
    account = draw(st.integers(min_value=1, max_value=999999999))
    password = draw(st.text(min_size=1, max_size=50))
    server = draw(st.text(min_size=1, max_size=100))
    return account, password, server


# Feature: mt5-auto-scalper, Property 1: Connection attempt on credential submission
# For any submitted credentials (valid or invalid), the application should attempt
# to establish an MT5 connection
@settings(max_examples=100)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
def test_property_1_connection_attempt_on_credential_submission(mock_mt5, creds):
    """
    Property 1: Connection attempt on credential submission
    Validates: Requirements 1.2
    
    For any submitted credentials, the system should attempt to connect to MT5.
    """
    account, password, server = creds
    
    # Setup mock
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    
    manager = MT5ConnectionManager()
    result = manager.connect(account, password, server)
    
    # Verify that connection was attempted
    mock_mt5.initialize.assert_called_once()
    mock_mt5.login.assert_called_once_with(account, password=password, server=server)
    
    # Connection should succeed with mocked successful responses
    assert result is True


@settings(max_examples=100)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
def test_property_1_connection_attempt_with_failures(mock_mt5, creds):
    """Test that connection is attempted even when it fails."""
    account, password, server = creds
    
    # Setup mock to simulate failure
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (1, "Connection failed")
    
    manager = MT5ConnectionManager()
    result = manager.connect(account, password, server)
    
    # Verify that connection was attempted despite failure
    mock_mt5.initialize.assert_called_once()
    assert result is False


# Feature: mt5-auto-scalper, Property 2: Application flow progression on successful connection
# For any successful MT5 connection, the application should transition to the main
# application flow (equity display phase)
@settings(max_examples=100)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
def test_property_2_flow_progression_on_successful_connection(mock_mt5, creds):
    """
    Property 2: Application flow progression on successful connection
    Validates: Requirements 1.5
    
    For any successful connection, the manager should be in connected state.
    """
    account, password, server = creds
    
    # Setup mock for successful connection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock()
    
    manager = MT5ConnectionManager()
    connection_result = manager.connect(account, password, server)
    
    # Verify successful connection enables progression
    assert connection_result is True
    assert manager.is_connected() is True


# Feature: mt5-auto-scalper, Property 3: Equity retrieval after connection
# For any established MT5 connection, the application should attempt to retrieve
# account equity
@settings(max_examples=100)
@given(
    account=st.integers(min_value=1, max_value=999999999),
    equity=st.floats(min_value=100.0, max_value=1000000.0),
    balance=st.floats(min_value=100.0, max_value=1000000.0)
)
@patch('src.mt5_connection.mt5')
def test_property_3_equity_retrieval_after_connection(mock_mt5, account, equity, balance):
    """
    Property 3: Equity retrieval after connection
    Validates: Requirements 2.1
    
    For any established connection, equity retrieval should be attempted.
    """
    # Setup mock for successful connection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock()
    
    # Setup mock account info
    mock_account_info = MagicMock()
    mock_account_info.login = account
    mock_account_info.equity = equity
    mock_account_info.balance = balance
    mock_account_info.margin = 0.0
    mock_account_info.margin_free = balance
    mock_account_info.currency = "USD"
    mock_mt5.account_info.return_value = mock_account_info
    
    manager = MT5ConnectionManager()
    manager.connect(account, "password", "server")
    
    # Attempt to retrieve account info
    account_info = manager.get_account_info()
    
    # Verify equity retrieval was attempted
    mock_mt5.account_info.assert_called_once()
    assert account_info is not None
    assert account_info.equity == equity
    assert account_info.balance == balance


@settings(max_examples=100)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
def test_reconnection_attempts(mock_mt5, creds):
    """Test that reconnection is attempted with exponential backoff."""
    account, password, server = creds
    
    # Setup mock for initial connection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    
    manager = MT5ConnectionManager()
    manager.connect(account, password, server)
    
    # Simulate disconnection
    manager._connected = False
    
    # Setup mock for reconnection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    
    # Attempt reconnection
    result = manager.reconnect(max_attempts=3)
    
    # Verify reconnection was attempted
    assert result is True
    assert mock_mt5.login.call_count >= 2  # Initial + reconnection



# Feature: mt5-auto-scalper, Property 23: Disconnection detection timing
# For any MT5 connection loss, the application should detect the disconnection
# within 10 seconds
@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
async def test_property_23_disconnection_detection_timing(mock_mt5, creds):
    """
    Property 23: Disconnection detection timing
    Validates: Requirements 8.1
    
    For any connection loss, detection should occur within 10 seconds.
    """
    account, password, server = creds
    
    # Setup mock for successful initial connection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock()
    
    manager = MT5ConnectionManager()
    manager.connect(account, password, server)
    
    # Track disconnection detection
    disconnection_detected = False
    detection_time = None
    
    def on_connection_change(connected: bool):
        nonlocal disconnection_detected, detection_time
        if not connected:
            disconnection_detected = True
            detection_time = True  # Mark that detection occurred
    
    manager.add_connection_listener(on_connection_change)
    
    # Simulate connection loss
    mock_mt5.terminal_info.return_value = None
    
    # Start heartbeat monitor with short interval for testing
    manager._heartbeat_task = asyncio.create_task(manager._heartbeat_loop(interval=1))
    
    # Wait up to 10 seconds for detection
    for _ in range(10):
        await asyncio.sleep(1)
        if disconnection_detected:
            break
    
    # Cleanup
    manager.stop_heartbeat_monitor()
    
    # Verify disconnection was detected within time limit
    assert disconnection_detected, "Disconnection should be detected"


# Feature: mt5-auto-scalper, Property 24: Reconnection with state preservation
# For any detected disconnection, the application should attempt automatic
# reconnection while pausing new entries and continuing to monitor open positions
@settings(max_examples=50)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
def test_property_24_reconnection_with_state_preservation(mock_mt5, creds):
    """
    Property 24: Reconnection with state preservation
    Validates: Requirements 8.2, 8.3, 8.4
    
    For any disconnection, automatic reconnection should be attempted.
    """
    account, password, server = creds
    
    # Setup mock for successful initial connection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock()
    
    manager = MT5ConnectionManager()
    manager.connect(account, password, server)
    
    # Track connection state changes
    connection_states = []
    
    def on_connection_change(connected: bool):
        connection_states.append(connected)
    
    manager.add_connection_listener(on_connection_change)
    
    # Simulate disconnection
    manager._connected = False
    mock_mt5.terminal_info.return_value = None
    
    # Setup mock for successful reconnection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    mock_mt5.terminal_info.return_value = MagicMock()
    
    # Attempt reconnection
    reconnection_result = manager.reconnect(max_attempts=3)
    
    # Verify reconnection was attempted and succeeded
    assert reconnection_result is True
    assert manager.is_connected() is True
    
    # Verify connection state was tracked
    assert True in connection_states  # At least one successful connection state


@settings(max_examples=50)
@given(creds=credentials_strategy())
@patch('src.mt5_connection.mt5')
def test_reconnection_with_exponential_backoff(mock_mt5, creds):
    """Test that reconnection uses exponential backoff between attempts."""
    account, password, server = creds
    
    # Setup mock for initial connection
    mock_mt5.initialize.return_value = True
    mock_mt5.login.return_value = True
    
    manager = MT5ConnectionManager()
    manager.connect(account, password, server)
    
    # Simulate disconnection
    manager._connected = False
    
    # Setup mock for failed reconnection attempts, then success
    call_count = 0
    def login_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return call_count >= 3  # Fail first 2 attempts, succeed on 3rd
    
    mock_mt5.initialize.return_value = True
    mock_mt5.login.side_effect = login_side_effect
    
    # Attempt reconnection with max 5 attempts
    start_time = time.time()
    result = manager.reconnect(max_attempts=5)
    elapsed_time = time.time() - start_time
    
    # Verify reconnection eventually succeeded
    assert result is True
    # Verify some time elapsed due to backoff (at least 1 second for 2 failed attempts)
    assert elapsed_time >= 1.0
