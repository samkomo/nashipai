# Let's create the ExchangeService class and get_accounts method


import logging
from datetime import datetime
from apps import db
from apps.exchanges.models import Account, Exchange, Transaction

logger = logging.getLogger(__name__)

class AccountService:
    @staticmethod
    def get_accounts(user_id):
        try:
            accounts = Account.query.filter_by(user_id=user_id).all()
            account_list = [account.to_dict() for account in accounts]
            return {'status': 'success', 'data': account_list}
        except Exception as e:
            logger.error(f"Failed to retrieve accounts: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve accounts'}
        finally:
            db.session.remove()

    @staticmethod
    def create_account(data):
        try:
            new_account = Account(**data)
            db.session.add(new_account)
            db.session.commit()
            return {'status': 'success', 'data': new_account.to_dict()}
        except Exception as e:
            logger.error(f"Failed to create account: {str(e)}")
            return {'status': 'error', 'message': 'Failed to create account'}
        finally:
            db.session.remove()

    @staticmethod
    def update_account(account_id, data):
        try:
            account = Account.query.get(account_id)
            if not account:
                return {'status': 'error', 'message': 'Account not found'}
            account.update_account(**data)
            return {'status': 'success', 'data': account.to_dict()}
        except Exception as e:
            logger.error(f"Failed to update account: {str(e)}")
            return {'status': 'error', 'message': 'Failed to update account'}
        finally:
            db.session.remove()

    @staticmethod
    def delete_account(account_id):
        try:
            account = Account.query.get(account_id)
            if not account:
                return {'status': 'error', 'message': 'Account not found'}
            account.delete()
            return {'status': 'success', 'message': 'Account deleted successfully'}
        except Exception as e:
            logger.error(f"Failed to delete account: {str(e)}")
            return {'status': 'error', 'message': 'Failed to delete account'}
        finally:
            db.session.remove()

class ExchangeService:
    @staticmethod
    def get_exchanges():
        try:
            exchanges = Exchange.query.all()
            exchange_list = [exchange.to_dict() for exchange in exchanges]
            return {'status': 'success', 'data': exchange_list}
        except Exception as e:
            logger.error(f"Failed to retrieve exchanges: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve exchanges'}
        finally:
            db.session.remove()

    @staticmethod
    def create_exchange(data):
        try:
            new_exchange = Exchange(**data)
            db.session.add(new_exchange)
            db.session.commit()
            return {'status': 'success', 'data': new_exchange.to_dict()}
        except Exception as e:
            logger.error(f"Failed to create exchange: {str(e)}")
            return {'status': 'error', 'message': 'Failed to create exchange'}
        finally:
            db.session.remove()

    @staticmethod
    def update_exchange(exchange_id, data):
        try:
            exchange = Exchange.query.get(exchange_id)
            if not exchange:
                return {'status': 'error', 'message': 'Exchange not found'}
            exchange.update_exchange(**data)
            return {'status': 'success', 'data': exchange.to_dict()}
        except Exception as e:
            logger.error(f"Failed to update exchange: {str(e)}")
            return {'status': 'error', 'message': 'Failed to update exchange'}
        finally:
            db.session.remove()

    @staticmethod
    def delete_exchange(exchange_id):
        try:
            exchange = Exchange.query.get(exchange_id)
            if not exchange:
                return {'status': 'error', 'message': 'Exchange not found'}
            exchange.delete()
            return {'status': 'success', 'message': 'Exchange deleted successfully'}
        except Exception as e:
            logger.error(f"Failed to delete exchange: {str(e)}")
            return {'status': 'error', 'message': 'Failed to delete exchange'}
        finally:
            db.session.remove()

class TransactionService:
    @staticmethod
    def get_transactions(account_id):
        try:
            transactions = Transaction.query.filter_by(account_id=account_id).all()
            transaction_list = [transaction.to_dict() for transaction in transactions]
            return {'status': 'success', 'data': transaction_list}
        except Exception as e:
            logger.error(f"Failed to retrieve transactions: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve transactions'}
        finally:
            db.session.remove()

    @staticmethod
    def create_transaction(data):
        try:
            new_transaction = Transaction(**data)
            db.session.add(new_transaction)
            db.session.commit()
            return {'status': 'success', 'data': new_transaction.to_dict()}
        except Exception as e:
            logger.error(f"Failed to create transaction: {str(e)}")
            return {'status': 'error', 'message': 'Failed to create transaction'}
        finally:
            db.session.remove()

    @staticmethod
    def update_transaction(transaction_id, data):
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return {'status': 'error', 'message': 'Transaction not found'}
            transaction.update_transaction(**data)
            return {'status': 'success', 'data': transaction.to_dict()}
        except Exception as e:
            logger.error(f"Failed to update transaction: {str(e)}")
            return {'status': 'error', 'message': 'Failed to update transaction'}
        finally:
            db.session.remove()

    @staticmethod
    def delete_transaction(transaction_id):
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return {'status': 'error', 'message': 'Transaction not found'}
            transaction.delete()
            return {'status': 'success', 'message': 'Transaction deleted successfully'}
        except Exception as e:
            logger.error(f"Failed to delete transaction: {str(e)}")
            return {'status': 'error', 'message': 'Failed to delete transaction'}
        finally:
            db.session.remove()
