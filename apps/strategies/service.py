from datetime import datetime, timedelta
import json
import logging

import pandas as pd
from apps.authentication.models import User
from apps.strategies.models import Strategy, StrategyMetadata, StrategyPerformanceMetrics, Subscription
from apps import db
from apps.strategies.util import normalize_key

logger = logging.getLogger(__name__)

class StrategyService:
    @staticmethod
    def create_strategy(strategy_data, strategy_metrics, strategy_settings):
        try:
            # Create and save the main Strategy instance
            new_strategy = Strategy(**strategy_data)
            db.session.add(new_strategy)
            db.session.flush()  # Flush to get the strategy_id before committing

            # Assume performance metrics are to be stored in a single JSON column
            # Adjust according to your model structure
            performance_metrics_instance = StrategyPerformanceMetrics(
                strategy_id=new_strategy.id,
                metrics=json.dumps(strategy_metrics)  # Assuming a JSON column for simplicity
            )
            db.session.add(performance_metrics_instance)

            # Save each setting as a separate entry in strategy metadata
            for key, value in strategy_settings.items():
                normalized_key = normalize_key(key)  # Normalize key if necessary
                metadata_instance = StrategyMetadata(
                    strategy_id=new_strategy.id,
                    key=normalized_key,
                    value=value
                )
                db.session.add(metadata_instance)

            db.session.commit()
            return {'status': 'success', 'message': 'Strategy created successfully.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Failed to create strategy: {e}'}
    @staticmethod
    def update_strategy(strategy_id, strategy_data):
        """
        Updates an existing trading strategy.
        :param strategy_id: ID of the strategy to update.
        :param strategy_data: Updated strategy details.
        :return: Update status and updated strategy details.
        """
        strategy = Strategy.find_by_id(strategy_id)
        if not strategy:
            return {'status': 'error', 'message': 'Strategy not found.'}

        try:
            for key, value in strategy_data.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)
            strategy.updated_date = datetime.utcnow()  # Manually set updated_date
            db.session.commit()
            return {'status': 'success', 'message': 'Strategy updated successfully.', 'strategy': strategy.to_dict()}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Failed to update strategy: {e}'}

    @staticmethod
    def upload_strategy_settings(strategy_id, csv_file_path):
        """
        Parses a CSV file and updates/creates strategy settings in the database.
        :param strategy_id: ID of the strategy to which settings will be attached.
        :param csv_file_path: Path to the uploaded CSV file.
        :return: Status message indicating success or failure.
        """
        strategy = Strategy.find_by_id(strategy_id)
        if not strategy:
            return {'status': 'error', 'message': 'Strategy not found.'}

        try:
            # Load CSV file
            df = pd.read_csv(csv_file_path)
            # Iterate over rows and update/create metadata entries
            for _, row in df.iterrows():
                StrategyMetadata.update_or_create(strategy_id=strategy_id, key=row['Parameter'], value=row['Value'])
            return {'status': 'success', 'message': 'Strategy settings uploaded successfully.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Failed to upload strategy settings: {e}'}
        
    @staticmethod
    def download_strategy_settings(strategy_id):
        """
        Prepares strategy settings for download as a CSV file.
        :param strategy_id: ID of the strategy whose settings will be downloaded.
        :return: Path to the generated CSV file or an error message.
        """
        strategy_metadata = StrategyMetadata.find_by_strategy_id(strategy_id=strategy_id)
        if not strategy_metadata:
            return {'status': 'error', 'message': 'No settings found for the strategy.'}

        # Convert metadata to DataFrame
        df = pd.DataFrame([{'Parameter': md.key, 'Value': md.value} for md in strategy_metadata])
        csv_file_path = f'/path/to/downloaded/settings_strategy_{strategy_id}.csv'  # Define path dynamically
        try:
            # Save DataFrame to CSV
            df.to_csv(csv_file_path, index=False)
            return {'status': 'success', 'file_path': csv_file_path}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to prepare settings for download: {e}'}

        
    @staticmethod
    def delete_strategy(strategy_id, current_user_id):
        """
        Deletes a trading strategy and its related data.
        :param strategy_id: ID of the strategy to delete.
        :return: Deletion status.
        """
        strategy = Strategy.query.get(strategy_id)
        if not strategy:
            return {'status': 'error', 'message': 'Strategy not found.'}
        
        if strategy.developer_id != current_user_id:
            return {'status': 'error', 'message': 'Unauthorized to delete this strategy.'}

        try:
            # Optional: Delete related data (e.g., performance metrics, subscriptions)
            # This step depends on your database design and whether you're using cascading deletes.
            
            db.session.delete(strategy)
            db.session.commit()
            return {'status': 'success', 'message': 'Strategy deleted successfully.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Failed to delete strategy: {str(e)}'}

    @staticmethod
    def get_strategy(strategy_id):
        """
        Retrieves details of a specific strategy.
        :param strategy_id: ID of the strategy.
        :return: Dictionary containing strategy details or an error message.
        """
        strategy = Strategy.find_by_id(strategy_id)
        if strategy:
            # Assuming to_dict method exists and properly serializes strategy details,
            # including any relationships like developer information, reviews, etc.
            return {'status': 'success', 'data': strategy.to_dict()}
        else:
            return {'status': 'error', 'message': 'Strategy not found.'} 

    @staticmethod
    def list_strategies(filter_criteria=None):
        """
        Lists all strategies, optionally filtered by criteria.
        :param filter_criteria: Criteria for filtering the strategies. This should be a dictionary where
                                keys are column names and values are the expected column values.
        :return: A dictionary with the list of serialized strategies or an error message.
        """
        try:
            query = Strategy.query
            
            if filter_criteria:
                for key, value in filter_criteria.items():
                    if hasattr(Strategy, key):
                        query = query.filter(getattr(Strategy, key) == value)

            strategies = query.all()
            return {'status': 'success', 'strategies': Strategy.list_to_dict(strategies)}
        except Exception as e:
            # Log the error and return an error message
            return {'status': 'error', 'message': f'Failed to list strategies: {str(e)}'}

    @staticmethod
    def subscribe_to_strategy(user_id, strategy_id, subscription_type):
        """
        Subscribes a user to a strategy.
        :param user_id: ID of the subscribing user.
        :param strategy_id: ID of the strategy to subscribe to.
        :return: Subscription status.
        """
        # Validate user and strategy exist
        user = User.query.get(user_id)
        strategy = Strategy.query.get(strategy_id)
        if not user or not strategy:
            return {'status': 'error', 'message': 'User or Strategy not found.'}
        
        # Check if the user is already subscribed to the strategy
        subscription = Subscription.query.filter_by(user_id=user_id, strategy_id=strategy_id).first()
        if subscription and subscription.is_active:
            return {'status': 'error', 'message': 'Already subscribed to this strategy.'}

        # Create new subscription
        new_subscription = Subscription(user_id=user_id, strategy_id=strategy_id, subscription_type=subscription_type)
        db.session.add(new_subscription)
        try:
            db.session.commit()
            return {'status': 'success', 'message': 'Subscription successful'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Failed to subscribe: {str(e)}'}

    @staticmethod
    def unsubscribe_from_strategy(user_id, strategy_id):
        """
        Unsubscribes a user from a strategy.
        :param user_id: ID of the user.
        :param strategy_id: ID of the strategy to unsubscribe from.
        :return: Unsubscription status.
        """
        # Find the subscription
        subscription = Subscription.query.filter_by(user_id=user_id, strategy_id=strategy_id).first()
        if not subscription:
            return {'status': 'error', 'message': 'Subscription not found.'}
        
        db.session.delete(subscription)
        try:
            db.session.commit()
            return {'status': 'success', 'message': 'Unsubscribed successfully'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Error during unsubscription: {str(e)}'}

    @staticmethod
    def list_user_subscriptions(user_id):
        """
        Lists all strategies a user is subscribed to.
        :param user_id: ID of the user.
        :return: A dictionary with a status and a list of subscribed strategies.
        """
        subscriptions = Subscription.query.filter_by(user_id=user_id, is_active=True).all()
        if not subscriptions:
            return {'status': 'error', 'message': 'No active subscriptions found for the user.'}

        subscribed_strategies = []
        for subscription in subscriptions:
            strategy = Strategy.query.get(subscription.strategy_id)
            if strategy:
                subscribed_strategies.append(strategy.to_dict())  # Assuming Strategy model has a to_dict method
        
        return {'status': 'success', 'strategies': subscribed_strategies}

    @staticmethod
    def record_strategy_performance(strategy_id, csv_file_path):
        """
        Records or updates performance metrics for a strategy from a CSV file.
        :param strategy_id: ID of the strategy.
        :param csv_file_path: Path to the CSV file containing performance metrics.
        :return: Performance recording status.
        """
        # Read the CSV file, assuming the first row contains the optimal metrics
        try:
            df = pd.read_csv(csv_file_path)
            # Select the first row
            optimal_metrics = df.iloc[0].to_dict()
            
            # Filter out columns starting with "__", as they're not part of performance metrics
            performance_data = {k: v for k, v in optimal_metrics.items() if not k.startswith("__")}
            
            # Check if there's an existing record for the strategy
            performance_record = StrategyPerformanceMetrics.query.filter_by(strategy_id=strategy_id).first()
            
            if performance_record:
                # Update existing record
                for key, value in performance_data.items():
                    if hasattr(performance_record, key):
                        setattr(performance_record, key, value)
            else:
                # Create a new record
                performance_record = StrategyPerformanceMetrics(strategy_id=strategy_id, **performance_data)
            
            # Save the path to the CSV file for future reference
            # Assuming there's a field in the Strategy or StrategyPerformanceMetrics model for this
            performance_record.csv_file_path = csv_file_path
            
            performance_record.save()
            return {'status': 'success', 'message': 'Performance metrics recorded successfully.'}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Failed to record performance metrics: {str(e)}'}

    @staticmethod
    def get_strategy_performance(strategy_id):
        """
        Retrieves recorded performance metrics for a strategy.
        :param strategy_id: ID of the strategy.
        :return: Dictionary with performance metrics or an error message.
        """
        performance_metrics = StrategyPerformanceMetrics.query.filter_by(strategy_id=strategy_id).first()
        
        if performance_metrics:
            return {'status': 'success', 'metrics': performance_metrics.to_dict()}
        else:
            return {'status': 'error', 'message': 'Performance metrics not found for the specified strategy.'}
