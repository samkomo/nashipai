# Import required modules
from decimal import Decimal
import sys
import humanize
from apps import db
import pandas as pd
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Numeric

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
        return sum(position.profit_loss for position in self.positions if position.closed_at != None)
    
    @property
    def total_percent_profit_loss(self):
        return sum(position.percent_profit_loss for position in self.positions if position.closed_at != None)
    
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
    signal = db.Column(db.String(20), nullable=True)  # e.g., TP 1, ..., TP X
    # position_size = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    average_entry_price = db.Column(Numeric(precision=10, scale=2), nullable=True)
    position_size = db.Column(Numeric(precision=10, scale=3), default=Decimal('0.0'))
    profit_loss = db.Column(Numeric(precision=12, scale=2), default=Decimal('0.0'))
    percent_profit_loss = db.Column(Numeric(precision=12, scale=2), default=Decimal('0.0'))
    exit_price = db.Column(Numeric(precision=10, scale=2), nullable=True)


    # Relationships
    orders = db.relationship('Order', back_populates='position')
    trading_bot = db.relationship('TradingBot', back_populates='positions')

    def update_position(self, order):
        """Update position details based on a new or modified order."""
        quantity = Decimal(str(order.quantity))  # Ensure order.quantity is Decimal
        entry_price = Decimal(str(order.entry_price))  # Convert entry price to Decimal

        if order.side == 'buy':
            if self.pos_type == 'long':
                # Calculate the total cost of the existing position and the new order
                total_cost_existing = self.average_entry_price * self.position_size
                total_cost_new = entry_price * quantity

                # Adjust the average entry price and increase size
                self.position_size += quantity
                self.signal=order.params
                # Calculate new average entry price
                if self.position_size != 0:  # Ensure no division by zero
                    self.average_entry_price = (total_cost_existing + total_cost_new) / self.position_size
                else:
                    self.average_entry_price = Decimal('0.0')  # Default to zero if no position size
                

            elif self.pos_type == 'short':
                # Reduce the position size
                self.position_size -= quantity
                self.closed_at=datetime.utcnow()
                self.signal=order.params
                self.exit_price=order.entry_price
            
            elif order.pos_type == 'flat':
                self.position_size -= quantity
                self.closed_at = datetime.utcnow()
                self.exit_price = order.entry_price
                self.signal=order.params
                # Update the position status
                if self.position_size == 0:
                    self.status = 'closed'

        elif order.side == 'sell':
            if self.pos_type == 'long':
                self.position_size -= quantity
                self.closed_at=datetime.utcnow()
                self.signal=order.params
                self.exit_price=order.entry_price

            elif self.pos_type == 'short':
                # Calculate the total cost of the existing position and the new order
                total_cost_existing = self.average_entry_price * self.position_size
                total_cost_new = entry_price * quantity

                self.position_size += quantity

                # Calculate new average entry price
                if self.position_size != 0:  # Ensure no division by zero
                    self.average_entry_price = (total_cost_existing + total_cost_new) / self.position_size
                else:
                    self.average_entry_price = Decimal('0.0')  # Default to zero if no position size
            elif order.pos_type == 'flat':
                self.position_size -= quantity
                self.closed_at=datetime.utcnow()
                self.signal=order.params
                self.exit_price=order.entry_price
                # Update the position status
                if self.position_size == 0:
                    self.status = 'closed'

        # Update the position status
        if self.position_size == 0:
            self.status = 'closed'


        db.session.commit()

    def calculate_profit_loss(self, order, fee_percent_float=0.075):
        quantity = Decimal(str(order.quantity))  # Ensure order.quantity is Decimal
        fee_percent = Decimal(str(fee_percent_float))

        if order.status != 'filled':
            return  # Only calculate profit/loss for filled orders

        # Initialize profit_or_loss to zero
        profit_or_loss = 0
        percent_profit_loss = 0  # Initialize percent profit or loss

        entry_price = Decimal(str(order.entry_price))  # Convert entry price to Decimal
        quantity = Decimal(str(order.quantity))  # Convert quantity to Decimal


        # Ensure average_entry_price is not None to avoid subtraction with NoneType
        if self.average_entry_price is None:
            # Default to the order's entry price if no average price is available, or skip calculation
            self.average_entry_price = entry_price if entry_price is not None else 0

        if self.pos_type == 'long' and order.side == 'sell':
            # Calculate profit or loss for long position when selling
            profit_or_loss = (entry_price - self.average_entry_price) * quantity
            if self.average_entry_price > 0:  # Avoid division by zero
                percent_profit_loss = ((entry_price - self.average_entry_price) / self.average_entry_price) * 100

        elif self.pos_type == 'short' and order.side == 'buy':
            # Calculate profit or loss for short position when buying to cover
            profit_or_loss = (self.average_entry_price - entry_price) * quantity
            if self.average_entry_price > 0:  # Avoid division by zero
                percent_profit_loss = ((self.average_entry_price - entry_price) / self.average_entry_price) * 100

        # Calculate fees based on the order's execution price and quantity
        fees = (entry_price * quantity) * (fee_percent / 100)

        # Deduct fees from the profit or loss
        profit_or_loss -= fees

        # Add the calculated profit or loss to the accumulated total
        # Store the results
        self.profit_loss += profit_or_loss
        self.percent_profit_loss += percent_profit_loss if self.average_entry_price > 0 else 0

        # # Check if the position should be closed
        # if self.position_size == 0 or order.pos_type == 'flat':
        #     self.status = 'closed'
        #     self.closed_at = datetime.utcnow()
        #     self.exit_price = entry_price
        #     self.signal=order.params

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

  

    def to_dict(self):
        """Serialize position to a dictionary, including computed properties."""
        return {
            'id': self.id,
            'trading_bot_id': self.trading_bot_id if hasattr(self, 'trading_bot_id') else None,
            'symbol': self.symbol,
            'pos_type': self.pos_type,
            'status': self.status,
            'signal':self.signal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'exit_pos_size': self.position_size,
            'entry_pos_size': self.total_position_size,
            'average_entry_price': self.average_entry_price,
            'exit_price': self.exit_price,
            'profit_loss': float(self.profit_loss),
            'percent_profit_loss': float(self.percent_profit_loss)  # Include the percentage profit or loss
        }


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
    quantity = db.Column(Numeric(precision=10, scale=3), default=0.0)
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

