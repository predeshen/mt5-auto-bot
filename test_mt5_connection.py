"""Quick MT5 Connection Test Script"""

import MetaTrader5 as mt5
import json

print("=" * 60)
print("MT5 CONNECTION DIAGNOSTIC TEST")
print("=" * 60)

# Step 1: Check if MT5 is installed
print("\n1. Checking MT5 installation...")
try:
    import MetaTrader5
    print("   ✅ MetaTrader5 package installed")
except ImportError:
    print("   ❌ MetaTrader5 package NOT installed")
    print("   Run: pip install MetaTrader5")
    exit(1)

# Step 2: Try to initialize MT5
print("\n2. Initializing MT5 terminal...")
if not mt5.initialize():
    error = mt5.last_error()
    print(f"   ❌ MT5 initialization failed: {error}")
    print("\n   Possible causes:")
    print("   - MT5 terminal is not running")
    print("   - MT5 terminal is not installed")
    print("   - MT5 terminal path is not in system PATH")
    print("\n   Solutions:")
    print("   1. Open MT5 terminal manually")
    print("   2. Make sure it's running")
    print("   3. Try again")
    exit(1)
else:
    print("   ✅ MT5 initialized successfully")

# Step 3: Get terminal info
print("\n3. Terminal Information:")
terminal_info = mt5.terminal_info()
if terminal_info:
    print(f"   Company: {terminal_info.company}")
    print(f"   Name: {terminal_info.name}")
    print(f"   Path: {terminal_info.path}")
    print(f"   Build: {terminal_info.build}")
    print(f"   Connected: {terminal_info.connected}")
else:
    print("   ⚠️  Could not get terminal info")

# Step 4: Load config and test login
print("\n4. Testing saved credentials...")
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    accounts = config.get('accounts', {})
    
    for key, acc in accounts.items():
        print(f"\n   Testing: {acc['name']}")
        print(f"   Account: {acc['account']}")
        print(f"   Server: {acc['server']}")
        
        # Try to login
        authorized = mt5.login(
            login=acc['account'],
            password=acc['password'],
            server=acc['server']
        )
        
        if authorized:
            print(f"   ✅ Login successful!")
            
            # Get account info
            account_info = mt5.account_info()
            if account_info:
                print(f"   Balance: {account_info.balance} {account_info.currency}")
                print(f"   Equity: {account_info.equity} {account_info.currency}")
                print(f"   Leverage: 1:{account_info.leverage}")
        else:
            error = mt5.last_error()
            print(f"   ❌ Login failed: {error}")
            print(f"   Error code: {error[0]}")
            
            if error[0] == -6:
                print("\n   Common causes for error -6 (Authorization failed):")
                print("   1. Wrong password")
                print("   2. Wrong server name")
                print("   3. Account is disabled/expired")
                print("   4. Need to login manually in MT5 terminal first")
                print("\n   Try this:")
                print("   1. Open MT5 terminal")
                print("   2. Login manually with these credentials")
                print("   3. If it works in terminal, try this script again")
                print("   4. If it doesn't work in terminal, update your password")

except FileNotFoundError:
    print("   ❌ config.json not found")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Step 5: List available servers
print("\n5. Available Servers:")
print("   (These are the servers your MT5 terminal knows about)")
print("   If your server isn't listed, you need to add it in MT5 terminal first.")

# Unfortunately, there's no direct API to list servers
# User needs to check in MT5 terminal: Tools -> Options -> Server

print("\n   To see available servers:")
print("   1. Open MT5 terminal")
print("   2. Go to: Tools -> Options -> Server tab")
print("   3. Check the server name exactly as shown")
print("   4. Update config.json if needed")

# Cleanup
mt5.shutdown()

print("\n" + "=" * 60)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 60)
print("\nNext steps:")
print("1. If login failed, try logging in manually in MT5 terminal first")
print("2. Check that the server name in config.json matches exactly")
print("3. Update password in config.json if it changed")
print("4. Run this script again to verify")
