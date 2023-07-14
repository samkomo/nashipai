import json
from flask import render_template, request, jsonify
from apps.trading import blueprint
from flask_login import login_required
from apps.trading.ccxt_client import TradingModule


# Instantiate the TradingModule
trading_module = TradingModule()


@blueprint.route('/trades')
# @login_required
def get_trades():
    exchange_id = request.args.get('exchange', 'bybit')
    symbol = request.args.get('symbol', 'BTC/USDT')
    trades = trading_module.get_trades(exchange_id, symbol)
    return jsonify(trades)
    # return render_template('trading/trades.html', trades=trades)

@blueprint.route('/webhook', methods=['GET', 'POST'])
# @login_required
def create_order():
    if request.method == 'POST':
        payload = request.get_json()
        exchange_id = payload['exchange'].lower()
        # If the symbol ends with ".P", trim it out
        if payload['symbol'].endswith('.P'):
            payload['symbol'] = payload['symbol'].replace('.P', '')

        print(json.dumps(payload, indent=2))

        order = trading_module.create_order(exchange_id, payload)

        return jsonify(order)
    else:
        # Handle GET request
        # Add your GET request logic here if needed
        pass


@blueprint.route('/orders', methods=['GET'])
def get_orders():
    exchange_id = request.args.get('exchange', 'bybit')
    symbol = request.args.get('symbol', 'BTC/USDT')

    orders = trading_module.get_orders(exchange_id, symbol)
    return jsonify(orders)

@blueprint.route('/my_trades', methods=['GET'])
def get_my_trades():
    exchange_id = request.args.get('exchange', 'bybit')
    symbol = request.args.get('symbol', 'BTC/USDT')

    orders = trading_module.get_orders(exchange_id, symbol)
    return jsonify(orders)


