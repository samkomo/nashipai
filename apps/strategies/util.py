# util.py

import re
import pandas as pd


def format_currency(value):
    """Format a number as currency."""
    return "${:,.2f}".format(value)

def pretty_date(time=False):
    """Get a datetime object or a int() Epoch timestamp and return a pretty string like 'an hour ago', 'Yesterday', '3 months ago', 'just now', etc."""
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff // 30) + " months ago"
    return str(day_diff // 365) + " years ago"



def process_csv(filepath, filename):
    # Extract coin_pair, time_frame, and strategy name from the file name using regex
    match = re.search(r"^(?P<coin_pair>\w+)\.P_(?P<time_frame>\d+[hmd]) (?P<strategy>.+?) (?=\[.*\]|-)", filename)

    if match:
        coin_pair = match.group('coin_pair')
        time_frame = match.group('time_frame').replace('m', 'min')  # Convert '15m' to '15min'
        strategy_name = match.group('strategy') + " Strategy by SMK"  # Append "by SMK" to the strategy name
    else:
        # Fallback values or handle error
        coin_pair, time_frame, strategy_name = 'Unknown', 'Unknown', 'Unknown'

    # Reading the CSV file
    df = pd.read_csv(filepath)
    
    # Fixing the approach to extract performance metrics and settings
    # Assume all settings start with '__' and metrics do not.
    metrics_columns = [col for col in df.columns if not col.startswith('__')]
    settings_columns = [col for col in df.columns if col.startswith('__')]

    # Assuming the first row contains the desired data.
    strategy_metrics = df[metrics_columns].iloc[0].to_dict()
    strategy_settings = df[settings_columns].iloc[0].to_dict()

    return coin_pair, time_frame, strategy_name, strategy_metrics, strategy_settings


def normalize_key(key):
    # Clean and normalize the key as specified
    return (key.replace(' ', '_')
            .replace(':', '')
            .replace('#', 'num')
            .replace('%', 'percent')
            .replace('-', '')
            .replace('&', 'and')
            .replace('/_', '_')
            .lower())