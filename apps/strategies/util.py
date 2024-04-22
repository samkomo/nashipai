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



def process_csv(filepath):
    # Extracting filename from the filepath
    filename = filepath.split('/')[-1]
    
    # Regex pattern to extract coin_pair, time_frame, and strategy_name
    regex_pattern = r'^(?P<coin_pair>[A-Z0-9]+(?:\.[A-Z0-9]+)*)[._](?P<time_frame>\d+[mhD])_(?P<strategy_name>.*?Strategy.*?)(?=-)'
    
    # Extract coin_pair, time_frame, and strategy name from the file name using regex
    match = re.search(regex_pattern, filename)
    if not match:
        return {'status': 'error', 'message': 'Failed to extract essential details from filename'}

    # Extracted details
    details = match.groupdict()
    details['strategy_name'] = details['strategy_name'].replace('_', ' ')  # Replacing underscores with spaces
    # Converting time_frame to a more readable format
    time_frame = details['time_frame']
    if time_frame.endswith('m'):
        details['time_frame'] = time_frame.replace('m', 'min')
    elif time_frame.endswith('h'):
        details['time_frame'] = time_frame.replace('h', ' hours')
    elif time_frame.endswith('D'):
        details['time_frame'] = time_frame.replace('D', ' day')
    
    try:
        # Reading the CSV file
        df = pd.read_csv(filepath)
        
        # Extracting strategy metrics and settings
        metrics_columns = [col for col in df.columns if not col.startswith('__')]
        settings_columns = [col for col in df.columns if col.startswith('__')]
        
        # Assuming the first row contains the desired data
        strategy_metrics = df[metrics_columns].iloc[0].to_dict()
        strategy_settings = df[settings_columns].iloc[0].to_dict()
        
        details.update({
            'status': 'success',  # Indicating successful processing
            'strategy_metrics': strategy_metrics,
            'strategy_settings': strategy_settings
        })
        
        return details
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}