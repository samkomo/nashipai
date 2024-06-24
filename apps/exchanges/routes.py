import json
import logging
from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from apps.exchanges.service import AccountService, ExchangeService, TransactionService
logger = logging.getLogger(__name__)

blueprint = Blueprint('main', __name__)

@blueprint.route('/accounts')
@login_required
def list_accounts():
    user_id = current_user.id
    logger.info(f'retreiving accounts for user ID: {current_user.id}')
    response = AccountService.get_accounts(user_id)
    print(json.dumps(response, indent=2))
    if response['status'] == 'success':
        return render_template('accounts/list.html', data=response['data'])
    else:
        flash(response['message'], 'error')
        logger.error(f"Failed to get accounts: {response['message']}")
        return jsonify({'message': response['message']}), 400

@blueprint.route('/accounts/create', methods=['POST'])
@login_required
def create_account():
    data = request.json
    response = AccountService.create_account(data)
    if response['status'] == 'success':
        return jsonify(response['data']), 201
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/accounts/update/<int:account_id>', methods=['POST'])
@login_required
def update_account(account_id):
    data = request.json
    response = AccountService.update_account(account_id, data)
    if response['status'] == 'success':
        return jsonify(response['data']), 200
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/accounts/delete/<int:account_id>', methods=['DELETE'])
@login_required
def delete_account(account_id):
    response = AccountService.delete_account(account_id)
    if response['status'] == 'success':
        return jsonify({'message': response['message']}), 200
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/exchanges')
@login_required
def list_exchanges():
    response = ExchangeService.get_exchanges()
    if response['status'] == 'success':
        return render_template('exchanges/list.html', data=response['data'])
    else:
        flash(response['message'], 'error')
        return jsonify({'message': response['message']}), 400

@blueprint.route('/exchanges/create', methods=['POST'])
@login_required
def create_exchange():
    data = request.json
    response = ExchangeService.create_exchange(data)
    if response['status'] == 'success':
        return jsonify(response['data']), 201
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/exchanges/update/<int:exchange_id>', methods=['POST'])
@login_required
def update_exchange(exchange_id):
    data = request.json
    response = ExchangeService.update_exchange(exchange_id, data)
    if response['status'] == 'success':
        return jsonify(response['data']), 200
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/exchanges/delete/<int:exchange_id>', methods=['DELETE'])
@login_required
def delete_exchange(exchange_id):
    response = ExchangeService.delete_exchange(exchange_id)
    if response['status'] == 'success':
        return jsonify({'message': response['message']}), 200
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/transactions/<int:account_id>')
@login_required
def list_transactions(account_id):
    response = TransactionService.get_transactions(account_id)
    if response['status'] == 'success':
        return render_template('transactions/list.html', data=response['data'])
    else:
        flash(response['message'], 'error')
        return jsonify({'message': response['message']}), 400

@blueprint.route('/transactions/create', methods=['POST'])
@login_required
def create_transaction():
    data = request.json
    response = TransactionService.create_transaction(data)
    if response['status'] == 'success':
        return jsonify(response['data']), 201
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/transactions/update/<int:transaction_id>', methods=['POST'])
@login_required
def update_transaction(transaction_id):
    data = request.json
    response = TransactionService.update_transaction(transaction_id, data)
    if response['status'] == 'success':
        return jsonify(response['data']), 200
    else:
        return jsonify({'message': response['message']}), 400

@blueprint.route('/transactions/delete/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    response = TransactionService.delete_transaction(transaction_id)
    if response['status'] == 'success':
        return jsonify({'message': response['message']}), 200
    else:
        return jsonify({'message': response['message']}), 400

