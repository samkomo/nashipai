from ccxt.base.errors import BadRequest, ArgumentsRequired
from flask import make_response, render_template, request, jsonify
from apps.trading import blueprint
from flask_login import login_required
from apps.trading.ccxt_client import TradingModule
from apps import db
from apps.trading.models import Order  # Import the Order model

# Instantiate the TradingModule
trading_module = TradingModule()

@blueprint.route('/trades0')
def get_trades():
    exchange_id = request.args.get('exchange', 'phemex')
    symbol = request.args.get('symbol', 'BTC/USDT')
    trades = trading_module.get_trades(exchange_id, symbol)
    return jsonify(trades)

@blueprint.route('/webhook', methods=['GET', 'POST'])
def create_order():
    if request.method == 'POST':
        try:
            payload = request.get_json()
            exchange_id = payload['exchange'].lower()
            subaccount = payload.get('subaccount')
            sandbox_mode = payload.get('sandbox_mode')

            trading_module.setup_exchanges(subaccount=subaccount,sandbox_mode=sandbox_mode)

            if payload['symbol'].endswith('.P'):
                payload['symbol'] = payload['symbol'].replace('.P', '')

            order = trading_module.create_order(exchange_id, payload)

            new_order = Order(
                exchange_id=exchange_id,
                symbol=payload['symbol'],
                order_id=None if "id" not in order else order['id'],
                price=payload['price'],
                type=payload['type'],
                side=payload['side'],
                size=payload['size'],
                pos_size=payload['pos_size'],
                market_pos=payload['order_id'],
                strategy=payload['strategy'],
                status=order['status']
            )
            db.session.add(new_order)
            db.session.commit()

            return jsonify(order)
        except ArgumentsRequired as e:
            error_msg = str(e)
            print("Error creating order:", error_msg)
            return jsonify({"errorCode": "arguments_required", "message": error_msg}), 400
        except Exception as e:
            error_msg = str(e)
            print("Error creating order:", error_msg)
            return jsonify({"errorCode": "generic_error", "message": error_msg}), 500

@blueprint.route('/orders', methods=['GET'])
def get_orders():
    exchange_id = request.args.get('exchange', 'phemex')
    symbol = request.args.get('symbol', 'BTC/USDT')
    orders = trading_module.get_orders(exchange_id, symbol)
    return jsonify(orders)

@blueprint.route('/my_trades', methods=['GET'])
def get_my_trades():
    exchange_id = request.args.get('exchange', 'phemex')
    symbol = request.args.get('symbol', 'BTC/USDT')
    orders = trading_module.get_orders(exchange_id, symbol)
    return jsonify(orders)

@blueprint.route('/trades', methods=['GET'])
def show_orders_table():
    orders = Order.query.order_by(Order.time.desc()).all()
    orders_list = [order.to_dict() for order in orders]
    return render_template('trading/trades.html', trades=orders_list)  # Pass 'trades' variable to the template context


@blueprint.route('/order', methods=['GET'])
def get_order_by_id():
    exchange_id = request.args.get('exchange', 'phemex')
    order_id = request.args.get('order_id')
    order = trading_module.get_order_by_id(exchange_id, order_id)
    return jsonify(order)

@blueprint.route('/delete_all_orders', methods=['POST'])
def delete_all_orders():
    Order.query.delete()
    db.session.commit()
    return jsonify({'message': 'All orders deleted successfully'})


@blueprint.route('/delete_order', methods=['POST'])
def delete_order():
    try:
        order_id = request.form.get('id')
        order = Order.query.get(order_id)
        if order:
            db.session.delete(order)
            db.session.commit()
            return jsonify({'message': f'Order {order_id} deleted successfully'})
        else:
            return jsonify({'error': f'Order with ID {order_id} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500