from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Numeric
from sqlalchemy.orm import relationship
from apps import db
from sqlalchemy.ext.hybrid import hybrid_property

# from datetime import datetime, timedelta
# from decimal import Decimal
# from sqlalchemy.ext.hybrid import hybrid_property
# from apps import db


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
    positions = db.relationship('Position', back_populates='trading_bot', cascade="all, delete-orphan")

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
    
    @hybrid_property
    def percent_profit_daily(self):
        return self._calculate_percent_profit_for_period(1)
    
    @hybrid_property
    def percent_profit_monthly(self):
        return self._calculate_percent_profit_for_period(30)
    
    def _calculate_percent_profit_for_period(self, days):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        positions = [p for p in self.positions if p.closed_at is not None and start_date <= p.closed_at <= end_date]
        return sum(p.percent_profit_loss for p in positions)

    def to_dict(self):
        """ Serialize the TradingBot object including strategy details. """
        days_running = (datetime.utcnow() - self.created_at).days if self.created_at else 0
        return {
            'id': self.id,
            'name': self.name,
            'strategy': self.strategy.to_dict_bot() if self.strategy else None,
            'account': self.account.to_dict_bot() if self.account else None,
            'positions': [position.to_dict() for position in self.positions] if self.positions else [],
            'user_id': self.user_id,
            'exchange_account_id': self.exchange_account_id,
            'status': self.status,
            'total_profit_loss': self.total_profit_loss,
            'total_percent_profit_loss': self.total_percent_profit_loss,
            'win_rate': self.calculate_win_rate(),
            'closed_trades': self.closed_trades_count,
            'has_open_position': self.has_open_position,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'days_running': days_running,
            'percent_profit_daily': self.percent_profit_daily,
            'percent_profit_monthly': self.percent_profit_monthly,
        }

class Position(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True)
    trading_bot_id = db.Column(db.Integer, db.ForeignKey('trading_bots.id'), nullable=False, index=True)
    symbol = db.Column(db.String(20), nullable=False)
    pos_type = db.Column(db.String(10), nullable=False)  # e.g., long, short
    status = db.Column(db.String(20), nullable=False, default='open')  # e.g., open, closed
    signal = db.Column(db.String(20), nullable=True)  # e.g., TP 1, SL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    average_entry_price = db.Column(Numeric(precision=20, scale=8), nullable=True)
    position_size = db.Column(Numeric(precision=20, scale=3), default=Decimal('0.0'))
    initial_size = db.Column(Numeric(precision=20, scale=3), default=Decimal('0.0'))
    profit_loss = db.Column(Numeric(precision=20, scale=8), default=Decimal('0.0'))
    percent_profit_loss = db.Column(Numeric(precision=20, scale=8), default=Decimal('0.0'))
    exit_price = db.Column(Numeric(precision=20, scale=8), nullable=True)

    # Relationships
    orders = db.relationship('Order', back_populates='position', cascade="all, delete-orphan")
    trading_bot = db.relationship('TradingBot', back_populates='positions')

    def to_dict(self):
        return {
            'id': self.id,
            'trading_bot_id': self.trading_bot_id,
            'symbol': self.symbol,
            'pos_type': self.pos_type,
            'status': self.status,
            'signal': self.signal,
            'created_at': self.created_at,
            'closed_at': self.closed_at,
            'average_entry_price': float(self.average_entry_price) if self.average_entry_price else None,
            'position_size': float(self.position_size),
            'initial_size': float(self.initial_size),
            'profit_loss': float(self.profit_loss),
            'percent_profit_loss': float(self.percent_profit_loss),
            'exit_price': float(self.exit_price) if self.exit_price else None,
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(64), nullable=False, unique=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)  # e.g., market, limit
    side = db.Column(db.String(10), nullable=False)  # e.g., buy, sell
    quantity = db.Column(Numeric(precision=20, scale=3), default=Decimal('0.0'))
    entry_price = db.Column(Numeric(precision=20, scale=8), nullable=True)  # Price at which order was filled
    status = db.Column(db.String(20), nullable=False, default='pending')  # e.g., pending, filled, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)
    bot_id = db.Column(db.String(64), nullable=True)
    bot_name = db.Column(db.String(255), nullable=True)
    exchange = db.Column(db.String(64), nullable=True)
    timeframe = db.Column(db.String(10), nullable=True)
    params = db.Column(db.String(255), nullable=True)

    # Relationships
    position = db.relationship('Position', back_populates='orders')

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'position_id': self.position_id,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'side': self.side,
            'quantity': str(self.quantity),
            'entry_price': str(self.entry_price) if self.entry_price else None,
            'status': self.status,
            'created_at': self.created_at,
            'executed_at': self.executed_at,
            'bot_id': self.bot_id,
            'bot_name': self.bot_name,
            'exchange': self.exchange,
            'timeframe': self.timeframe,
            'params': self.params,
        }
