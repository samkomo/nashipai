from datetime import datetime
from decimal import Decimal, getcontext, ROUND_HALF_UP
import logging
from typing import Any, Dict
import uuid
from apps.trading.ccxt_client import CCXTService
from apps.trading.models import Order, Position, TradingBot
from apps import db

logger = logging.getLogger(__name__)
# Set decimal precision to avoid floating-point precision errors
getcontext().prec = 28


class TradingService:

    @staticmethod
    def list_bots(user_id):
        """ Retrieve all trading bots associated with a given user ID and return them in a standardized format. """
        try:
            bots = TradingBot.query.filter_by(user_id=user_id).all()
            bots_data = [bot.to_dict() for bot in bots]  # Convert each bot instance to a dictionary

            # Calculate total profit/loss and percentage
            total_profit_loss = sum(bot.total_profit_loss for bot in bots)
            total_percent_profit_loss = sum(bot.total_percent_profit_loss for bot in bots)  # / len(bots) if bots else 0
            
            # Calculate total balance, ensuring each account is only counted once
            seen_accounts = set()
            total_balance = 0
            for bot in bots:
                if bot.account.id not in seen_accounts:
                    total_balance += bot.account.balance
                    seen_accounts.add(bot.account.id)

            total_percent_profit_daily = sum(bot.percent_profit_daily for bot in bots)
            total_percent_profit_monthly = sum(bot.percent_profit_monthly for bot in bots)
            total_profit_loss_daily = sum(bot.profit_loss_daily for bot in bots)
            total_profit_loss_monthly = sum(bot.profit_loss_monthly for bot in bots)

            # Create a new dictionary to store total data
            totals = {
                'total_profit_loss': total_profit_loss,
                'total_percent_profit_loss': total_percent_profit_loss,
                'total_balance': total_balance,
                'percent_profit_daily': total_percent_profit_daily,
                'percent_profit_monthly': total_percent_profit_monthly,
                'profit_loss_daily': total_profit_loss_daily,
                'profit_loss_monthly': total_profit_loss_monthly,
            }


            # Append totals to the bot_data list
            all_data = {
                'bots': bots_data,
                'totals': totals
            }
            return {'status': 'success', 'message': 'Bots retrieved successfully.', 'data': all_data}
        except Exception as e:
            logger.error(f'Error retrieving bots for user {user_id}: {str(e)}')
            return {'status': 'error', 'message': str(e)}

        finally:
            db.session.remove()  # Ensure the session is closed after processing



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
        
        finally:
            db.session.remove()  # Ensure the session is closed after processing

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
        
        finally:
            db.session.remove()  # Ensure the session is closed after processing

    @staticmethod
    async def process_order(data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Step 1: Get Bot and Strategy
            bot = TradingService.get_trading_bot(data['bot_id'])
            if not bot:
                raise ValueError("Trading bot not found")

            # Step 2: Parse Signal Data
            parsed_data = TradingService.parse_signal(data)

            # Step 3: Execute Order
            order = TradingService.execute_order(parsed_data, bot)

            # Step 4: Update Position
            position = TradingService.update_position(bot.id, parsed_data, order)

            # Step 5: Commit Order with Position ID
            order.position_id = position.id
            db.session.add(order)
            db.session.commit()

            # Step 6: Calculate PnL
            TradingService.calculate_pnl(position, parsed_data['order_price'], parsed_data['order_side'])

            # Step 7: Manage Risk (Optional)
            TradingService.manage_risk(parsed_data, position)

            # Step 8: Notify
            TradingService.send_notifications(parsed_data, order)

            return {'status': 'success', 'message': 'Order executed successfully', 'order': order.to_dict(), 'position': position.to_dict()}

        except Exception as e:
            logger.error(f"Exception in process_order: {str(e)}")
            db.session.rollback()
            return {'status': 'error', 'message': str(e)}

        finally:
            db.session.remove()  # Ensure the session is closed after processing

    @staticmethod
    def get_trading_bot(bot_id: int) -> TradingBot:
        return TradingBot.query.get(bot_id)

    @staticmethod
    def parse_signal(data: Dict[str, Any]) -> Dict[str, Any]:
        def to_decimal(value: str) -> Decimal:
            return Decimal(value).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        def price_to_decimal(value: str) -> Decimal:
            return Decimal(value).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
        def parse_time(value: str) -> datetime:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return {
            'exchange': data.get('exchange'),
            'symbol': data.get('symbol'),
            'order_id': data.get('order_id') or str(uuid.uuid4()),  # Ensure unique order_id
            'order_price': price_to_decimal(data.get('order_price')),
            'order_side': data.get('order_side'),
            'order_size': to_decimal(data.get('order_size')),
            'pos_size': to_decimal(data.get('pos_size')),
            'pos_type': data.get('pos_type'),
            'type': data.get('type'),
            'timeframe': data.get('timeframe'),
            'params': data.get('params'),
            'bot_id': data.get('bot_id'),
            'bot_name': data.get('bot_name'),
            'time': parse_time(data.get('time'))  # Parse time to datetime
        }

    @staticmethod
    def execute_order(data: Dict[str, Any], bot: TradingBot) -> Order:
        new_order = Order(
            order_id=str(uuid.uuid4()),
            position_id=None,  # This will be set when the position is updated
            symbol=data['symbol'],
            order_type=data['type'],
            side=data['order_side'],
            quantity=data['order_size'],
            entry_price=data['order_price'],
            status='filled',
            created_at=data['time'],
            executed_at=datetime.utcnow(),
            bot_id=bot.id,
            bot_name=bot.name,
            exchange=data['exchange'],
            timeframe=data['timeframe'],
            params=data['params']
        )
        return new_order

    @staticmethod
    def update_position(bot_id: int, data: Dict[str, Any], order: Order) -> Position:
        position = Position.query.filter_by(trading_bot_id=bot_id, symbol=data['symbol'], status='open').first()
        
        if not position:
            if abs(data['order_size']) == abs(data['pos_size']):
                position = Position(
                    trading_bot_id=bot_id,
                    symbol=data['symbol'],
                    pos_type=data['pos_type'],
                    status='open',
                    created_at=data['time'],
                    average_entry_price=data['order_price'],
                    position_size=data['order_size'],
                    initial_size=data['order_size']
                )
                db.session.add(position)
            else:
                raise ValueError("Order size mismatch, cannot open or update position")

        else:
            if position.pos_type == 'long':
                if data['order_side'] == 'buy':
                    total_cost = position.average_entry_price * position.position_size + data['order_price'] * data['order_size']
                    position.position_size += data['order_size']
                    position.initial_size += data['order_size']
                    position.average_entry_price = total_cost / position.position_size
                elif data['order_side'] == 'sell':
                    position.position_size -= data['order_size']
                    position.exit_price = data['order_price']
            elif position.pos_type == 'short':
                if data['order_side'] == 'sell':
                    total_cost = position.average_entry_price * position.position_size + data['order_price'] * data['order_size']
                    position.position_size += data['order_size']
                    position.initial_size += data['order_size']
                    position.average_entry_price = total_cost / position.position_size
                elif data['order_side'] == 'buy':
                    position.position_size -= data['order_size']
                    position.exit_price = data['order_price']

            if position.position_size <= 0:
                position.status = 'closed'
                position.closed_at = data['time']
                position.exit_price = data['order_price']
                position.position_size = Decimal('0.0')

        db.session.flush()  # Replacing commit with flush

        return position

    @staticmethod
    def calculate_pnl(position: Position, price: Decimal, side: str):
        if position.status == 'closed' or position.exit_price is not None:
            logger.info(f"Calculating PnL for position {position.id}:")
            logger.info(f"Position type: {position.pos_type}, Average entry price: {position.average_entry_price}, Exit price: {price}, Initial size: {position.initial_size}")

            # Fetch account details to get fee rates
            bot = TradingBot.query.get(position.trading_bot_id)
            account = bot.account

            # Convert fee percentages into decimal rates
            maker_fee_rate = Decimal(account.maker_fee) / Decimal('100')
            taker_fee_rate = Decimal(account.taker_fee) / Decimal('100')

            # Calculate fees
            entry_fee = maker_fee_rate * position.average_entry_price * abs(position.initial_size)
            exit_fee = taker_fee_rate * price * abs(position.initial_size)
            total_fees = entry_fee + exit_fee

            if position.pos_type == 'long':
                gross_pnl = (price - position.average_entry_price) * position.initial_size
            elif position.pos_type == 'short':
                gross_pnl = (position.average_entry_price - price) * position.initial_size

            logger.info(f"Gross PnL: {gross_pnl}, Total fees: {total_fees}")

            net_pnl = gross_pnl - total_fees

            position.profit_loss = net_pnl

            logger.info(f"Calculated profit/loss: {position.profit_loss}")

            position.percent_profit_loss = (net_pnl / (position.average_entry_price * abs(position.initial_size))) * Decimal('100')

            # Correct precision issues
            position.profit_loss = position.profit_loss.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            position.percent_profit_loss = position.percent_profit_loss.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            logger.info(f"Calculated percent profit/loss: {position.percent_profit_loss}")

            # Update account balance
            account.balance += position.profit_loss
            db.session.commit()

    @staticmethod
    def manage_risk(data: Dict[str, Any], position: Position):
        # Implement risk management logic such as updating stop-loss and take-profit orders
        pass

    @staticmethod
    def send_notifications(data: Dict[str, Any], order: Order):
        # Implement notification logic, e.g., sending an email or a message to a messaging platform
        pass

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
            if bot:
                db.session.delete(bot)
                db.session.commit()
                logger.info(f"Deleted bot {bot_id} and its related positions and orders.")
                return {"status": "success", "message": f"Bot {bot_id} and its related positions and orders were deleted successfully."}
            else:
                logger.warning(f"Bot {bot_id} not found.")
                return {"status": "error", "message": f"Bot {bot_id} not found."}
        except Exception as e:
            db.session.rollback()
            logger.error(f"An error occurred while deleting bot {bot_id}: {str(e)}")
            return {"status": "error", "message": f"An error occurred while deleting bot {bot_id}: {str(e)}"}

    @staticmethod
    def place_order(bot_id, symbol, order_type, side, quantity, entry_price=None):
        # Logic to place an order
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
