from apps import db

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
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Name to identify the account
    api_key = db.Column(db.String(255), nullable=False)
    secret_key = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=True)  # Required for some exchanges
    sandbox_mode = db.Column(db.Boolean, default=False)  # Indicates if this account uses the exchange's sandbox environment
    additional_info = db.Column(db.JSON, nullable=True)  # Any other necessary details

    exchange = db.relationship('Exchange', back_populates='accounts')


    def to_dict(self):
        """Serialize account details to a dictionary for API responses, excluding sensitive information."""
        return {
            'id': self.id,
            'name': self.name,
            'exchange_id': self.exchange_id,
            'user_id': self.user_id,
            'api_key': self.api_key,
            'secret_key': self.secret_key,
            'password': self.password,
            'sandbox_mode': self.sandbox_mode,
            'additional_info': self.additional_info
        }
    
    def to_dict_bot(self):
        """Serialize account details to a dictionary for API responses, excluding sensitive information."""
        return {
            'id': self.id,
            'name': self.name,
            'exchange_id': self.exchange_id,
            'user_id': self.user_id,
            'api_key': self.api_key,
            'secret_key': self.secret_key,
            'password': self.password,
            'sandbox_mode': self.sandbox_mode,
            'additional_info': self.additional_info,
            'exchange_name': self.exchange.name
            
        }

    def __repr__(self):
        return f'<Account {self.name} on Exchange {self.exchange.name}>'

    @classmethod
    def create_account(cls, exchange_id, name, api_key, secret_key, password=None, sandbox_mode=False, additional_info=None, commit=True):
        """Class method to create and save a new account."""
        new_account = cls(
            exchange_id=exchange_id,
            name=name,
            api_key=api_key,
            secret_key=secret_key,
            password=password,
            sandbox_mode=sandbox_mode,
            additional_info=additional_info
        )
        db.session.add(new_account)
        if commit:
            db.session.commit()
        return new_account

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