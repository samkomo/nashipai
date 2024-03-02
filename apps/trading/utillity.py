# util.py
import hashlib
from cryptography.fernet import Fernet
import os

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