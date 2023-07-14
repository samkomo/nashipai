# ccxt_client.py

import json
import ccxt
from apps.config import config_dict

class TradingModule:
    def __init__(self):
        self.exchanges = {}
        self.setup_exchanges()

    def setup_exchanges(self):
        exchanges_config = config_dict['Production'].EXCHANGES

        for exchange_id, exchange_config in exchanges_config.items():
            api_key = exchange_config['API_KEY']
            api_secret = exchange_config['API_SECRET']

            exchange_class = getattr(ccxt, exchange_id.lower())
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'verbose': True
            })
            exchange.set_sandbox_mode(True) # activates testnet mode


            self.exchanges[exchange_id] = exchange

    def get_trades(self, exchange_id, symbol='BTC/USDT'):
        exchange = self.exchanges.get(exchange_id)
        print("==============================")
        print(json.dumps(exchange.load_markets(), indent=2))
        trades = exchange.fetch_trades(symbol, limit=10)
        return trades

    def get_my_trades(self, exchange_id, symbol='BTC/USDT'):
        exchange = self.exchanges.get(exchange_id)
        print("==============================")
        print(json.dumps(symbol, indent=2))
        trades = exchange.fetch_my_trades(symbol, limit=10)
        return trades
    
    def create_order(self, exchange_id, payload):
        exchange = self.exchanges.get(exchange_id)
        print("==============================")
        print(json.dumps(exchange_id, indent=2))
        order = exchange.create_order(payload['symbol'], payload['type'], payload['side'], payload['size'], payload['price'], params = payload['params'])
        return order

    def get_orders(self, exchange_id, symbol=None):
        exchange = self.exchanges.get(exchange_id)

        if symbol:
            orders = exchange.fetch_positions(symbol)
        else:
            orders = exchange.fetch_positions()

        print(json.dumps(orders, indent=2))

        return orders
