import logging
import os
from flask import request, jsonify, redirect, url_for, flash, render_template
from flask_login import current_user, login_required
from apps.trading.service import TradingService
from apps.trading import blueprint
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)
EXPECTED_PASSPHRASE = os.environ.get('WEBHOOK_PASSPHRASE')


@blueprint.route('/list_bots')
@login_required
def list_bots():
    user_id = current_user.id
    response = TradingService.list_bots(user_id)
    
    if response['status'] == 'success':
        return render_template('trading/bots.html', bots=response['data'])
    else:
        logger.error(f"Failed to list trading bots for user {user_id}: {response['message']}")
        flash(response['message'], 'error')
        return jsonify({'message': response['message']}), 400


@blueprint.route('/create_bot', methods=['POST'])
@login_required
def create_bot():
    # Collect form data
    user_id = current_user.id  # Using Flask-Login to get the current user's ID
    strategy_id = request.form.get('strategy_id')
    exchange_account_id = request.form.get('exchange_account_id')
    bot_name = request.form.get('bot_name')

    # Check if all required form data is provided
    if not (strategy_id and exchange_account_id and bot_name):
        flash('All fields are required to create a bot.', 'error')
        return redirect(url_for(request.url))  # Adjust with your actual route

    # Call the service method to create a bot
    result = TradingService.create_bot(user_id, strategy_id, exchange_account_id, bot_name)

    # Handle response from the service layer
    if result['status'] == 'success':
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')

    # Redirect to the bot list page or wherever appropriate
    return redirect(url_for('trading_blueprint.list_bots'))  # Adjust with your actual route for listing bots


@blueprint.route('/view_bot/<int:bot_id>')
@login_required
def view_bot(bot_id):
    try:
        response = TradingService.get_bot(bot_id)
        if response['status'] == 'success':
            logger.info(f"{response['status']}: {response['message']}")
            return render_template('trading/bot-details.html', bot=response['message'])
        else:
            flash(response['message'], 'warning')
            logger.error(f"{response['status']}: {response['message']}")
            return redirect(url_for('trading_blueprint.list_bots'))
    except Exception as e:
        flash(f'Error fetching bot details: {str(e)}', 'error')
        logger.error(f"Exception: {str(e)}")
        return redirect(url_for('trading_blueprint.list_bots'))


@blueprint.route('/webhook', methods=['POST'])
async def webhook() -> Tuple[Dict[str, Any], int]:
    if request.method != 'POST':
        return jsonify({"errorCode": "invalid_method", "message": "Method not allowed"}), 405

    payload: Dict[str, Any] = request.get_json()
    if not payload:
        return jsonify({"errorCode": "bad_request", "message": "No payload provided"}), 400

    if payload.get('passphrase') != EXPECTED_PASSPHRASE:
        return jsonify({"errorCode": "unauthorized", "message": "Unauthorized access"}), 401

    required_fields = ['exchange', 'symbol', 'order_price', 'order_size', 'order_side', 'pos_size', 'pos_type', 'bot_id','type']
    if any(field not in payload for field in required_fields):
        return jsonify({"errorCode": "missing_field", "message": "Missing required field(s)"}), 400

    try:
        logger.info(f"Moving to TradingService")
        response = await TradingService.process_order(payload)
        if response['status'] == 'success':
            logger.info(f"{response['status']}: {response['message']}")
            return render_template('trading/bot-details.html', bot=response['message'])
        else:
            flash(response['message'], 'warning')
            logger.error(f"{response['status']}: {response['message']}")
            return redirect(url_for('trading_blueprint.list_bots'))
    except Exception as e:
        flash(f'Error fetching bot details: {str(e)}', 'error')
        logger.error(f"Exception: {str(e)}")
        return redirect(url_for('trading_blueprint.list_bots'))


@blueprint.route('/activate_bot/<int:bot_id>', methods=['POST'])
def activate_bot(bot_id):
    TradingService.activate_bot(bot_id)
    flash('Trading bot activated successfully!', 'success')
    return redirect(url_for('dashboard.show_bots'))

@blueprint.route('/deactivate_bot/<int:bot_id>', methods=['POST'])
def deactivate_bot(bot_id):
    TradingService.deactivate_bot(bot_id)
    flash('Trading bot deactivated successfully!', 'info')
    return redirect(url_for('dashboard.show_bots'))

@blueprint.route('/update_bot/<int:bot_id>', methods=['POST'])
def update_bot(bot_id):
    settings = request.form.to_dict()
    TradingService.update_bot_settings(bot_id, **settings)
    flash('Trading bot updated successfully!', 'success')
    return redirect(url_for('dashboard.show_bots'))

@blueprint.route('/delete_bot/<int:bot_id>', methods=['POST'])
def delete_bot(bot_id):
    TradingService.delete_bot(bot_id)
    flash('Trading bot deleted successfully!', 'warning')
    return redirect(url_for('dashboard.show_bots'))

@blueprint.route('/place_order', methods=['POST'])
def place_order():
    bot_id = request.form.get('bot_id')
    symbol = request.form.get('symbol')
    order_type = request.form.get('order_type')
    side = request.form.get('side')
    quantity = request.form.get('quantity')
    entry_price = request.form.get('entry_price', None)
    result = TradingService.place_order(bot_id, symbol, order_type, side, quantity, entry_price)
    flash('Order placed successfully!', 'success')
    return redirect(url_for('dashboard.show_orders'))

@blueprint.route('/execute_order/<int:order_id>', methods=['POST'])
def execute_order(order_id):
    execution_price = request.form.get('execution_price')
    TradingService.execute_order(order_id, execution_price)
    flash('Order executed successfully!', 'success')
    return redirect(url_for('dashboard.show_orders'))

@blueprint.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    TradingService.cancel_order(order_id)
    flash('Order cancelled successfully!', 'info')
    return redirect(url_for('dashboard.show_orders'))

@blueprint.route('/open_position/<int:order_id>', methods=['POST'])
def open_position(order_id):
    TradingService.open_position(order_id)
    flash('Position opened successfully!', 'success')
    return redirect(url_for('dashboard.show_positions'))

@blueprint.route('/close_position/<int:position_id>', methods=['POST'])
def close_position(position_id):
    closing_price = request.form.get('closing_price')
    TradingService.close_position(position_id, closing_price)
    flash('Position closed successfully!', 'success')
    return redirect(url_for('dashboard.show_positions'))

@blueprint.route('/generate_alert', methods=['POST'])
def generate_alert():
    bot_id = request.form.get('bot_id')
    message = request.form.get('message')
    alert_type = request.form.get('alert_type')
    severity = request.form.get('severity', 'info')
    TradingService.generate_alert(bot_id, message, alert_type, severity)
    flash('Alert generated successfully!', 'success')
    return redirect(url_for('dashboard.show_alerts'))

@blueprint.route('/dismiss_alert/<int:alert_id>', methods=['POST'])
def dismiss_alert(alert_id):
    TradingService.dismiss_alert(alert_id)
    flash('Alert dismissed successfully!', 'info')
    return redirect(url_for('dashboard.show_alerts'))

@blueprint.route('/view_alert/<int:alert_id>', methods=['GET'])
def view_alert(alert_id):
    TradingService.view_alert(alert_id)
    flash('Alert viewed successfully!', 'info')
    return redirect(url_for('dashboard.show_alerts'))

