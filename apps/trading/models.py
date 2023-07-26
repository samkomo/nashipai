# Import required modules
from apps import db
from datetime import datetime

class Order(db.Model):
    # Define the Order class with appropriate fields
    id = db.Column(db.Integer, primary_key=True)
    exchange_id = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    order_id = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, nullable=False)
    side = db.Column(db.String(10), nullable=True)
    size = db.Column(db.Float, nullable=True)
    pos_size = db.Column(db.Float, default=0)
    type = db.Column(db.String(20), nullable=True)
    market_pos = db.Column(db.String(20), nullable=True)
    params = db.Column(db.JSON)
    # New fields
    time = db.Column(db.DateTime, nullable=True, server_default=db.func.now())
    strategy = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='Posted')

    def __repr__(self):
        return f"<Order {self.id} - {self.exchange_id}>"

    def to_dict(self):
        # Convert Order instance to a dictionary
        return {
            'id': self.id,
            'exchange_id': self.exchange_id,
            'symbol': self.symbol,
            'order_id': self.order_id,
            'price': self.price,
            'side': self.side,
            'size': self.size,
            'type': self.type,
            'pos_size': self.pos_size,
            'params': self.params,
            'market_pos': self.market_pos,
            'time': self.time.strftime('%Y-%m-%d %H:%M:%S') if self.time else None,
            'strategy': self.strategy,
            'status': self.status
            # Add more attributes if needed
        }

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