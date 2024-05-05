from datetime import datetime
import logging
from typing import Any, Dict
from apps.trading.ccxt_client import CCXTService
from apps.trading.models import Order, Position, TradingBot
from apps import db

logger = logging.getLogger(__name__)

class TradingService:

    @staticmethod
    def list_bots(user_id):
        """ Retrieve all trading bots associated with a given user ID and return them in a standardized format. """
        try:
            bots = TradingBot.query.filter_by(user_id=user_id).all()
            bots_data = [bot.to_dict() for bot in bots]  # Convert each bot instance to a dictionary
            return {'status': 'success', 'message': 'Bots retrieved successfully.', 'data': bots_data}
        except Exception as e:
            logger.error(f'Error retrieving bots for user {user_id}: {str(e)}')
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def create_bot(user_id, strategy_id, exchange_account_id, bot_name):
        """ Create a new trading bot and save it to the database """
        try:
            new_bot = TradingBot(
                user_id=user_id,
                strategy_id=strategy_id,
                exchange_account_id=exchange_account_id,
                name=bot_name,
                created_at=datetime.utcnow()
            )
            db.session.add(new_bot)
            db.session.commit()
            return {'status': 'success', 'message': 'Trading bot created successfully.'}
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating bot: {str(e)}')
            return {'status': 'error', 'message': 'Failed to create trading bot.'}
        
    @staticmethod
    def get_bot(bot_id):
        """ Retrieve a single trading bot by its ID with standardized error handling. """
        try:
            bot = TradingBot.query.get(bot_id)
            if bot:
                return {'status': 'success', 'message': bot.to_dict()}
            else:
                return {'status': 'error', 'message': 'Bot not found.'}
        except Exception as e:
            logger.error(f'Failed to retrieve bot {bot_id}: {str(e)}')
            return {'status': 'error', 'message': str(e)}
        
    @staticmethod
    async def process_order(payload: Dict[str, Any]) -> Dict[str, Any]:
        # Check if the payload provided is indeed a dictionary as expected
        if not isinstance(payload, dict):
            logger.error("Trade details should be a dictionary")
            return {'status': 'error', 'message': 'Invalid trade details format'}
        
        symbol = payload['symbol']
        order_type = payload['type']
        side = payload['order_side']
        quantity = float(payload['order_size'])
        order_price = float(payload['order_price']) if payload['order_price'] else None
        pos_type = payload['pos_type']
        order_id = payload['order_id']
        params = payload['params']
        time = payload['time']
        exchange = payload['exchange']
        pos_size = payload['pos_size']
        timeframe = payload['timeframe']
        bot_name = payload['bot_name']

        ccxt_client = None
        try:
            # Extract details, find bot and account, initialize exchange
            bot_id = str(payload['bot_id'])  # Casting to string in case it's not
            logger.info(f"Bot ID: {bot_id}")

            bot = TradingBot.query.get(bot_id)
            if not bot:
                return {'status': 'error', 'message': 'Trading bot not found'}

            logger.info(f"Bot ID: {bot.id}")

            account = bot.account
            ccxt_client = CCXTService(account.exchange.name, account.api_key, account.api_secret)
            await ccxt_client.initialize_exchange()  # Properly await the asynchronous initialization


            # Get or create the associated position
            position = Position.query.filter_by(symbol=payload['symbol'], trading_bot_id=payload['bot_id'], status='open').first()
            is_new_position = False
            if not position:
                position = Position(
                    trading_bot_id=payload['bot_id'],
                    symbol=payload['symbol'],
                    pos_type=payload['pos_type'],
                    average_entry_price=payload['order_price'] if payload['order_side'] == 'buy' else None,
                    position_size=payload['pos_size'],
                    status='open'
                )
                db.session.add(position)
                db.session.flush()
                is_new_position = True
            
            # Create and execute the order
            order = Order(
                order_id=order_id,
                position_id=position.id,
                symbol=symbol,
                order_type=order_type,
                side=side,
                quantity=quantity,
                entry_price=order_price,
                status='filled',  # Default status before execution
                created_at=time,
                bot_id=bot_id,
                bot_name=bot_name,
                exchange=exchange,
                pos_size=pos_size,
                pos_type=pos_type,
                timeframe=timeframe,
                params=params
            )
            db.session.add(order)
            db.session.flush()  # Necessary to ensure the order is persisted before calculation

            # Only update position if it wasn't newly created
            if not is_new_position:
                position.update_position(order)
            position.calculate_profit_loss(order, account.maker_fee)  # Calculate profit/loss upon order execution regardless of new or existing

            db.session.commit()

            return {'status': 'success', 'message': 'Order executed and position updated.', 'order_id': order.id}
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}
        finally:
            if ccxt_client and ccxt_client.exchange:
                await ccxt_client.exchange.close()  # Properly close the exchange


    @staticmethod
    def activate_bot(bot_id):
        # Logic to activate a bot
        pass

    @staticmethod
    def deactivate_bot(bot_id):
        # Logic to deactivate a bot
        pass

    @staticmethod
    def update_bot_settings(bot_id, **settings):
        # Logic to update bot settings
        pass

    @staticmethod
    def delete_bot(bot_id):
        """ Deletes a bot from the database """
        try:
            bot = TradingBot.query.get(bot_id)
            if not bot:
                return {'status': 'error', 'message': 'Bot not found.'}
            db.session.delete(bot)
            db.session.commit()
            return {'status': 'success', 'message': 'Bot deleted successfully.'}
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error deleting bot: {str(e)}')
            return {'status': 'error', 'message': 'Failed to delete bot.'}

    @staticmethod
    def place_order(bot_id, symbol, order_type, side, quantity, entry_price=None):
        # Logic to place an order
        pass

    @staticmethod
    def execute_order(order_id, execution_price):
        # Logic to execute an order
        pass

    @staticmethod
    def cancel_order(order_id):
        # Logic to cancel an order
        pass

    @staticmethod
    def open_position(order_id):
        # Logic to open a position based on an order
        pass

    @staticmethod
    def close_position(position_id, closing_price):
        # Logic to close a position
        pass

    @staticmethod
    def generate_alert(bot_id, message, alert_type, severity='info'):
        # Logic to generate a new alert
        pass

    @staticmethod
    def dismiss_alert(alert_id):
        # Logic to dismiss an alert
        pass

    @staticmethod
    def view_alert(alert_id):
        # Logic to mark an alert as viewed
        pass
