# util.py
import hashlib
import json
import logging
import time
from cryptography.fernet import Fernet
import os

from flask import app
import pika

from apps.trading.service import TradingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def generate_key():
    """Generate a new encryption key."""
    return Fernet.generate_key()

def encrypt_message(message, key):
    """Encrypt a message using a key."""
    fernet = Fernet(key)
    encrypted_message = fernet.encrypt(message.encode())
    return encrypted_message.decode()

def decrypt_message(encrypted_message, key):
    """Decrypt an encrypted message using a key."""
    fernet = Fernet(key)
    decrypted_message = fernet.decrypt(encrypted_message.encode())
    return decrypted_message.decode()


def load_encryption_key():
    """Load the encryption key from an environment variable or file."""
    # Example: Load from an environment variable
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("Encryption key not found. Make sure ENCRYPTION_KEY is set.")
    return key


def format_value(key, value):
    if value in [None, 'N/A']:
        return 'N/A'
    if 'percent' in key:
        # Check if the value is already formatted as a string
        if isinstance(value, str) and '%' in value:
            return value
        return f"{value:.2f}%"
    if any(x in key for x in ['profit', 'loss', 'return', 'trade', 'paid']):
        # Check if the value is already formatted as a string
        if isinstance(value, str) and '$' in value:
            return value
        return f"${value:,.2f}"
    return value



def generate_trade_uid(base_string):
    """
    Generates a unique identifier for a trade based on a base string.
    
    :param base_string: A string from which to generate the UID.
    :return: A unique identifier.
    """
    return hashlib.sha1(base_string.encode()).hexdigest()


def calculate_profit_and_percentage(entry_price, exit_price, size, side, leverage=10):
    if side == 'buy':  # Long position
        profit = (exit_price - entry_price) * size
    else:  # Short position
        profit = (entry_price - exit_price) * size
    
    # Adjust percentage profit calculation to consider leverage
    percentage_profit = ((profit / (entry_price * size)) * 100) * leverage

    # Limit profit and percentage profit to 2 decimal points
    profit = round(profit, 2)
    percentage_profit = round(percentage_profit, 2)

    return profit, percentage_profit

# Configure logging

def get_connection_with_retry(max_retries=5, retry_delay=10):
    url = os.environ['CLOUDAMQP_URL']
    params = pika.URLParameters(url)
    params.connection_attempts = 3
    params.retry_delay = 5  # Time in seconds to wait before retrying connection
    retry_count = 0
    while retry_count < max_retries:
        try:
            return pika.BlockingConnection(params)
        except pika.exceptions.AMQPConnectionError as error:
            if "connection limit" in str(error):
                logging.warning("Connection limit reached, retrying in %s seconds...", retry_delay)
                time.sleep(retry_delay)
                retry_count += 1
            else:
                logging.error("Failed to connect to RabbitMQ: %s", error)
                raise
    raise Exception("Failed to connect to RabbitMQ after several retries.")


def get_connection_with_retry(max_retries=5, retry_delay=10):
    url = os.environ['CLOUDAMQP_URL']
    params = pika.URLParameters(url)
    params.connection_attempts = 3
    params.retry_delay = 5  # Time in seconds to wait before retrying connection
    retry_count = 0
    while retry_count < max_retries:
        try:
            return pika.BlockingConnection(params)
        except pika.exceptions.AMQPConnectionError as error:
            if "connection limit" in str(error):
                logging.warning("Connection limit reached, retrying in %s seconds...", retry_delay)
                time.sleep(retry_delay)
                retry_count += 1
            else:
                logging.error("Failed to connect to RabbitMQ: %s", error)
                raise
    raise Exception("Failed to connect to RabbitMQ after several retries.")

def send_message_to_queue(data):
    connection = None  # Initialize connection to None to avoid UnboundLocalError
    try:
        connection = get_connection_with_retry()
        channel = connection.channel()
        channel.queue_declare(queue='trade_alerts', durable=True)
        channel.basic_publish(
            exchange='',
            routing_key='trade_alerts',
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2)  # make message persistent
        )
    except Exception as e:
        logging.error("Failed to send message: %s", e)
    finally:
        if connection:  # Check if connection was successfully established before trying to close
            connection.close()
