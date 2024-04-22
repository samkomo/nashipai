import json
import logging
from flask import jsonify
from flask_login import current_user, login_required
from apps.authentication import blueprint
from apps.exchanges.service import ExchangeService
logger = logging.getLogger(__name__)

@blueprint.route('/get-accounts', methods=['GET'])
@login_required
def get_accounts():
    try:
        logger.info(f'retreiving accounts for user ID: {current_user.id}')
        # Replace with your method that gets the list of exchange accounts for the current user
        accounts = ExchangeService.get_accounts(current_user.id)
        # account_list = [
        #     {'id': account.id, 'display_name': f"{account.name} - {account.exchange.name}"}
        #     for account in accounts
        # ]
        print(json.dumps(accounts, indent=2))
        return jsonify(accounts['data']), 200
    except Exception as e:
        # Log the exception if logging is set up
        logger.error(f"Failed to get accounts: {e}")
        return jsonify({'message': 'Unable to retrieve accounts.'}), 500



