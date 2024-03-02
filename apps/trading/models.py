# Import required modules
from apps import db
import pandas as pd

from datetime import datetime

class Order(db.Model):
    # Define the Order class with appropriate fields
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(50), nullable=False, unique=True)
    exchange_id = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)
    entry_price = db.Column(db.Float, nullable=False)
    side = db.Column(db.String(10), nullable=True)
    size = db.Column(db.Float, nullable=True)
    pos_size = db.Column(db.Float, default=0)
    type = db.Column(db.String(20), nullable=True)
    market_pos = db.Column(db.String(20), nullable=True)
    params = db.Column(db.JSON)
    # New fields
    entry_time = db.Column(db.DateTime, nullable=True, server_default=db.func.now())
    exit_time = db.Column(db.DateTime, nullable=True)
    # strategy = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20))
    exit_price = db.Column(db.Float, nullable=True)
    profit = db.Column(db.Float, nullable=True, default=0)
    percentage_profit = db.Column(db.Float, nullable=True, default=0)

    # Add a foreign key column to reference the Strategy
    strategy_uid = db.Column(db.String(64), db.ForeignKey('strategies.uid'), nullable=True)
    
    # Define a relationship in the Order model for backref (optional)
    strategy = db.relationship('Strategy', back_populates='orders')

    def __repr__(self):
        return f"<Order {self.id} - {self.exchange_id}>"

    def to_dict(self):
        """Convert object properties to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @staticmethod
    def delete_all_orders():
        # Static method to delete all orders from the database
        db.session.query(Order).delete()
        db.session.commit()


# from apps import db
# from apps.trading.models import Order
# db.drop_all()
# db.create_all()
# exit()
        

class Strategy(db.Model):
    __tablename__ = 'strategies'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64), unique=True, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=True, server_default=db.func.now())
    updated_date = db.Column(db.DateTime, nullable=True)
    # New fields
    coin_pair = db.Column(db.String(20))  # Adjust the size as needed
    time_frame = db.Column(db.String(10))
    strategy_name = db.Column(db.String(255))  # Ensure the length accommodates your strategy name length
    # Existing fields...
    net_profit_percent_all = db.Column(db.Float)
    net_profit_percent_long = db.Column(db.Float)
    net_profit_percent_short = db.Column(db.Float)
    net_profit_all = db.Column(db.Float)
    net_profit_long = db.Column(db.Float)
    net_profit_short = db.Column(db.Float)
    gross_profit_percent_all = db.Column(db.Float)
    gross_profit_percent_long = db.Column(db.Float)
    gross_profit_percent_short = db.Column(db.Float)
    gross_profit_all = db.Column(db.Float)
    gross_profit_long = db.Column(db.Float)
    gross_profit_short = db.Column(db.Float)
    gross_loss_percent_all = db.Column(db.Float)
    gross_loss_percent_long = db.Column(db.Float)
    gross_loss_percent_short = db.Column(db.Float)
    gross_loss_all = db.Column(db.Float)
    gross_loss_long = db.Column(db.Float)
    gross_loss_short = db.Column(db.Float)
    max_runup = db.Column(db.Float)
    max_runup_percent = db.Column(db.Float)
    max_drawdown = db.Column(db.Float)
    max_drawdown_percent = db.Column(db.Float)
    buy_and_hold_return = db.Column(db.Float)
    buy_and_hold_return_percent = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    sortino_ratio = db.Column(db.Float, default=0.0)  # You might need to handle NaN values separately
    profit_factor_all = db.Column(db.Float)
    profit_factor_long = db.Column(db.Float)
    profit_factor_short = db.Column(db.Float)
    max_contracts_held_all = db.Column(db.Integer)
    max_contracts_held_long = db.Column(db.Integer)
    max_contracts_held_short = db.Column(db.Integer)
    open_pl = db.Column(db.Float)
    open_pl_percent = db.Column(db.Float)
    commission_paid_all = db.Column(db.Float)
    commission_paid_long = db.Column(db.Float)
    commission_paid_short = db.Column(db.Float)
    total_closed_trades_all = db.Column(db.Integer)
    total_closed_trades_long = db.Column(db.Integer)
    total_closed_trades_short = db.Column(db.Integer)
    total_open_trades_all = db.Column(db.Integer)
    total_open_trades_long = db.Column(db.Integer)
    total_open_trades_short = db.Column(db.Integer)
    number_winning_trades_all = db.Column(db.Integer)
    number_winning_trades_long = db.Column(db.Integer)
    number_winning_trades_short = db.Column(db.Integer)
    number_losing_trades_all = db.Column(db.Integer)
    number_losing_trades_long = db.Column(db.Integer)
    number_losing_trades_short = db.Column(db.Integer)
    percent_profitable_all = db.Column(db.Float)
    percent_profitable_long = db.Column(db.Float)
    percent_profitable_short = db.Column(db.Float)
    
    
    avg_num_bars_in_losing_trades_all = db.Column(db.Float)
    avg_num_bars_in_losing_trades_long = db.Column(db.Float)
    avg_num_bars_in_losing_trades_short = db.Column(db.Float)
    avg_num_bars_in_trades_all = db.Column(db.Float)
    avg_num_bars_in_trades_long = db.Column(db.Float)
    avg_num_bars_in_trades_short = db.Column(db.Float)
    avg_num_bars_in_winning_trades_all = db.Column(db.Float)
    avg_num_bars_in_winning_trades_long = db.Column(db.Float)
    avg_num_bars_in_winning_trades_short = db.Column(db.Float)
    avg_losing_trade_percent_all = db.Column(db.Float)
    avg_losing_trade_percent_long = db.Column(db.Float)
    avg_losing_trade_percent_short = db.Column(db.Float)
    avg_losing_trade_all = db.Column(db.Float)
    avg_losing_trade_long = db.Column(db.Float)
    avg_losing_trade_short = db.Column(db.Float)
    avg_trade_percent_all = db.Column(db.Float)
    avg_trade_percent_long = db.Column(db.Float)
    avg_trade_percent_short = db.Column(db.Float)
    avg_trade_all = db.Column(db.Float)
    avg_trade_long = db.Column(db.Float)
    avg_trade_short = db.Column(db.Float)
    avg_winning_trade_percent_all = db.Column(db.Float)
    avg_winning_trade_percent_long = db.Column(db.Float)
    avg_winning_trade_percent_short = db.Column(db.Float)
    avg_winning_trade_all = db.Column(db.Float)
    avg_winning_trade_long = db.Column(db.Float)
    avg_winning_trade_short = db.Column(db.Float)
    
    largest_losing_trade_percent_all = db.Column(db.Float)
    largest_losing_trade_percent_long = db.Column(db.Float)
    largest_losing_trade_percent_short = db.Column(db.Float)
    largest_losing_trade_all = db.Column(db.Float)
    largest_losing_trade_long = db.Column(db.Float)
    largest_losing_trade_short = db.Column(db.Float)
    largest_winning_trade_percent_all = db.Column(db.Float)
    largest_winning_trade_percent_long = db.Column(db.Float)
    largest_winning_trade_percent_short = db.Column(db.Float)
    largest_winning_trade_all = db.Column(db.Float)
    largest_winning_trade_long = db.Column(db.Float)
    largest_winning_trade_short = db.Column(db.Float)
    margin_calls_all = db.Column(db.Integer)
    margin_calls_long = db.Column(db.Integer)
    margin_calls_short = db.Column(db.Integer)
    ratio_avg_win_avg_loss_all = db.Column(db.Float)
    ratio_avg_win_avg_loss_long = db.Column(db.Float)
    ratio_avg_win_avg_loss_short = db.Column(db.Float)
    comment = db.Column(db.Text)  # Assuming 'comment' is a text field
    settings=db.Column(db.JSON)

    # Define the relationship to orders
    orders = db.relationship('Order', order_by=Order.id, back_populates='strategy')

    def __init__(self, **kwargs):
        super(Strategy, self).__init__(**kwargs)
        # You can add initialization logic here if necessary

    @classmethod
    def create_from_dict(cls, data_dict):
        # Filter out keys that are not column names
        valid_keys = {k: v for k, v in data_dict.items() if k in cls.__table__.columns}
        # Handle NaN values and convert them to None
        for key, value in valid_keys.items():
            if pd.isna(value):
                valid_keys[key] = None
        return cls(**valid_keys)

    def to_dict(self):
        """Convert object properties to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def save(self):
        db.session.add(self)
        db.session.commit()
