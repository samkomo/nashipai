from datetime import datetime, timedelta
import json
from flask_login import current_user

import pandas as pd
from apps import db
from apps.strategies.util import normalize_key

class Strategy(db.Model):
    __tablename__ = 'strategies'
    id = db.Column(db.Integer, primary_key=True)
    developer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strategy_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # e.g., active, inactive, under review
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, onupdate=datetime.utcnow)
    coin_pair = db.Column(db.String(20), nullable=False)
    time_frame = db.Column(db.String(10), nullable=False)
    settings_file_path = db.Column(db.String, nullable=True)  # Path to the strategy's configuration or settings file
    
    # Relationships
    developer = db.relationship('User', backref=db.backref('strategies', lazy=True))
    performance_metrics = db.relationship('StrategyPerformanceMetrics', backref='strategy', uselist=False, cascade='all, delete-orphan')
    trading_bots = db.relationship('TradingBot', back_populates='strategy', lazy='dynamic')
    # subscriptions = db.relationship('Subscription', backref='strategy', lazy='dynamic')
    # Define the relationship to StrategyReview and specify the back_populates
    reviews = db.relationship('StrategyReview', back_populates='strategy')

    strategy_metadata = db.relationship('StrategyMetadata', backref='strategy', lazy='dynamic', cascade='all, delete-orphan')
    @property
    def subscribers_count(self):
        """Property to count the number of subscribers a strategy has."""
        return len(self.subscriptions.all())
    # Add a relationship to TradingBot

    # Add method to check if the current user has created a bot from this strategy
    def has_user_botified(self, user_id):
        """Check if the current user has created a trading bot for this strategy."""
        return self.trading_bots.filter_by(user_id=user_id).count() > 0
    
    def is_user_subscribed(self):
        # Assuming there is a many-to-many relationship between users and strategies
        return any(sub.user_id == current_user.id for sub in self.subscriptions)
    
    def to_dict(self):
        """ Serialize the strategy object along with its related objects. """
        current_date = datetime.utcnow()
        
        days_ago = (current_date - self.creation_date).days if self.creation_date else None

        strategy_data = {
            'id': self.id,
            'developer_id': self.developer_id,
            'strategy_name': self.strategy_name,
            'description': self.description,
            'status': self.status,
            'creation_date': self.creation_date.strftime('%Y-%m-%d') if self.creation_date else None,
            'days_ago': days_ago,
            'coin_pair': self.coin_pair,
            'time_frame': self.time_frame,
            'developer_username': self.developer.username if self.developer else 'Unknown',
            'settings_file_path': self.settings_file_path,
            'performance_metrics': self.performance_metrics.to_dict() if self.performance_metrics else None,
            'reviews': [review.to_dict() for review in self.reviews],
            # 'strategy_metadata': [metadata.to_dict() for metadata in self.strategy_metadata],
            'average_rating': self.get_average_rating(),  # Call without argument
            'subscribers_count': self.subscribers_count,  # Include subscriber count in serialized data
            'is_subscribed': self.is_user_subscribed(),
            'is_botified': self.has_user_botified(current_user.id)

        }
        # Here's how you might incorporate the average rating:
        return strategy_data

    @staticmethod
    def list_to_dict(strategies):
        """
        Converts a list of Strategy instances into a list of dictionaries.
        """
        return [strategy.to_dict() for strategy in strategies]
    
    # Assuming existing model setup
    def to_dict_bot(self):
        """ Simplified strategy serialization for nested use in TradingBot """
        return {
            'id': self.id,
            'name': self.strategy_name,
            'description': self.description,
            'coin_pair': self.coin_pair,
            'time_frame': self.time_frame,
            'status': self.status
        }

    def __repr__(self):
        return f'<Strategy {self.strategy_name} by Developer ID {self.developer_id}>'

    def get_average_rating(self):
        # Here, self.reviews is expected to be a relationship query, not a list
        total_reviews = len(self.reviews)  # If self.reviews is a list after conversion in to_dict
        if total_reviews > 0:
            total_rating = sum(review.rating for review in self.reviews)  # Directly access the attribute
            return total_rating / total_reviews
        return 0

    


    @classmethod
    def find_by_id(cls, id):
        """Find a strategy by its ID."""
        return cls.query.filter_by(id=id).first()

    def update(self, **kwargs):
        """Update strategy details."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()

    def deactivate(self):
        """Deactivate the strategy."""
        self.status = 'inactive'
        db.session.commit()

    def activate(self):
        """Activate the strategy."""
        self.status = 'active'
        db.session.commit()

    def delete(self):
        """Delete the strategy."""
        db.session.delete(self)
        db.session.commit()   
    
    def save(self):
        db.session.add(self)
        db.session.commit()

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=False)
    subscribed_on = db.Column(db.DateTime, default=datetime.utcnow)
    expires_on = db.Column(db.DateTime, nullable=True)
    subscription_type = db.Column(db.String(50))  # E.g., 'free', 'monthly', 'yearly'
    cost = db.Column(db.Float, default=0.0)  # Subscription cost
    payment_status = db.Column(db.String(50), default='pending')  # E.g., 'pending', 'paid', 'failed'

    user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))
    strategy = db.relationship('Strategy', backref=db.backref('subscriptions', lazy='dynamic'))

    def __init__(self, user_id, strategy_id, subscription_type):
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.subscription_type = subscription_type
        self.subscribed_on = datetime.utcnow()

        if subscription_type == 'monthly':
            self.expires_on = self.subscribed_on + timedelta(days=30)
            self.cost = 10.0  # Set cost for monthly
        elif subscription_type == 'yearly':
            self.expires_on = self.subscribed_on + timedelta(days=365)
            self.cost = 100.0  # Set cost for yearly
        elif subscription_type == 'free':
            self.expires_on = None  # Never expires or a specific long duration
            self.cost = 0.0

        self.payment_status = 'pending' if self.cost > 0 else 'n/a'  # Payment not applicable if free


    def __repr__(self):
        return f'<Subscription {self.subscription_type} for user_id={self.user_id} strategy_id={self.strategy_id}>'

    @property
    def is_active(self):
        """Check if the subscription is active based on the expiration date."""
        return self.expires_on is None or self.expires_on > datetime.utcnow()
    

    def to_dict(self):
        """Convert subscription details to a dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def save(self):
        db.session.add(self)
        db.session.commit()


class StrategyMetadata(db.Model):
    __tablename__ = 'strategy_metadata'
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=False)
    key = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<StrategyMetadata {self.key}: {self.value} for Strategy ID {self.strategy_id}>'

    @classmethod
    def create(cls, strategy_id, key, value):
        """Create a new metadata entry for a strategy."""
        new_metadata = cls(strategy_id=strategy_id, key=key, value=value)
        db.session.add(new_metadata)
        db.session.commit()
        return new_metadata

    @classmethod
    def find_by_strategy_id(cls, strategy_id):
        """Find all metadata entries for a given strategy."""
        return cls.query.filter_by(strategy_id=strategy_id).all()

    @classmethod
    def update_or_create(cls, strategy_id, key, value):
        """Update an existing metadata entry or create it if it doesn't exist."""
        existing_metadata = cls.query.filter_by(strategy_id=strategy_id, key=key).first()
        if existing_metadata:
            existing_metadata.value = value
        else:
            existing_metadata = cls.create(strategy_id, key, value)
        db.session.commit()
        return existing_metadata

    def delete(self):
        """Delete the metadata entry."""
        db.session.delete(self)
        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'key': self.key,
            'value': self.value
        }

class StrategyReview(db.Model):
    __tablename__ = 'strategy_reviews'

    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # You might use a scale of 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    # Define the relationship back to Strategy and specify the back_populates
    strategy = db.relationship('Strategy', back_populates='reviews')
    user = db.relationship('User', backref=db.backref('reviews', lazy='dynamic'))

    def __repr__(self):
        return f'<StrategyReview {self.rating} by User ID {self.user_id} for Strategy ID {self.strategy_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<StrategyReview Strategy ID: {self.strategy_id}, User ID: {self.user_id}>'

    @classmethod
    def create_review(cls, strategy_id, user_id, rating, comment=None):
        """Create and save a new review."""
        review = cls(strategy_id=strategy_id, user_id=user_id, rating=rating, comment=comment)
        db.session.add(review)
        db.session.commit()
        return review

    @classmethod
    def find_by_strategy_id(cls, strategy_id):
        """Retrieve all reviews for a specific strategy."""
        return cls.query.filter_by(strategy_id=strategy_id).all()

    @classmethod
    def find_by_user_id(cls, user_id):
        """Retrieve all reviews made by a specific user."""
        return cls.query.filter_by(user_id=user_id).all()

    def update_review(self, rating=None, comment=None):
        """Update the rating and/or comment of the review."""
        if rating is not None:
            self.rating = rating
        if comment is not None:
            self.comment = comment
        db.session.commit()

    def delete(self):
        """Delete the review."""
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        """Serialize review details to a dictionary for API responses or other uses."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    

class StrategyPerformanceMetrics(db.Model):
    __tablename__ = 'strategy_performance_metrics'
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=False)
    settings=db.Column(db.JSON)
    metrics=db.Column(db.JSON)

    def to_dict(self):
        """Serialize the strategy performance metrics to a dictionary."""
        # Assuming 'metrics' column stores JSON data
        raw_metrics = json.loads(self.metrics) if self.metrics else {}

        # Normalize and clean each key in the metrics dictionary
        cleaned_metrics = {normalize_key(k): v for k, v in raw_metrics.items()}

        data = {
            'id': self.id,
            'strategy_id': self.strategy_id,
            'settings': json.loads(self.settings) if self.settings else {},
            'metrics': cleaned_metrics,
        }
        return data

    def __repr__(self):
        return f'<StrategyPerformanceMetrics for Strategy ID: {self.strategy_id}>'

    @classmethod
    def create_or_update(cls, strategy_id, **metrics):
        """Create or update strategy performance metrics."""
        instance = cls.query.filter_by(strategy_id=strategy_id).first()
        if not instance:
            instance = cls(strategy_id=strategy_id)
            db.session.add(instance)
        for key, value in metrics.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    
    
    
    @staticmethod
    def handle_nan(value):
        """Convert NaN values to None."""
        return None if pd.isna(value) else value

    @classmethod
    def create_from_dict(cls, data_dict):
        """Create a new StrategyPerformanceMetrics instance from a dictionary."""
        cleaned_data = {k: cls.handle_nan(v) for k, v in data_dict.items() if k in cls.__table__.columns.keys()}
        metrics = cls(**cleaned_data)
        db.session.add(metrics)
        db.session.commit()
        return metrics

    def save(self):
        db.session.add(self)
        db.session.commit()