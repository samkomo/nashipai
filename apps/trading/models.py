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
    def cumulative_pnl(self):
        return sum(position.pnl for position in self.positions if position.status == 'closed')

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
            'cumulative_pnl': self.cumulative_pnl,  # Add cumulative PnL to the serialized output
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
    quantity = db.Column(db.Float, nullable=False)  # Current size of the position
    position_type = db.Column(db.String(20), nullable=False)  # e.g., long, short
    average_entry_price = db.Column(db.Float, nullable=False)  # Weighted average price of entered positions 
    current_price = db.Column(db.Float)  # Current market price of the asset
    status = db.Column(db.String(50), default='open')  # e.g., open, closed
    symbol = db.Column(db.String(50), nullable=False)  # e.g., SOLUSDT, ETHUSDT
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    # pnl = db.Column(db.Float, nullable=True, default=0)  # Profit and Loss
    @hybrid_property
    def pnl(self):
        if self.position_type == 'long' and self.status == 'closed':
            return (self.current_price - self.average_entry_price) * self.quantity
        elif self.position_type == 'short' and self.status == 'closed':
            return (self.average_entry_price - self.current_price) * self.quantity
        return 0


    # Relationships
    orders = db.relationship('Order', back_populates='position')
    trading_bot = db.relationship('TradingBot', back_populates='positions')

    def __repr__(self):
        return f'<Position {self.id} - Quantity: {self.quantity}, PnL: {self.pnl}>'
    

    def to_dict(self):
        recursion_limit = sys.getrecursionlimit()  # Get the current recursion limit
        print("Current recursion limit:", recursion_limit)
        """Serialize position to a dictionary, including the related orders."""
        position_data = {
            'id': self.id,
            'trading_bot_id': self.trading_bot_id,
            'quantity': self.quantity,
            'position_type': self.position_type,
            'average_entry_price': self.average_entry_price,
            'current_price': self.current_price,
            'status': self.status,
            'symbol': self.symbol,
            'opened_at': self.opened_at.strftime('%Y-%m-%d %H:%M:%S') if self.opened_at else None,
            'pnl': self.pnl,  # Include PnL in the serialization
            'closed_at': self.closed_at.strftime('%Y-%m-%d %H:%M:%S') if self.closed_at else None,
            'orders': [order.to_dict() for order in self.orders]
        }
        return position_data
    
    def update_position(self, order_price, order_quantity, order_side):
        if self.position_type == 'long':
            if order_side == 'buy':
                new_total_quantity = self.quantity + order_quantity
                if new_total_quantity > 0:
                    self.average_entry_price = ((self.average_entry_price * self.quantity) + (order_price * order_quantity)) / new_total_quantity
                self.quantity = new_total_quantity
            elif order_side == 'sell':
                self.quantity -= order_quantity
        elif self.position_type == 'short':
            if order_side == 'sell':
                new_total_quantity = self.quantity + order_quantity  # Note short positions have negative quantity
                if new_total_quantity < 0:
                    self.average_entry_price = ((self.average_entry_price * -self.quantity) + (order_price * order_quantity)) / -new_total_quantity
                self.quantity = new_total_quantity
            elif order_side == 'buy':
                self.quantity -= order_quantity  # Reducing a short position
    
    def delete(self, commit=True):
        """Delete the Position instance from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def find_by_id(cls, _id):
        """Find a position by its ID."""
        return cls.query.get(_id)

    def calculate_pnl(self):
        """Calculate the profit and loss for this position based on the current market price."""
        if self.status == 'open' and self.current_price is not None:
            self.pnl = (self.current_price - self.average_entry_price) * self.quantity
            return self.pnl
        # If the position is closed, the PnL should already be finalized
        return self.pnl

    def update_position(self, executed_order):
        """Update the position's size and average entry price based on an executed order."""
        # This method assumes 'executed_order' has attributes like 'order_price' and 'order_quantity'
        # You'll need to adjust this logic based on how orders affect your position size and entry price
        new_total_quantity = self.quantity + executed_order.order_quantity
        if new_total_quantity != 0:
            new_average_price = (
                (self.average_entry_price * self.quantity) +
                (executed_order.order_price * executed_order.order_quantity)
            ) / new_total_quantity
        else:
            new_average_price = 0  # Reset if position is closed/zeroed out

        self.average_entry_price = new_average_price
        self.quantity = new_total_quantity
        self.save()

    def close_position(self, closing_price):
        """Close the position and finalize the PnL calculation."""
        self.status = 'closed'
        self.current_price = closing_price
        self.closed_at = datetime.utcnow()
        self.calculate_pnl()
        self.save()

    def save(self, commit=True):
        """Save the position to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)  # e.g., market, limit
    side = db.Column(db.String(10), nullable=False)  # e.g., buy, sell
    quantity = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=True)  # Price at which order was executed
    status = db.Column(db.String(20), nullable=False, default='pending')  # e.g., pending, executed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    position = db.relationship('Position', back_populates='orders')
    # trading_bot = db.relationship('TradingBot', backref='orders')

    def __repr__(self):
        return f'<Order {self.id} - {self.symbol}, {self.side}, Status: {self.status}>'
    
    def to_dict(self):
        """Serialize order to a dictionary."""
        return {
            'id': self.id,
            'position_id': self.position_id,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'side': self.side,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'created_at': self.created_at,
            'status': self.status
        }
    
    def execute(self, execution_price):
        """Execute the order, updating its status and potentially modifying a related position."""
        self.status = 'executed'
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

