"""
ccxt_client.py

This module provides a class (TradingModule) for interacting with different cryptocurrency exchanges
using the CCXT library. It includes methods for setting up exchanges, fetching trades, creating orders,
and getting orders by ID.
"""

import json
import ccxt
from apps.config import config_dict

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
    def setup_exchanges(self, subaccount=None):

        exchanges_config = config_dict['Production'].EXCHANGES

        for exchange_id, exchange_config in exchanges_config.items():
            try:
                subaccount_config = exchange_config.get('SUBACCOUNT', {}).get(subaccount)

                if subaccount_config:
                    api_key = subaccount_config['API_KEY']
                    api_secret = subaccount_config['API_SECRET']
                else:
                    api_key = exchange_config['API_KEY']
                    api_secret = exchange_config['API_SECRET']

                # Print out the subaccount configuration for debugging
                print(json.dumps(subaccount_config, indent=2))

                # Use the CCXT library to create an exchange object
                exchange_class = getattr(ccxt, exchange_id.lower())
                exchange = exchange_class({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'verbose': True
                })

                # Activates testnet mode
                exchange.set_sandbox_mode(True)

                self.exchanges[exchange_id] = exchange
            except Exception as e:
                return json.dumps({"errorCode": "setup_error", "status": str(e)})
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
            json_string = json.dumps({"errorCode": "get_my_trades_error", "status": str(e)})
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
            print(json.dumps(orders, indent=2))
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
