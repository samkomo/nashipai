# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from datetime import datetime
from flask_login import UserMixin

from apps import db, login_manager

from apps.authentication.util import hash_pass

class User(db.Model, UserMixin):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.LargeBinary)

    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))

    def save(self, commit=True):
        """Save the user to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)
    
    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return any(role.name == role_name for role in self.roles)

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    bio = db.Column(db.Text)
    location = db.Column(db.String(128))
    profile_picture = db.Column(db.String(256))
    contact_number = db.Column(db.String(15))
    kyc_status = db.Column(db.String(50), default='pending')  # e.g., pending, verified, rejected
    kyc_submission_date = db.Column(db.DateTime)
    notification_preferences = db.Column(db.JSON, default=dict)  # Stores user preferences for receiving notifications

    # Relationship with User
    user = db.relationship('User', backref=db.backref('profile', uselist=False, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<UserProfile for User ID {self.user_id}>'

    def submit_kyc(self, submission_date=datetime.utcnow()):
        """Submit KYC for verification."""
        self.kyc_status = 'pending'
        self.kyc_submission_date = submission_date
        self.save()

    def verify_kyc(self):
        """Mark KYC as verified."""
        self.kyc_status = 'verified'
        self.save()

    def reject_kyc(self):
        """Mark KYC as rejected."""
        self.kyc_status = 'rejected'
        self.save()

    def update_notification_preferences(self, preferences):
        """Update user's notification preferences."""
        self.notification_preferences = preferences
        self.save()

    def save(self, commit=True):
        """Save the profile to the database."""
        db.session.add(self)
        if commit:
            db.session.commit()

    def delete(self, commit=True):
        """Delete the profile from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()
            
    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    @classmethod
    def find_by_user_id(cls, user_id):
        """Find a profile by user ID."""
        return cls.query.filter_by(user_id=user_id).first()



class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.DateTime)


@login_manager.user_loader
def user_loader(id):
    return User.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    return user if user else None


class Exchange(db.Model):
    __tablename__ = 'exchanges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Exchange name, e.g., 'binance', 'coinbasepro'
    url = db.Column(db.String(255), nullable=True)  # The main URL of the exchange
    sandbox_url = db.Column(db.String(255), nullable=True)  # Sandbox environment URL, if available
    documentation_url = db.Column(db.String(255), nullable=True)  # URL to exchange's API documentation

    # Relationships
    accounts = db.relationship('Account', backref='exchange', lazy='dynamic')

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

    def add_role(self, role_name):
        """Assign a role to the user."""
        role = Role.query.filter_by(name=role_name).first()
        if role and role not in self.roles:
            self.roles.append(role)
            db.session.commit()

    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return any(role.name == role_name for role in self.roles)



class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    exchange_id = db.Column(db.Integer, db.ForeignKey('exchanges.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Name to identify the account
    api_key = db.Column(db.String(255), nullable=False)
    secret_key = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=True)  # Required for some exchanges
    sandbox_mode = db.Column(db.Boolean, default=False)  # Indicates if this account uses the exchange's sandbox environment
    additional_info = db.Column(db.JSON, nullable=True)  # Any other necessary details

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