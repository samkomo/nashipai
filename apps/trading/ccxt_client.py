"""
ccxt_client.py

This module provides a class (TradingModule) for interacting with different cryptocurrency exchanges
using the CCXT library. It includes methods for setting up exchanges, fetching trades, creating orders,
and getting orders by ID.
"""

from datetime import datetime, timedelta
import json
import ccxt
import os

class TradingModule:
    """
    Class for a trading module to interact with different exchanges
    """
    def __init__(self):
        """
        Initialize the trading module
        """
        self.exchanges = {}
        self.setup_exchanges()

    """
    Sets up exchanges using configuration from a config file.
    
    Parameters:
    - subaccount (str): The subaccount to use, if any. Defaults to None.
    """
    def setup_exchanges(self, subaccount=None, sandbox_mode=True):
        # Fetch the list of supported exchanges from the environment variable and split it
        supported_exchanges = os.environ.get('SUPPORTED_EXCHANGES', '').split(',')

        for exchange_id in supported_exchanges:
            # Fetch API key and secret for the given exchange_id from environment variables
            api_key = os.environ.get(f'{exchange_id.upper()}_API_KEY')
            api_secret = os.environ.get(f'{exchange_id.upper()}_API_SECRET')
            
            # If there's a subaccount, try to fetch its specific API key and secret
            subaccount_api_key = os.environ.get(f'{exchange_id.upper()}_{subaccount}_API_KEY', api_key)
            subaccount_api_secret = os.environ.get(f'{exchange_id.upper()}_{subaccount}_API_SECRET', api_secret)

            # Use the CCXT library to create an exchange object
            exchange_class = getattr(ccxt, exchange_id.lower())
            exchange = exchange_class({
                'apiKey': subaccount_api_key,
                'secret': subaccount_api_secret,
                'enableRateLimit': True,
                'verbose': True
            })

            # Activates testnet mode
            # exchange.set_sandbox_mode(sandbox_mode)

            self.exchanges[exchange_id] = exchange
    """
    Fetches trades from a specific exchange.

    Parameters:
    - exchange_id (str): The ID of the exchange to fetch trades from.
    - symbol (str): The trading pair to fetch trades for. Defaults to 'BTC/USDT'.
    """
    def get_trades(self, exchange_id, symbol='BTC/USDT'):

        try:
            exchange = self.exchanges.get(exchange_id)
            trades = exchange.fetch_trades(symbol, limit=10)
            return trades
        except Exception as e:
            print(f"Failed to fetch trades from {exchange_id}: {e}")
            return None
    """
    Fetches personal trades from a specific exchange.

    Parameters:
    - exchange_id (str): The ID of the exchange to fetch trades from.
    - symbol (str): The trading pair to fetch trades for. Defaults to 'BTC/USDT'.
    """
    def get_my_trades(self, exchange_id, symbol='BTC/USDT'):

        try:
            exchange = self.exchanges.get(exchange_id)
            trades = exchange.fetch_my_trades(symbol, limit=10)
            return trades
        except Exception as e:
            print(f"Failed to fetch personal trades from {exchange_id}: {e}")
            json_string = json.dumps({"errorCode": "get_trades_error", "status": str(e)})
            response_json = json.loads(e)
            return response_json
    """
    Creates an order on a specific exchange.

    Parameters:
    - exchange_id (str): The ID of the exchange to create the order on.
    - payload (dict): The parameters for the order.
    """
    def create_order(self, exchange_id, payload):
        try:
            exchange = self.exchanges.get(exchange_id)
            # Check if the order should use Good Till Time (GTT)
            if payload.get('time_in_force') == 'GTT':
                # Calculate expire time based on the 'expireAfter' parameter in payload
                expire_after_minutes = payload.get('expire_after', 30)
                expire_time = datetime.utcnow() + timedelta(minutes=expire_after_minutes)
                # Set timeInForce and expireTime parameters
                payload['params']['timeInForce'] = 'GTT'
                payload['params']['expireTime'] = int(expire_time.timestamp())
                print(json.dumps(payload, indent=2))
            # execute create order
            order = exchange.create_order(
                payload['symbol'],
                payload['type'],
                payload['side'],
                payload['size'],
                payload['price'],
                params=payload['params']
            )
            return order
        except Exception as e:
            print(f"Failed to create order on {exchange_id}: {e}")
            json_string = json.dumps({"status":"Error","errorCode": "create_trade_error", "message": str(e)})
            response_json = json.loads(json_string)
            return response_json
    """
    Fetches orders from a specific exchange.

    Parameters:
    - exchange_id (str): The ID of the exchange to fetch orders from.
    - symbol (str): The trading pair to fetch orders for. If None, fetches all orders.
    """
    def get_orders(self, exchange_id, symbol=None):
        try:
            exchange = self.exchanges.get(exchange_id)
            if symbol:
                orders = exchange.fetch_positions(symbol)
            else:
                orders = exchange.fetch_positions()
            return orders
        except Exception as e:
            print(f"Failed to fetch orders from {exchange_id}: {e}")
            return json.dumps({"errorCode": "create_order_error", "status": str(e)})

    """
    Fetches a specific order by its ID.

    Parameters:
    - exchange_id (str): The ID of the exchange to fetch the order from.
    - order_id (str): The ID of the order to fetch.
    - symbol (str): The trading pair of the order. Defaults to 'BTCUSDT'.
    """
    def get_order_by_id(self, exchange_id, order_id, symbol="BTCUSDT"):

        try:
            exchange = self.exchanges.get(exchange_id)
            order = exchange.fetch_order(order_id, symbol)
            return order
        except ccxt.OrderNotFound as e:
            error_message = f"Order {order_id} does not exist."
            print(f"Error retrieving order: {error_message}")
            return json.dumps({"errorCode": "order_not_found", "status": f"Order {order_id} does not exist."})
        except Exception as e:
            print(f"Failed to fetch order from {exchange_id}: {e}")
            return json.dumps({"errorCode": "get_order_by_id_error", "status": str(e)})
