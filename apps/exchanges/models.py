from datetime import datetime, timedelta
from apps import db
from decimal import Decimal
from sqlalchemy import Numeric

class Exchange(db.Model):
    __tablename__ = 'exchanges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    url = db.Column(db.String(255), nullable=True)
    sandbox_url = db.Column(db.String(255), nullable=True)
    documentation_url = db.Column(db.String(255), nullable=True)

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
    status = db.Column(db.String(50), nullable=False, default='active')
    balance = db.Column(Numeric(precision=20, scale=8), default=Decimal('0.0'))
    open_orders = db.Column(db.Integer, nullable=True)
    closed_orders = db.Column(db.Integer, nullable=True)
    last_accessed = db.Column(db.DateTime, nullable=True)

    # Fees
    taker_fee = db.Column(db.Float, nullable=True)
    maker_fee = db.Column(db.Float, nullable=True)

    # Margin info
    margin_info = db.Column(db.String(255), nullable=True)

    # API rate limit status
    rate_limit_status = db.Column(db.String(255), nullable=True)

    # Relationships
    exchange = db.relationship('Exchange', back_populates='accounts')
    user = db.relationship('User', back_populates='accounts')
    api_credentials = db.relationship('APICredentials', back_populates='account', uselist=False)
    transactions = db.relationship('Transaction', back_populates='account', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_name': self.account_name,
            'status': self.status,
            'balance': float(self.balance),
            'open_orders': self.open_orders,
            'closed_orders': self.closed_orders,
            'taker_fee': self.taker_fee,
            'maker_fee': self.maker_fee,
            'margin_info': self.margin_info,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'rate_limit_status': self.rate_limit_status,
            'exchange_name': self.exchange.name
        }

    @classmethod
    def find_by_id(cls, account_id):
        return cls.query.get(account_id)

    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    def update_account(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        db.session.delete(self)
        if commit:
            db.session.commit()

class APICredentials(db.Model):
    __tablename__ = 'api_credentials'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=False)
    api_permissions = db.Column(db.String(255), nullable=True)
    encryption_data = db.Column(db.String(255), nullable=True)

    account = db.relationship('Account', back_populates='api_credentials')


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # e.g., 'deposit', 'withdrawal', 'trade'
    amount = db.Column(Numeric(precision=20, scale=8), nullable=False)
    currency = db.Column(db.String(10), nullable=False)  # e.g., 'USDT', 'BTC'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    account = db.relationship('Account', back_populates='transactions')

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'currency': self.currency,
            'timestamp': self.timestamp.isoformat()
        }
