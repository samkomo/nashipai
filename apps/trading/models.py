# Import required modules
import sys
import humanize
from apps import db
import pandas as pd
from sqlalchemy.ext.hybrid import hybrid_property

from datetime import datetime

class TradingBot(db.Model):
    __tablename__ = 'trading_bots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    exchange_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    status = db.Column(db.String(50), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    strategy = db.relationship('Strategy', back_populates='trading_bots')
    user = db.relationship('User', backref='trading_bots')
    account = db.relationship('Account', backref='trading_bots')
    positions = db.relationship('Position', back_populates='trading_bot')

    @property
    def total_profit_loss(self):
        return sum(position.profit_loss for position in self.positions if position.status == 'closed')
    
    @property
    def total_percent_profit_loss(self):
        return sum(position.percent_profit_loss for position in self.positions if position.status == 'closed')
    
    @property
    def closed_trades_count(self):
        # Count positions with status 'closed'
        return sum(1 for position in self.positions if position.status == 'closed')
    
    @property
    def has_open_position(self):
        # Return True if any position is open
        return any(position.status == 'open' for position in self.positions)


    def calculate_win_rate(self):
        closed_positions = [p for p in self.positions if p.status == 'closed']
        if not closed_positions:
            return 0  # Avoid division by zero if no positions are closed

        wins = sum(1 for p in closed_positions if p.profit_loss > 0)
        total_closed = len(closed_positions)
        win_rate = (wins / total_closed) * 100  # Win rate as a percentage

        return win_rate
    
    def to_dict(self):
        """ Serialize the TradingBot object including strategy details. """
        days_running = (datetime.utcnow() - self.created_at).days if self.created_at else 0
        # natural_day = humanize.naturalday(self.created_at) if self.created_at else 'Unknown'

        return {
            'id': self.id,
            'name': self.name,
            'strategy': self.strategy.to_dict_bot() if self.strategy else None,
            'account': self.account.to_dict_bot() if self.account else None,
            'positions': [position.to_dict() for position in self.positions] if self.positions else [],
            'user_id': self.user_id,
            'exchange_account_id': self.exchange_account_id,
            'status': self.status,
            'total_profit_loss': self.total_profit_loss,  # Add cumulative PnL to the serialized output
            'total_percent_profit_loss': self.total_percent_profit_loss,  # Add cumulative PnL to the serialized output
            'win_rate': self.calculate_win_rate(),  # Include win rate in the dictionary
            'closed_trades': self.closed_trades_count,
            'has_open_position': self.has_open_position,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'days_running': days_running
        }


    def __repr__(self):
        return f'<TradingBot "{self.name}", Status: {self.status}>'

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_active_bots(cls):
        return cls.query.filter_by(status='active').all()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def activate(self):
        self.status = 'active'
        self.save()

    def deactivate(self):
        self.status = 'inactive'
        self.save()

class Position(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True)
    trading_bot_id = db.Column(db.Integer, db.ForeignKey('trading_bots.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    pos_type = db.Column(db.String(10), nullable=False)  # e.g., long, short, flat
    status = db.Column(db.String(20), nullable=False, default='open')  # e.g., open, closed
    average_entry_price = db.Column(db.Float, nullable=True)
    position_size = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    profit_loss = db.Column(db.Float, default=0.0)
    percent_profit_loss = db.Column(db.Float, default=0.0)  # New column for percent profit or loss
    exit_price=db.Column(db.Float, nullable=True)

    # Relationships
    orders = db.relationship('Order', back_populates='position')
    trading_bot = db.relationship('TradingBot', back_populates='positions')

    def update_position(self, order):
        """Update position details based on a new or modified order."""
        if order.side == 'buy':
            if self.pos_type == 'long':
                # Adjust the average entry price and increase size
                self.position_size += order.quantity
                self.average_entry_price = ((self.average_entry_price or 0) * (self.position_size - order.quantity) + order.entry_price * order.quantity) / self.position_size
            elif self.pos_type == 'short':
                # Reduce the position size
                self.position_size += order.quantity
        elif order.side == 'sell':
            if self.pos_type == 'long':
                self.position_size -= order.quantity
            elif self.pos_type == 'short':
                self.position_size -= order.quantity
                self.average_entry_price = ((self.average_entry_price or 0) * (self.position_size - order.quantity) - order.entry_price * order.quantity) / self.position_size

        # Update the position status
        if self.position_size == 0:
            self.status = 'closed'
            self.closed_at = datetime.utcnow()
            self.exit_price = order.entry_price

        db.session.commit()

    def calculate_profit_loss(self, order, fee_percent=0.05):
        if order.status != 'filled':
            return  # Only calculate profit/loss for filled orders

        # Initialize profit_or_loss to zero
        profit_or_loss = 0
        percent_profit_loss = 0  # Initialize percent profit or loss

        # Ensure average_entry_price is not None to avoid subtraction with NoneType
        if self.average_entry_price is None:
            # Default to the order's entry price if no average price is available, or skip calculation
            self.average_entry_price = order.entry_price if order.entry_price is not None else 0

        if self.pos_type == 'long' and order.side == 'sell':
            # Calculate profit or loss for long position when selling
            profit_or_loss = (order.entry_price - self.average_entry_price) * order.quantity
            if self.average_entry_price > 0:  # Avoid division by zero
                percent_profit_loss = ((order.entry_price - self.average_entry_price) / self.average_entry_price) * 100

        elif self.pos_type == 'short' and order.side == 'buy':
            # Calculate profit or loss for short position when buying to cover
            profit_or_loss = (self.average_entry_price - order.entry_price) * order.quantity
            if self.average_entry_price > 0:  # Avoid division by zero
                percent_profit_loss = ((self.average_entry_price - order.entry_price) / self.average_entry_price) * 100

        # Calculate fees based on the order's execution price and quantity
        fees = (order.entry_price * order.quantity) * (fee_percent / 100)

        # Deduct fees from the profit or loss
        profit_or_loss -= fees

        # Add the calculated profit or loss to the accumulated total
        # Store the results
        self.profit_loss += profit_or_loss
        self.percent_profit_loss += percent_profit_loss if self.average_entry_price > 0 else 0

        # Check if the position should be closed
        if self.position_size == 0:
            self.status = 'closed'
            self.closed_at = datetime.utcnow()
            self.exit_price = order.entry_price

        db.session.commit()

        # Optionally return both the absolute and percentage profit or loss
        return {
            'absolute_profit_loss': profit_or_loss,
            'percent_profit_loss': percent_profit_loss
        }


    @property
    def is_open(self):
        return self.status == 'open'

    @hybrid_property
    def total_position_size(self):
        """Calculate net position size accounting for buys and sells."""
        size = sum(order.quantity for order in self.orders if order.side == 'buy' and order.pos_type == 'long')  or sum(order.quantity for order in self.orders if order.side == 'sell' and order.pos_type == 'short')
        # if self.pos_type == 'short':
        #     size = -size
        return size

    # @hybrid_property
    # def average_entry_price(self):
    #     """Calculate the weighted average entry price for open positions."""
    #     total_quantity = 0
    #     total_value = 0
    #     for order in self.orders:
    #         if order.status == 'filled':
    #             total_quantity += order.quantity
    #             total_value += order.quantity * order.entry_price
    #     return total_value / total_quantity if total_quantity > 0 else None
    
    # @hybrid_property
    # def profit_loss(self):
    #     """Calculate profit or loss for closed portions of the position, including final closure."""
    #     profit_loss = 0
    #     entry_positions = []  # To store (quantity, price) tuples for each position increment

    #     for order in self.orders:
    #         if order.status == 'filled':
    #             if self.pos_type == 'long':
    #                 if order.side == 'buy':
    #                     entry_positions.append((order.quantity, order.entry_price))
    #                 elif order.side == 'sell':
    #                     remaining_quantity = order.quantity
    #                     while remaining_quantity > 0 and entry_positions:
    #                         quantity, price = entry_positions.pop(0)
    #                         if quantity <= remaining_quantity:
    #                             profit_loss += (order.entry_price - price) * quantity
    #                             remaining_quantity -= quantity
    #                         else:
    #                             profit_loss += (order.entry_price - price) * remaining_quantity
    #                             entry_positions.insert(0, (quantity - remaining_quantity, price))
    #                             break

    #             elif self.pos_type == 'short':
    #                 if order.side == 'sell':
    #                     entry_positions.append((order.quantity, order.entry_price))
    #                 elif order.side == 'buy':
    #                     remaining_quantity = order.quantity
    #                     while remaining_quantity > 0 and entry_positions:
    #                         quantity, price = entry_positions.pop(0)
    #                         if quantity <= remaining_quantity:
    #                             profit_loss += (price - order.entry_price) * quantity
    #                             remaining_quantity -= quantity
    #                         else:
    #                             profit_loss += (price - order.entry_price) * remaining_quantity
    #                             entry_positions.insert(0, (quantity - remaining_quantity, price))
    #                             break

    #             if order.pos_type == 'flat':  # Handle closing of the position through a flat type order
    #                 for quantity, price in entry_positions:
    #                     if self.pos_type == 'long':
    #                         profit_loss += (order.entry_price - price) * quantity
    #                     elif self.pos_type == 'short':
    #                         profit_loss += (price - order.entry_price) * quantity
    #                 entry_positions.clear()  # Clear remaining positions as they are now considered closed

    #     return profit_loss

    # @hybrid_property
    # def status(self):
    #     if not self.orders:
    #         return 'pending'  # No orders linked yet
    #     # Check if any order has a 'flat' pos_type and the position size is zero
    #     if any(order.pos_type == 'flat' and order.pos_size == 0 for order in self.orders):
    #         return 'closed'
    #     return 'open'



    def to_dict(self):
        """Serialize position to a dictionary, including computed properties."""
        return {
            'id': self.id,
            'trading_bot_id': self.trading_bot_id if hasattr(self, 'trading_bot_id') else None,
            'symbol': self.symbol,
            'pos_type': self.pos_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'position_size': self.total_position_size,
            'average_entry_price': self.average_entry_price,
            'exit_price': self.exit_price,
            'profit_loss': self.profit_loss,
            'percent_profit_loss': self.percent_profit_loss  # Include the percentage profit or loss
        }


# Note: Ensure to define other relationships and fields as necessary
    

# class Position(db.Model):
#     __tablename__ = 'positions'
#     id = db.Column(db.Integer, primary_key=True)
#     trading_bot_id = db.Column(db.Integer, db.ForeignKey('trading_bots.id'), nullable=False)
#     quantity = db.Column(db.Float, nullable=False)  # Current size of the position
#     position_type = db.Column(db.String(20), nullable=False)  # e.g., long, short
#     position_signal = db.Column(db.String(20), nullable=False)  # e.g., TP 1, SL 1, 
#     average_entry_price = db.Column(db.Float, nullable=False)  # Weighted average price of entered positions 
#     current_price = db.Column(db.Float)  # Current market price of the asset
#     status = db.Column(db.String(50), default='open')  # e.g., open, closed
#     symbol = db.Column(db.String(50), nullable=False)  # e.g., SOLUSDT, ETHUSDT
#     opened_at = db.Column(db.DateTime, default=datetime.utcnow)
#     closed_at = db.Column(db.DateTime)
#     # pnl = db.Column(db.Float, nullable=True, default=0)  # Profit and Loss
#     @hybrid_property
#     def pnl(self):
#         if self.position_type == 'long' and self.status == 'closed':
#             return (self.current_price - self.average_entry_price) * self.quantity
#         elif self.position_type == 'short' and self.status == 'closed':
#             return (self.average_entry_price - self.current_price) * self.quantity
#         return 0


#     # Relationships
#     orders = db.relationship('Order', back_populates='position')
#     trading_bot = db.relationship('TradingBot', back_populates='positions')

#     def __repr__(self):
#         return f'<Position {self.id} - Quantity: {self.quantity}, PnL: {self.pnl}>'
    

#     def to_dict(self):
#         recursion_limit = sys.getrecursionlimit()  # Get the current recursion limit
#         print("Current recursion limit:", recursion_limit)
#         """Serialize position to a dictionary, including the related orders."""
#         position_data = {
#             'id': self.id,
#             'trading_bot_id': self.trading_bot_id,
#             'quantity': self.quantity,
#             'position_signal': self.position_signal,
#             'position_type': self.position_type,
#             'average_entry_price': self.average_entry_price,
#             'current_price': self.current_price,
#             'status': self.status,
#             'symbol': self.symbol,
#             'opened_at': self.opened_at.strftime('%Y-%m-%d %H:%M:%S') if self.opened_at else None,
#             'pnl': self.pnl,  # Include PnL in the serialization
#             'closed_at': self.closed_at.strftime('%Y-%m-%d %H:%M:%S') if self.closed_at else None,
#             'orders': [order.to_dict() for order in self.orders]
#         }
#         return position_data
    
#     def update_position(self, order_price, order_quantity, order_side):
#         if self.position_type == 'long':
#             if order_side == 'buy':
#                 new_total_quantity = self.quantity + order_quantity
#                 if new_total_quantity > 0:
#                     self.average_entry_price = ((self.average_entry_price * self.quantity) + (order_price * order_quantity)) / new_total_quantity
#                 self.quantity = new_total_quantity
#             elif order_side == 'sell':
#                 self.quantity -= order_quantity
#         elif self.position_type == 'short':
#             if order_side == 'sell':
#                 new_total_quantity = self.quantity + order_quantity  # Note short positions have negative quantity
#                 if new_total_quantity < 0:
#                     self.average_entry_price = ((self.average_entry_price * -self.quantity) + (order_price * order_quantity)) / -new_total_quantity
#                 self.quantity = new_total_quantity
#             elif order_side == 'buy':
#                 self.quantity -= order_quantity  # Reducing a short position
    
#     def delete(self, commit=True):
#         """Delete the Position instance from the database."""
#         db.session.delete(self)
#         if commit:
#             db.session.commit()

#     @classmethod
#     def find_by_id(cls, _id):
#         """Find a position by its ID."""
#         return cls.query.get(_id)

#     def calculate_pnl(self):
#         """Calculate the profit and loss for this position based on the current market price."""
#         if self.status == 'open' and self.current_price is not None:
#             self.pnl = (self.current_price - self.average_entry_price) * self.quantity
#             return self.pnl
#         # If the position is closed, the PnL should already be finalized
#         return self.pnl

#     def update_position(self, executed_order):
#         """Update the position's size and average entry price based on an executed order."""
#         # This method assumes 'executed_order' has attributes like 'order_price' and 'order_quantity'
#         # You'll need to adjust this logic based on how orders affect your position size and entry price
#         new_total_quantity = self.quantity + executed_order.order_quantity
#         if new_total_quantity != 0:
#             new_average_price = (
#                 (self.average_entry_price * self.quantity) +
#                 (executed_order.order_price * executed_order.order_quantity)
#             ) / new_total_quantity
#         else:
#             new_average_price = 0  # Reset if position is closed/zeroed out

#         self.average_entry_price = new_average_price
#         self.quantity = new_total_quantity
#         self.save()

#     def close_position(self, closing_price):
#         """Close the position and finalize the PnL calculation."""
#         self.status = 'closed'
#         self.current_price = closing_price
#         self.closed_at = datetime.utcnow()
#         self.calculate_pnl()
#         self.save()

    def save(self, commit=True):
        """Save the position to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)  # e.g., market, limit
    side = db.Column(db.String(10), nullable=False)  # e.g., buy, sell
    quantity = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=True)  # Price at which order was filled
    status = db.Column(db.String(20), nullable=False, default='pending')  # e.g., pending, filled, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)
    bot_id = db.Column(db.String(20), nullable=True)
    bot_name = db.Column(db.String(50), nullable=True)
    exchange = db.Column(db.String(20), nullable=True)
    pos_size = db.Column(db.Float, nullable=True)
    pos_type = db.Column(db.String(10), nullable=True)  # e.g., short, long, flat
    timeframe = db.Column(db.String(10), nullable=True)
    params = db.Column(db.String(255), nullable=True)

    # Relationships
    position = db.relationship('Position', back_populates='orders')

    def __repr__(self):
        return f'<Order {self.id} - {self.symbol}, {self.side}, Status: {self.status}>'
    
    def to_dict(self):
        """Serialize order to a dictionary."""
        return {
            'id': self.id,
            'position_id': self.position_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'side': self.side,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'bot_id': self.bot_id,
            'bot_name': self.bot_name,
            'exchange': self.exchange,
            'pos_size': self.pos_size,
            'pos_type': self.pos_type,
            'timeframe': self.timeframe,
            'params': self.params
        }

    
    def execute(self, execution_price):
        """Execute the order, updating its status and potentially modifying a related position."""
        self.status = 'filled'
        self.entry_price = execution_price
        self.executed_at = datetime.utcnow()
        
        # Update related position if exists, else create a new position
        if self.position:
            self.position.update_position(self)
        else:
            # Logic to create a new position
            # This assumes existence of a method in Position to handle new orders without an existing position
            new_position = Position(
                quantity=self.quantity,
                average_entry_price=execution_price,
                current_price=execution_price,  # Assuming current price is the execution price at order creation
                status='open'
            )
            new_position.save()

        self.save()

    def cancel(self):
        """Cancel the order if it has not been executed."""
        if self.status == 'pending':
            self.status = 'cancelled'
            self.save()

    def save(self, commit=True):
        """Save the order to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        """Delete the order from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def find_by_id(cls, order_id):
        """Find an order by its ID."""
        return cls.query.get(order_id)


class TradeAlert(db.Model):
    __tablename__ = 'trade_alerts'
    id = db.Column(db.Integer, primary_key=True)
    trading_bot_id = db.Column(db.Integer, db.ForeignKey('trading_bots.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)  # Description or message of the alert
    alert_type = db.Column(db.String(50), nullable=False)  # Type of alert, e.g., "price_threshold", "order_executed"
    severity = db.Column(db.String(10), nullable=False, default='info')  # e.g., "info", "warning", "critical"
    status = db.Column(db.String(20), nullable=False, default='new')  # e.g., "new", "viewed", "dismissed"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    viewed_at = db.Column(db.DateTime, nullable=True)  # Timestamp when the alert was viewed

    # Relationships
    trading_bot = db.relationship('TradingBot', backref='alerts')

    def __repr__(self):
        return f'<Alert {self.id} - {self.alert_type}: {self.message}>'

    def mark_viewed(self):
        """Mark the alert as viewed and set the viewed_at timestamp."""
        self.status = 'viewed'
        self.viewed_at = datetime.utcnow()
        self.save()

    def save(self, commit=True):
        """Save the alert to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        """Delete the alert from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def find_by_id(cls, alert_id):
        """Find an alert by its ID."""
        return cls.query.get(alert_id)

    @classmethod
    def create_alert(cls, trading_bot_id, message, alert_type, severity='info', commit=True):
        """Class method to create and save a new alert."""
        new_alert = cls(
            trading_bot_id=trading_bot_id,
            message=message,
            alert_type=alert_type,
            severity=severity
        )
        db.session.add(new_alert)
        if commit:
            db.session.commit()
        return new_alert

