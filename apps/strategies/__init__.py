from flask import Blueprint

blueprint = Blueprint(
    'strategies_blueprint',
    __name__,
    url_prefix='/strategies',  # Set the desired URL prefix for the trading blueprint
    template_folder='templates'
)

