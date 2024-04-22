import ccxt.async_support as ccxt  # Import asynchronous version of CCXT
from ccxt.base.errors import OrderNotFound, ExchangeError, NetworkError
import logging
import asyncio
from typing import Dict, Any, List, Optional

# Configure basic logging for the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CCXTService:
    """
    A class for interacting with cryptocurrency exchanges using the CCXT library,
    enhanced with asynchronous operations, structured error handling, and logging.

    Attributes:
        exchange_id (str): Identifier for the cryptocurrency exchange.
        api_key (str): API key for the cryptocurrency exchange.
        api_secret (str): API secret for the cryptocurrency exchange.
        exchange (ccxt.Exchange): CCXT exchange instance (async version).
    """

    def __init__(self, exchange_id: str, api_key: str, api_secret: str):
        """Initializes the ccxt client class with exchange details and API credentials."""
        self.exchange_id: str = exchange_id.lower()
        self.api_key: str = api_key
        self.api_secret: str = api_secret
        self.exchange: Optional[ccxt.Exchange] = None

    async def initialize_exchange(self):
        """Asynchronously initializes the exchange with API credentials."""
        if self.exchange is None:  # Check if the exchange has already been initialized
            try:
                exchange_class = getattr(ccxt, self.exchange_id)()
                await exchange_class.load_markets()
                exchange_class.apiKey = self.api_key
                exchange_class.secret = self.api_secret
                exchange_class.enableRateLimit = True
                self.exchange = exchange_class
                logger.info(f"Initialized exchange: {self.exchange_id}")
            except AttributeError:
                logger.error(f"Exchange {self.exchange_id} is not supported by CCXT.")
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred during exchange initialization: {e}")
                raise

    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Processes a trade order based on the given payload."""
        # Extracting order details from the payload
        symbol = payload.get('symbol', '').rstrip('.P')  # Remove trailing '.P' if present
        order_type = payload['type']
        side = payload['order_side']
        amount = payload['order_size']
        price = payload.get('order_price', None)  # Price is only relevant for limit orders


        try:
            # Determine the correct order function based on the order type
            if order_type in ['limit', 'market']:
                logger.info(f"Order received")

                # Using the generalized create_order method for both limit and market orders
                order = await self.exchange.create_order(symbol, order_type, side, amount, price)
                logger.info(f"Order processed successfully: {order}")
                return {"success": True, "order": order}
            else:
                logger.warning(f"Invalid order type: {order_type}")
                raise ValueError("Invalid order type")
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An exchange/network error occurred: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()

    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Fetches a specific order by its ID and symbol."""
        if symbol.endswith('.P'):
            symbol = symbol[:-2]
        try:
            logger.warning(f"Received parameters: {order_id}, {symbol}")
            order = await self.exchange.fetch_order(order_id, symbol)
            logger.info(f"Order fetched successfully: {order}")
            return order
        except OrderNotFound:
            logger.warning(f"Order not found: {order_id}")
            return {"status": "error", "message": "Order not found"}
            
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching the order: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancels an order on the cryptocurrency exchange after ensuring the symbol is in the correct format.

        Parameters:
        - order_id (str): The unique identifier of the order to cancel.
        - symbol (str): The market symbol (e.g., 'BTC/USDT') of the order, with any exchange-specific suffixes removed.

        Returns:
        - Dict[str, Any]: A dictionary with the status of the cancellation and the exchange's response.
        """
        # Format check and cleanup for the symbol
        formatted_symbol = self.format_symbol(symbol)

        if not self.exchange:
            return {"success": False, "error": "Exchange not initialized"}

        try:
            cancellation_result = await self.exchange.cancel_order(order_id, formatted_symbol)
            logger.info(f"Order {order_id} for {formatted_symbol} cancelled successfully.")
            return {"success": True, "result": cancellation_result}
        except OrderNotFound:
            logger.warning(f"Order {order_id} for {formatted_symbol} not found.")
            return {"success": False, "error": "Order not found"}
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An error occurred while cancelling the order {order_id} for {formatted_symbol}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred while cancelling the order {order_id} for {formatted_symbol}: {e}")
            return {"success": False, "error": "An unexpected error occurred"}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()
    

    async def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Fetches details of a specific order by its ID and symbol from the cryptocurrency exchange.

        Parameters:
        - order_id (str): The unique identifier of the order.
        - symbol (str): The market symbol (e.g., 'BTC/USDT') of the order, ensuring it's in the correct format.

        Returns:
        - Dict[str, Any]: A dictionary containing the order details or an error message.
        """
        # Ensure the symbol is in the correct format
        formatted_symbol = self.format_symbol(symbol)

        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        try:
            # Fetch the order from the exchange
            order = await self.exchange.fetch_order(order_id, formatted_symbol)
            logger.info(f"Successfully fetched order {order_id} for {formatted_symbol}.")
            return {"success": True, "order": order}
        except OrderNotFound:
            logger.warning(f"Order {order_id} for {formatted_symbol} not found.")
            return {"success": False, "error": "Order not found"}
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An error occurred while fetching the order {order_id} for {formatted_symbol}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching the order {order_id} for {formatted_symbol}: {e}")
            return {"success": False, "error": "An unexpected error occurred"}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()


    async def fetch_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetches a list of orders for a specific symbol, optionally filtered by timestamp and limited by number.

        Parameters:
        - symbol (Optional[str]): The market symbol (e.g., 'BTC/USDT') to fetch orders for, ensuring it's in the correct format.
        - since (Optional[int]): Timestamp in milliseconds to fetch orders created after a certain time.
        - limit (Optional[int]): The maximum number of orders to fetch.

        Returns:
        - Dict[str, Any]: A dictionary containing the list of orders or an error message.
        """
        if symbol:
            formatted_symbol = self.format_symbol(symbol)
        else:
            formatted_symbol = None  # Fetch orders for all symbols if none is specified

        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        try:
            # Fetch the orders from the exchange
            orders = await self.exchange.fetch_orders(formatted_symbol, since, limit)
            logger.info(f"Successfully fetched orders for {formatted_symbol if formatted_symbol else 'all symbols'}. Orders: {orders}")
            return {"success": True, "orders": orders}
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An error occurred while fetching orders for {formatted_symbol if formatted_symbol else 'all symbols'}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching orders: {e}")
            return {"success": False, "error": "An unexpected error occurred"}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()

    def format_symbol(self, symbol: str) -> str:
        """
        Formats the trading symbol to ensure it's in the correct format for the exchange.

        Parameters:
        - symbol (str): The original symbol that may contain exchange-specific suffixes or formats.

        Returns:
        - str: The formatted symbol without any exchange-specific suffixes.
        """
        # This example removes a specific suffix; adjust as needed
        return symbol.rstrip('.P')


    async def fetch_open_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetches a list of open (active) orders for a specific symbol, optionally filtered by timestamp and limited by number.

        Parameters:
        - symbol (Optional[str]): The market symbol (e.g., 'BTC/USDT') to fetch open orders for, ensuring it's in the correct format.
        - since (Optional[int]): Timestamp in milliseconds to fetch orders created after a certain time.
        - limit (Optional[int]): The maximum number of orders to fetch.

        Returns:
        - Dict[str, Any]: A dictionary containing the list of open orders or an error message.
        """
        if symbol:
            formatted_symbol = self.format_symbol(symbol)
        else:
            formatted_symbol = None  # Fetch open orders for all symbols if none is specified

        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        try:
            # Fetch the open orders from the exchange
            open_orders = await self.exchange.fetch_open_orders(formatted_symbol, since, limit)
            logger.info(f"Successfully fetched open orders for {formatted_symbol if formatted_symbol else 'all symbols'}.")
            return {"success": True, "orders": open_orders}
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An error occurred while fetching open orders for {formatted_symbol if formatted_symbol else 'all symbols'}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching open orders: {e}")
            return {"success": False, "error": "An unexpected error occurred"}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()


    async def fetch_closed_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetches a list of closed (completed or canceled) orders for a specific symbol,
        optionally filtered by timestamp and limited by the number of orders.

        Parameters:
        - symbol (Optional[str]): The market symbol (e.g., 'BTC/USDT') to fetch closed orders for,
                                  ensuring it's in the correct format.
        - since (Optional[int]): Timestamp in milliseconds to fetch orders created after a certain time.
        - limit (Optional[int]): The maximum number of orders to fetch.

        Returns:
        - Dict[str, Any]: A dictionary containing the list of closed orders or an error message.
        """
        if symbol:
            formatted_symbol = self.format_symbol(symbol)
        else:
            formatted_symbol = None  # Fetch closed orders for all symbols if none is specified

        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        try:
            # Fetch the closed orders from the exchange
            closed_orders = await self.exchange.fetch_closed_orders(formatted_symbol, since, limit)
            logger.info(f"Successfully fetched closed orders for {formatted_symbol if formatted_symbol else 'all symbols'}.")
            return {"success": True, "orders": closed_orders}
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An error occurred while fetching closed orders for {formatted_symbol if formatted_symbol else 'all symbols'}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching closed orders: {e}")
            return {"success": False, "error": "An unexpected error occurred"}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()


    async def fetch_my_trades(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetches the trade history for a specific symbol belonging to the user,
        optionally filtered by timestamp and limited by the number of trades.

        Parameters:
        - symbol (Optional[str]): The market symbol (e.g., 'BTC/USDT') to fetch trades for,
                                  ensuring it's in the correct format.
        - since (Optional[int]): Timestamp in milliseconds to fetch trades executed after a certain time.
        - limit (Optional[int]): The maximum number of trades to fetch.

        Returns:
        - Dict[str, Any]: A dictionary containing the list of trades or an error message.
        """
        if symbol:
            formatted_symbol = self.format_symbol(symbol)
        else:
            formatted_symbol = None  # Fetch trades for all symbols if none is specified

        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        try:
            # Fetch the user's trades from the exchange
            my_trades = await self.exchange.fetch_my_trades(formatted_symbol, since, limit)
            logger.info(f"Successfully fetched my trades for {formatted_symbol if formatted_symbol else 'all symbols'}.")
            return {"success": True, "trades": my_trades}
        except (ExchangeError, NetworkError) as e:
            logger.error(f"An error occurred while fetching my trades for {formatted_symbol if formatted_symbol else 'all symbols'}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching my trades: {e}")
            return {"success": False, "error": "An unexpected error occurred"}
        finally:
            # Close the exchange to release all resources
            await self.exchange.close()


    async def fetch_positions(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetches open positions for specified symbols if the exchange supports it.

        Parameters:
        - symbols (Optional[List[str]]): A list of market symbols (e.g., ['BTC/USDT', 'ETH/USDT']) to fetch positions for.
                                         If None, fetches positions for all symbols.

        Returns:
        - Dict[str, Any]: A dictionary containing the list of open positions or an error message.
        """
        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        if self.exchange.has['fetchPositions']:
            try:
                # Fetch the open positions from the exchange
                if symbols is None:
                    positions = await self.exchange.fetch_positions()
                else:
                    positions = [await self.exchange.fetch_positions(symbol) for symbol in symbols]
                logger.info(f"Successfully fetched open positions. {positions}")
                return {"success": True, "positions": positions}
            except (ExchangeError, NetworkError) as e:
                logger.error(f"An error occurred while fetching positions: {e}")
                return {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(f"An unexpected error occurred while fetching positions: {e}")
                return {"success": False, "error": "An unexpected error occurred"}
            finally:
                # Close the exchange to release all resources
                await self.exchange.close()
        else:
            logger.warning("This exchange does not support fetching positions.")
            return {"success": False, "error": "Fetching positions is not supported by this exchange"}


    async def fetch_position(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches details of an open position for a specific symbol if the exchange supports it.

        Parameters:
        - symbol (str): The market symbol (e.g., 'BTC/USDT') to fetch the position for.

        Returns:
        - Dict[str, Any]: A dictionary containing the details of the open position or an error message.
        """
        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        # Check if the exchange supports fetching individual positions
        if self.exchange.has['fetchPosition']:
            try:
                if symbol:
                    formatted_symbol = self.format_symbol(symbol)
                else:
                    formatted_symbol = None  # Fetch closed orders for all symbols if none is specified
                # Fetch the open position from the exchange
                position = await self.exchange.fetch_positions(formatted_symbol)
                logger.info(f"Successfully fetched position for {formatted_symbol}.")
                return {"success": True, "position": position}
            except (ExchangeError, NetworkError) as e:
                logger.error(f"An error occurred while fetching the position for {formatted_symbol}: {e}")
                return {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(f"An unexpected error occurred while fetching the position for {formatted_symbol}: {e}")
                return {"success": False, "error": "An unexpected error occurred"}
            finally:
                # Close the exchange to release all resources
                await self.exchange.close()
        else:
            logger.warning("Fetching individual positions is not supported by this exchange.")
            return {"success": False, "error": "Fetching individual positions is not supported by this exchange"}


    async def create_position_if_supported(self, symbol: str, type: str, side: str, amount: float, price: Optional[float] = None, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Attempts to create a position directly if the exchange supports it, otherwise places an order that opens a new position.

        Parameters:
        - symbol (str): The market symbol (e.g., 'BTC/USDT').
        - type (str): Order type ('market' or 'limit').
        - side (str): Order side ('buy' to open a long position or 'sell' to open a short position).
        - amount (float): Amount of the asset to trade.
        - price (Optional[float]): Price per asset (required for limit orders).
        - params (Dict[str, Any]): Additional parameters specific to the exchange.

        Returns:
        - Dict[str, Any]: A dictionary containing the order details or an error message.
        """
        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        if self.exchange.has['createPosition']:
            try:
                # Directly create a position if the exchange supports it
                position = await self.exchange.create_position(symbol, type, side, amount, price, params)
                logger.info(f"Position created successfully for {symbol}.")
                return {"success": True, "position": position}
            except Exception as e:
                logger.error(f"An error occurred while creating the position for {symbol}: {e}")
                return {"success": False, "error": str(e)}
            finally:
                # Close the exchange to release all resources
                await self.exchange.close()
        else:
            # Fallback to placing an order that opens a position
            try:
                order = await self.create_order(symbol, type, side, amount, price, params)
                logger.info(f"Order placed successfully for {symbol}, which may open a position.")
                return {"success": True, "order": order}
            except Exception as e:
                logger.error(f"An error occurred while placing the order for {symbol}: {e}")
                return {"success": False, "error": str(e)}
            finally:
                # Close the exchange to release all resources
                await self.exchange.close()
            

    async def set_leverage(self, leverage: int, symbol: str) -> Dict[str, Any]:
        """
        Sets the leverage for a specific symbol if the exchange supports it.

        Parameters:
        - leverage (int): The leverage to set (e.g., 10 for 10x leverage).
        - symbol (str): The market symbol (e.g., 'BTC/USDT') to set leverage for.

        Returns:
        - Dict[str, Any]: A dictionary indicating whether the operation was successful or containing an error message.
        """
        if not self.exchange:
            logger.error("Exchange not initialized.")
            return {"success": False, "error": "Exchange not initialized"}

        # Check if the exchange supports setting leverage
        if 'setLeverage' in self.exchange.has and self.exchange.has['setLeverage']:
            try:
                # Attempt to set the leverage
                await self.exchange.set_leverage(leverage, symbol)
                logger.info(f"Leverage set to {leverage}x for {symbol}.")
                return {"success": True, "message": f"Leverage set to {leverage}x for {symbol}."}
            except Exception as e:
                logger.error(f"An error occurred while setting leverage for {symbol}: {e}")
                return {"success": False, "error": str(e)}
            finally:
                # Close the exchange to release all resources
                await self.exchange.close()
        else:
            return {"success": False, "error": "Setting leverage is not supported by this exchange"}



# Trading
# create_order(symbol, type, side, amount, price=None, params={}): Places a new order.
# cancel_order(id, symbol=None, params={}): Cancels an order.
# fetch_order(id, symbol=None, params={}): Fetches details of an order.
# fetch_orders(symbol=None, since=None, limit=None, params={}): Fetches a list of orders for a symbol.
# fetch_open_orders(symbol=None, since=None, limit=None, params={}): Fetches open orders.
# fetch_closed_orders(symbol=None, since=None, limit=None, params={}): Fetches closed orders.
# fetch_my_trades(symbol=None, since=None, limit=None, params={}): Fetches trades for a specific account and symbol.


# fetchPosition: Fetches the details of a single open position for a given symbol. This function is useful for getting the current state of a position, including unrealized profit and loss, entry price, and current margin.

# fetchPositions: Fetches all open positions for the account. This is similar to fetch_positions mentioned previously and provides an overview of all current positions held by the trader.

# createPosition: Some exchanges might allow directly opening a position through their API. This function would typically require details such as symbol, amount, leverage, and whether it's a long or short position.

# editPosition: Allows for modifying an existing open position. Modifications can include changing the amount, leverage, or adding a stop-loss or take-profit level.

# closePosition: Closes an open position for a given symbol. This might be implemented by placing a counter-order to nullify the position or by using an exchange-specific API call to close the position directly.

# setPositionMode: For exchanges that support different position modes (such as "hedged" or "one-way" modes in futures trading), this function allows the trader to switch between these modes.

# fetchPositionRisk: Fetches risk-related information for open positions, such as liquidation price, maintenance margin requirements, and current leverage level.

# reducePosition: Allows partially closing an open position by specifying the amount to reduce. This is useful for managing risk or taking partial profits.

# fetchLeverageTiers: Retrieves information about available leverage tiers and their corresponding margin requirements. This is important for understanding how much leverage can be applied to positions and the associated risks.