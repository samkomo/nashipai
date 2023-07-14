from flask import Blueprint

blueprint = Blueprint(
    'trading_blueprint',
    __name__,
    url_prefix='/trading'  # Set the desired URL prefix for the trading blueprint
)