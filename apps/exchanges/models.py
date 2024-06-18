import datetime
from apps import db
from decimal import Decimal
from sqlalchemy import Numeric

class Exchange(db.Model):
    __tablename__ = 'exchanges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Exchange name, e.g., 'binance', 'coinbasepro'
    url = db.Column(db.String(255), nullable=True)  # The main URL of the exchange
    sandbox_url = db.Column(db.String(255), nullable=True)  # Sandbox environment URL, if available
    documentation_url = db.Column(db.String(255), nullable=True)  # URL to exchange's API documentation

    # Relationships
    accounts = db.relationship('Account', back_populates='exchange', lazy='dynamic')

    def to_dict(self):
        """Serialize review details to a dictionary for API responses or other uses."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def __repr__(self):
        return f'<Exchange {self.name}>'

    @classmethod
    def create_exchange(cls, name, url=None, sandbox_url=None, documentation_url=None, commit=True):
        """Class method to create and save a new exchange."""
        new_exchange = cls(
            name=name,
            url=url,
            sandbox_url=sandbox_url,
            documentation_url=documentation_url
        )
        db.session.add(new_exchange)
        if commit:
            db.session.commit()
        return new_exchange

    @classmethod
    def find_by_name(cls, name):
        """Find an exchange by its name."""
        return cls.query.filter_by(name=name).first()

    @classmethod
    def delete_by_name(cls, name, commit=True):
        """Delete an exchange by its name."""
        exchange = cls.find_by_name(name)
        if exchange:
            db.session.delete(exchange)
            if commit:
                db.session.commit()
            return True
        return False

    def update_exchange(self, **kwargs):
        """Update existing exchange details."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def save(self, commit=True):
        """Save the exchange to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        """Delete the exchange from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()

class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    account_name = db.Column(db.String(50), nullable=True)
    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=False)
    api_permissions = db.Column(db.String(255), nullable=True)  # Simplified to db.String type
    status = db.Column(db.String(50), nullable=False, default='active')
    balance = db.Column(Numeric(precision=20, scale=8), default=Decimal('0.0'))  # Assuming balance can be represented as a db.Float
    open_orders = db.Column(db.Integer, nullable=True)  # Assuming number of open orders
    closed_orders = db.Column(db.Integer, nullable=True)  # Assuming number of closed orders
    transaction_history = db.Column(db.String(255), nullable=True)  # Simplify to a db.String or URL/link
    taker_fee = db.Column(db.Float, nullable=True)
    maker_fee = db.Column(db.Float, nullable=True)
    margin_info = db.Column(db.String(255), nullable=True)  # Assuming a simple db.String can describe the margin info
    last_accessed = db.Column(db.DateTime, nullable=True)
    last_api_error = db.Column(db.String(255), nullable=True)
    rate_limit_status = db.Column(db.String(255), nullable=True)  # Assuming simple status descriptions
    encryption_data = db.Column(db.String(255), nullable=True)  # Assuming encryption key or method description

    exchange = db.relationship('Exchange', back_populates='accounts')

    def __init__(self, user_id, account_name, api_key, api_secret, api_permissions=None, status='active'):
        self.user_id = user_id
        self.account_name = account_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_permissions = api_permissions
        self.status = status
        self.last_accessed = datetime.now()  # Set last accessed time to current time at creation

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_name': self.account_name,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'api_permissions': self.api_permissions,
            'status': self.status,
            'balance': self.balance,
            'open_orders': self.open_orders,
            'closed_orders': self.closed_orders,
            'transaction_history': self.transaction_history,
            'taker_fee': self.taker_fee,
            'maker_fee': self.maker_fee,
            'margin_info': self.margin_info,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'last_api_error': self.last_api_error,
            'rate_limit_status': self.rate_limit_status,
            'encryption_data': self.encryption_data
        }

    
    def to_dict_bot(self):
        """Serialize account details to a dictionary for API responses, excluding sensitive information."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_name': self.account_name,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'api_permissions': self.api_permissions,
            'status': self.status,
            'balance': self.balance,
            'open_orders': self.open_orders,
            'closed_orders': self.closed_orders,
            'transaction_history': self.transaction_history,
            'taker_fee': self.taker_fee,
            'maker_fee': self.maker_fee,
            'margin_info': self.margin_info,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'last_api_error': self.last_api_error,
            'rate_limit_status': self.rate_limit_status,
            'encryption_data': self.encryption_data,
            'exchange_name': self.exchange.name
            
        }

    @classmethod
    def find_by_id(cls, account_id):
        """Find an account by its ID."""
        return cls.query.get(account_id)

    @classmethod
    def find_by_name(cls, name):
        """Find an account by its name."""
        return cls.query.filter_by(name=name).first()

    def update_account(self, **kwargs):
        """Update existing account details."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def save(self, commit=True):
        """Save the account to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        """Delete the account from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()