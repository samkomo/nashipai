# Import required modules
from apps import db
import pandas as pd

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TradingBot(db.Model):
    __tablename__ = 'trading_bots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    exchange_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    status = db.Column(db.String(50), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    strategy = db.relationship('Strategy', backref='trading_bots')
    user = db.relationship('User', backref='trading_bots')
    account = db.relationship('Account', backref='trading_bots')
    positions = db.relationship('Position', backref='trading_bot', lazy='dynamic')
    orders = db.relationship('Order', backref='trading_bot', lazy='select', cascade='all, delete')

    def __repr__(self):
        return f'<TradingBot "{self.name}", Status: {self.status}>'

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

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
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Current size of the position
    average_entry_price = db.Column(db.Float, nullable=False)  # Weighted average price of entered positions
    current_price = db.Column(db.Float)  # Current market price of the asset
    status = db.Column(db.String(50), default='open')  # e.g., open, closed
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    pnl = db.Column(db.Float, nullable=True, default=0)  # Profit and Loss

    # Relationships
    order = db.relationship('Order', back_populates='positions')
    trading_bot = db.relationship('TradingBot', back_populates='positions')

    def __repr__(self):
        return f'<Position {self.id} - Quantity: {self.quantity}, PnL: {self.pnl}>'

    def to_dict(self):
        """Serialize position to a dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

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
    trading_bot_id = db.Column(db.Integer, db.ForeignKey('trading_bots.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=True)
    symbol = db.Column(db.String(20), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)  # e.g., market, limit
    side = db.Column(db.String(10), nullable=False)  # e.g., buy, sell
    quantity = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=True)  # Price at which order was executed
    status = db.Column(db.String(20), nullable=False, default='pending')  # e.g., pending, executed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    position = db.relationship('Position', back_populates='order')
    trading_bot = db.relationship('TradingBot', backref='orders')

    def __repr__(self):
        return f'<Order {self.id} - {self.symbol}, {self.side}, Status: {self.status}>'

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
                trading_bot_id=self.trading_bot_id,
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
