from binance.client import Client

# Initialize the client with your Testnet keys
api_key = ''
api_secret = ''
client = Client(api_key, api_secret, testnet=True)  # Critical for Testnet

def test_api_connection():
    print("=== Testing Binance Testnet API Connection ===\n")
    
    try:
        # Test 1: Basic Connection & Server Time
        print("1. Testing server connection...")
        server_time = client.get_server_time()
        print(f"   ✅ Server time: {server_time['serverTime']}")
        
        # Test 2: Market Data
        print("2. Testing market data...")
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        print(f"   ✅ Current BTC Price: {ticker['price']}")
        
        # Test 3: Account Info
        print("3. Testing account info...")
        account = client.get_account()
        free_balances = [bal for bal in account['balances'] if float(bal['free']) > 0]
        print(f"   ✅ Account has {len(free_balances)} assets with free balance.")
        for bal in free_balances:
            print(f"      - {bal['asset']}: {bal['free']}")
        
        # Test 4: Placing a Test Order
        print("4. Testing order placement...")
        # This is a LIMIT order that's unlikely to fill, just to test permissions.

        # NEU (Korrektur):
        test_order = client.create_order(
            symbol='BTCUSDT',
            side='BUY', 
            type='LIMIT',
            timeInForce='GTC',
            quantity=0.001,
            price='110000'  # ✅ Nahe am aktuellen Preis (~110,268)
        )
        print(f"   ✅ Test order placed! Order ID: {test_order['orderId']}")
        
        # Check open orders
        open_orders = client.get_open_orders(symbol='BTCUSDT')
        print(f"   ✅ Open orders check: {len(open_orders)} order(s) open.")
        
        # Cancel the test order
        cancel_result = client.cancel_order(symbol='BTCUSDT', orderId=test_order['orderId'])
        print(f"   ✅ Test order canceled.")
        
        print("\n🎉 All tests passed! Your API key is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        # This helps pinpoint where the failure occurred
        import traceback
        traceback.print_exc()

if __name__ == "__main__":

    test_api_connection()
