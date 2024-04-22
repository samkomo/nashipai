import ccxt
from datetime import datetime

class CCXTServiceB:
    def __init__(self, exchange_id, api_key, api_secret):
        self.exchange = getattr(ccxt, exchange_id)({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True  # Important to respect the API rate limits to avoid bans.
        })

    def fetch_balance(self):
        """Fetches the balance from the exchange."""
        try:
            return self.exchange.fetch_balance()
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def create_order(self, symbol, type, side, amount, price=None):
        """Creates an order on the exchange."""
        try:
            return self.exchange.create_order(symbol, type, side, amount, price)
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def cancel_order(self, order_id):
        """Cancels an order on the exchange."""
        try:
            return self.exchange.cancel_order(order_id)
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def fetch_order(self, order_id):
        """Fetches details of a specific order."""
        try:
            return self.exchange.fetch_order(order_id)
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def fetch_ticker(self, symbol):
        """Fetches the current ticker for a symbol."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def fetch_market_data(self, symbol):
        """Fetches detailed market data for the given symbol."""
        try:
            return self.exchange.fetch_ohlcv(symbol, '1d')  # Example: Daily data
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def check_exchange_status(self):
        """Checks the operational status of the exchange."""
        try:
            status = self.exchange.fetch_status()
            return status['status']
        except ccxt.BaseError as e:
            return {'error': str(e)}

    def list_markets(self):
        """Lists all markets on the exchange."""
        try:
            return self.exchange.load_markets()
        except ccxt.BaseError as e:
            return {'error': str(e)}

