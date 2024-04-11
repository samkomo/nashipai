from datetime import datetime, timedelta
import json

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
    performance_metrics = db.relationship('StrategyPerformanceMetrics', backref='strategy', uselist=False)
    # subscriptions = db.relationship('Subscription', backref='strategy', lazy='dynamic')
    reviews = db.relationship('StrategyReview', backref='strategy', lazy='dynamic')
    strategy_metadata = db.relationship('StrategyMetadata', backref='strategy', lazy='dynamic')

    def __repr__(self):
        return f'<Strategy {self.strategy_name} by Developer ID {self.developer_id}>'

    @classmethod
    def create(cls, strategy_name, developer_id, coin_pair, time_frame, description=None, settings_file_path=None, status='active'):
        """Create a new strategy instance."""
        strategy = cls(
            strategy_name=strategy_name,
            developer_id=developer_id,
            coin_pair=coin_pair,
            time_frame=time_frame,
            description=description,
            settings_file_path=settings_file_path,
            status=status
        )
        db.session.add(strategy)
        db.session.commit()
        return strategy

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

    def to_dict(self):
        """
        Serialize the strategy object along with its related objects.
        """
        strategy_data = {
            'id': self.id,
            'developer_id': self.developer_id,
            'strategy_name': self.strategy_name,
            'description': self.description,
            'status': self.status,
            'creation_date': self.creation_date.isoformat(),
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'coin_pair': self.coin_pair,
            'time_frame': self.time_frame,
            'settings_file_path': self.settings_file_path,
            'performance_metrics': self.performance_metrics.to_dict() if self.performance_metrics else None,
            'reviews': [review.to_dict() for review in self.reviews],
            # 'strategy_metadata': [metadata.to_dict() for metadata in self.strategy_metadata]
        }
        return strategy_data
    
    def save(self):
        db.session.add(self)
        db.session.commit()

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=False)
    trader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)  # Automatically set to True upon creation

    # Relationships
    strategy = db.relationship('Strategy', backref=db.backref('subscriptions', lazy='dynamic'))
    trader = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))

    def __repr__(self):
        return f'<Subscription Strategy ID: {self.strategy_id}, Trader ID: {self.trader_id}>'

    @classmethod
    def create(cls, strategy_id, trader_id, end_date=None):
        """Create a new subscription instance."""
        subscription = cls(
            strategy_id=strategy_id,
            trader_id=trader_id,
            end_date=end_date
        )
        db.session.add(subscription)
        db.session.commit()
        return subscription

    def deactivate(self):
        """Deactivate the subscription."""
        self.is_active = False
        db.session.commit()

    def activate(self):
        """Reactivate the subscription."""
        self.is_active = True
        db.session.commit()

    def extend(self, additional_days):
        """Extend the subscription end date."""
        if not self.end_date:
            self.end_date = datetime.utcnow()
        self.end_date += timedelta(days=additional_days)
        db.session.commit()

    def is_subscription_active(self):
        """Check if the subscription is currently active."""
        if self.is_active and (self.end_date is None or self.end_date > datetime.utcnow()):
            return True
        self.is_active = False  # Automatically deactivate if conditions are not met
        db.session.commit()
        return False

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
    rating = db.Column(db.Integer, nullable=False)  # Consider a scale, e.g., 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('strategy_reviews', lazy='dynamic'))

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