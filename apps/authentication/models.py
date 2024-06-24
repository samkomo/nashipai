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
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    accounts = db.relationship('Account', back_populates='user', lazy='dynamic')

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'profile':self.profile.to_dict() if self.profile else None,
        }

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
    first_name = db.Column(db.String(20))
    second_name = db.Column(db.String(20))
    last_name = db.Column(db.String(20))
    location = db.Column(db.String(128))
    profile_picture = db.Column(db.String(256))
    contact_number = db.Column(db.String(15))
    kyc_status = db.Column(db.String(50), default='pending')  # e.g., pending, verified, rejected
    kyc_submission_date = db.Column(db.DateTime)
    notification_preferences = db.Column(db.JSON, default=dict)  # Stores user preferences for receiving notifications

    # Relationship with User
    # user = db.relationship('User', backref=db.backref('profile', uselist=False, cascade='all, delete-orphan'))
    def to_dict(self):
        """Serialize review details to a dictionary for API responses or other uses."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    
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

    def add_role(self, role_name):
        """Assign a role to the user."""
        role = Role.query.filter_by(name=role_name).first()
        if role and role not in self.roles:
            self.roles.append(role)
            db.session.commit()

    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return any(role.name == role_name for role in self.roles)

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

