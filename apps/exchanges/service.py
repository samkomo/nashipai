# Let's create the ExchangeService class and get_accounts method

import json
import logging
from apps.exchanges.models import Account, Exchange

logger = logging.getLogger(__name__)

class ExchangeService:

    @staticmethod
    def get_accounts(user_id):
        """
        Retrieve all accounts associated with a user's exchange accounts.

        :param user_id: ID of the user for whom to retrieve the accounts.
        :return: A list of account details including the exchange name, or an error message.
        """
        logger.info("We're inside service")

        try:
            accounts = Account.query.filter_by(user_id=user_id).all()
            account_list = [account.to_dict() for account in accounts]
            return {'status': 'success', 'data': account_list}
        except Exception as e:
            # Log the exception for debugging
            logger.error(f"Failed to retrieve accounts: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve accounts'}