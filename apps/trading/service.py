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
        
        ccxt_client = None
        try:
            # Extract details, find bot and account, initialize exchange
            bot_id = str(payload['bot_id'])  # Casting to string in case it's not
            logger.info(f"Bot ID: {bot_id}")

            bot = TradingBot.query.get(bot_id)
            if not bot:
                return {'status': 'error', 'message': 'Trading bot not found'}
            # if bot.user_id != user_id:
            #     return {'status': 'error', 'message': 'Current user is not authorized to run this bot'}

            logger.info(f"Bot ID: {bot.id}")

            account = bot.account
            ccxt_client = CCXTService(account.exchange.name, account.api_key, account.secret_key)
            await ccxt_client.initialize_exchange()  # Properly await the asynchronous initialization

            symbol = payload['symbol']
            order_type = payload['type']
            side = payload['order_side']
            amount = float(payload['order_size'])
            price = float(payload['order_price']) if payload['order_price'] else None
            pos_type = payload['pos_type']
            pos_size = payload['pos_size']

            
            # Create order on the exchange
            # order = await ccxt_client.create_order(payload)
            # logger.info(f"Order created: {order.id}")
            

            # Manage Position Logic
            position = Position.query.filter_by(trading_bot_id=bot.id, symbol=symbol, status='open').first()
            if not position:
                if pos_type == 'flat':
                    # Cannot close a non-existent position
                    return {'status': 'error', 'message': 'No open position to close'}
                # Create a new position if it does not exist and it's not a closure request
                position = Position(
                    trading_bot_id=bot.id,
                    symbol=symbol,
                    status='open',
                    position_type=pos_type,
                    quantity=amount,
                    average_entry_price=price,  # Initialize with the first price if it's a new position
                    current_price=price
                )
                # Position(trading_bot_id=bot.id, symbol=symbol, position_type=pos_type, average_entry_price=price, quantity=amount)
            else:
                # Update existing position
                if pos_type == 'flat':
                    # Closing the position
                    position.status = 'closed'
                    position.closed_at = datetime.utcnow()
                    position.current_price = price
                    # Calculate PnL
                    # if position.position_type == 'long':
                    #     position.pnl = (price - position.average_entry_price) * position.quantity
                    # elif position.position_type == 'short':
                    #     position.pnl = (position.average_entry_price - price) * position.quantity
                else:
                    # Adjust position size and recalculate average price
                    if side == 'buy':
                        if position.position_type == 'long':
                            # total_quantity = position.quantity + amount
                            # if total_quantity > 0:
                            position.average_entry_price = (position.average_entry_price * position.quantity + price * amount) / total_quantity
                            # position.quantity = total_quantity
                        # elif position.position_type == 'short':
                            # position.quantity -= amount
                    elif side == 'sell':
                        # if position.position_type == 'long':
                            # position.quantity -= amount
                        # elif position.position_type == 'short':
                            # total_quantity = position.quantity - amount
                            # if total_quantity < 0:
                            position.average_entry_price = (position.average_entry_price * -position.quantity + price * amount) / -total_quantity
                            # position.quantity = total_quantity

            # Save the updated position to the database
            db.session.add(position)
            # Commit changes to the database
            db.session.commit()
                
            # Save the order details
            new_order = Order(
                position_id=position.id if position else None,
                symbol=symbol,
                order_type=order_type,
                side=side,
                quantity=amount,
                entry_price=price,
                status= "Executed" #order['status']
            )
            db.session.add(new_order)
            db.session.commit()

            return {'status': 'success', 'message': 'Order executed and position updated.', 'order_id': new_order.id}
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
