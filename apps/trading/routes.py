import json
from flask import make_response, render_template, request, jsonify
from apps.trading import blueprint
from flask_login import login_required
from apps.trading.ccxt_client import TradingModule
from apps import db
from apps.trading.models import Order  # Import the Order model

# Instantiate the TradingModule
trading_module = TradingModule()


@blueprint.route('/trades0')
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
        subaccount = payload.get('strategy')
        
        trading_module.setup_exchanges(subaccount=subaccount)
        
        # If the symbol ends with ".P", trim it out
        if payload['symbol'].endswith('.P'):
            payload['symbol'] = payload['symbol'].replace('.P', '')

        print(json.dumps(payload, indent=2))

        order = trading_module.create_order(exchange_id, payload)

        # Save the order to the database
        
        new_order = Order(
            exchange_id=exchange_id,
            symbol=payload['symbol'],
            order_id=order['id'],
            price=payload['price'],
            type=payload['type'],  # Include 'type' here
            side=payload['side'],
            size=payload['size'],
            pos_size=payload['pos_size'],
            market_pos=payload['market_pos'],
            strategy=subaccount,
            status=order['status']
        )
        db.session.add(new_order)
        db.session.commit()

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


# routes.py

@blueprint.route('/trades', methods=['GET'])
def show_orders_table():
    orders = Order.query.order_by(Order.time.desc()).all()
    orders_list = [order.to_dict() for order in orders]
    
    # Create the response
    response = make_response(render_template('trading/trades.html', trades=orders_list))
    # Order.delete_all_orders()

    # Set cache control headers to prevent caching
    response.cache_control.no_cache = True
    response.cache_control.must_revalidate = True
    response.cache_control.max_age = 0

    return response


@blueprint.route('/order', methods=['GET'])
def get_order_by_id():
    exchange_id = request.args.get('exchange', 'bybit')
    order_id = request.args.get('order_id')

    order = trading_module.get_order_by_id(exchange_id, order_id)
    return jsonify(order)


@blueprint.route('/delete_all_orders', methods=['POST'])
def delete_all_orders():
    # Your code to delete all orders from the database
    Order.query.delete()
    db.session.commit()
    return jsonify({'message': 'All orders deleted successfully'})


# routes.py

# ... Existing code ...

# @blueprint.route('/orders', methods=['GET'])
# def get_orders():
#     exchange_id = request.args.get('exchange', 'bybit')
#     symbol = request.args.get('symbol', 'BTC/USDT')

#     orders = trading_module.get_orders(exchange_id, symbol)

#     # Query the saved orders from the database
#     saved_orders = Order.query.all()

#     return render_template('trading/orders.html', orders=orders, saved_orders=saved_orders)
