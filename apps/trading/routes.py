import os
from ccxt.base.errors import BadRequest, ArgumentsRequired
from flask import make_response, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from apps.trading import blueprint
from flask_login import login_required
from apps.trading.ccxt_client import TradingBot
from apps import db
from apps.trading.models import Order, Strategy  # Import the Order model
from sqlalchemy.exc import SQLAlchemyError  # Ensure this is imported
from ccxt.base.errors import BaseError  # Import base CCXT error class
import pandas as pd
import re
from typing import Tuple, Dict, Any
import logging
from ccxt.base.errors import BaseError, OrderNotFound
import time  # Correct import for the time module
from apps.trading.utillity import encrypt_message, decrypt_message, generate_trade_uid, load_encryption_key, format_value,calculate_profit_and_percentage, generate_key
from cryptography.fernet import InvalidToken

# Configure basic logging for the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# print(f"Encryption key: {generate_key()}")z
logger = logging.getLogger(__name__)
# Instantiate the TradingModule
EXPECTED_PASSPHRASE = os.environ.get('WEBHOOK_PASSPHRASE')
encryption_key = load_encryption_key()
# logger.info(f"Encryption Key: {generate_key()}")

# logging.basicConfig(level=logging.DEBUG)


@blueprint.route('/webhook', methods=['POST'])
async def webhook() -> Tuple[Dict[str, Any], int]:
    if request.method != 'POST':
        return jsonify({"errorCode": "invalid_method", "message": "Method not allowed"}), 405
    
    payload: Dict[str, Any] = request.get_json()
    if not payload or payload.get('passphrase') != EXPECTED_PASSPHRASE:
        return jsonify({"errorCode": "unauthorized", "message": "Unauthorized access"}), 401
    
    required_fields = ['exchange', 'symbol', 'price', 'type', 'side', 'size', 'pos_size', 'market_pos', 'strategy_uid']
    for field in required_fields:
        if field not in payload:
            return jsonify({"errorCode": "missing_field", "message": f"Missing field: {field}"}), 400
        
    if not payload['api_key'] or not payload['api_secret']:
        return jsonify({"error": "Encrypted API key and Secret key are required"}), 400  
    
    try:    
        decrypted_api_key = decrypt_message(payload['api_key'], encryption_key)
        decrypted_secret_key = decrypt_message(payload['api_secret'], encryption_key)
    

        # Instantiate and process the trade with the trading bot
        trading_bot = TradingBot(payload['exchange'], decrypted_api_key, decrypted_secret_key)
        await trading_bot.initialize_exchange()  # Ensure the exchange is initialized
        result = await trading_bot.create_order(payload)  # Now safely proceed with trade processing

        # If trade execution fails, return an error response
        if not result["success"]:
            return jsonify({"status": "error", "message": result.get("error", "Trade execution failed")}), 500
            
        # result = {"success": True, "message": "Test Mode"}



        # Extract relevant, consistent information
        strategy = payload["strategy_uid"]
        symbol = payload["symbol"]
        size = str(payload["size"])
        
        # Use these fields to form a base string for the UID
        base_string = f"{strategy}-{symbol}-{size}"

        uid = generate_trade_uid(base_string)
    
    
        if payload['market_pos'] in ['long', 'short']:  # Attempt to open trade
            new_order = Order(
                uid=uid,
                exchange_id=payload['exchange'],
                symbol=payload['symbol'],
                entry_price=payload['price'],
                type=payload['type'],
                side=payload['side'],
                size=payload['size'],
                strategy_uid=payload['strategy_uid'],
                market_pos=payload['market_pos'],
                pos_size=payload['pos_size'],
                status='Error' if not result["success"] else 'Open',
                order_id=result.get("order", {}).get("id", None),
            )
            db.session.add(new_order)
        elif payload['market_pos'] == 'flat':  # Attempt to close trade
            order_to_close = Order.query.filter_by(uid=uid, status='Open').first()
            if order_to_close:
                if result["success"]:
                    order_to_close.exit_price = payload['price']
                    order_to_close.exit_time = db.func.now()  # Set exit_time to the current time
                    order_to_close.status = 'Closed'
                    order_to_close.pos_size = payload['pos_size']
                    # Calculate profit and percentage profit
                    profit, percentage_profit = calculate_profit_and_percentage(order_to_close.entry_price, order_to_close.exit_price, order_to_close.size, order_to_close.side)
                    order_to_close.profit = profit
                    order_to_close.percentage_profit = percentage_profit
                else:
                    # If trade execution failed, mark the order as Error without closing
                    order_to_close.status = 'Error'
        else:
            return jsonify({"errorCode": "invalid_market_pos", "message": "Invalid market position"}), 400
        
        db.session.commit()
        if result["success"]:
            return jsonify({"status": "success", "order": result.get("order", {}), "uid": uid, "profit": profit if 'profit' in locals() else None, "percentage_profit": percentage_profit if 'percentage_profit' in locals() else None}), 200
        else:
            return jsonify({"status": "error", "message": result.get("error", "Trade execution failed"), "uid": uid}), 500
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"An error occurred during decryption: {e}")
        return jsonify({"errorCode": "database_error", "message": str(e)}), 500
    except InvalidToken as e:
        # Handling the exception and providing a user-friendly message
        logger.error(f"An error occurred during decryption: {e}")

        return jsonify({"error": "Decryption failed. Invalid token or key."}), 400

@blueprint.route('/get-order/<order_id>', methods=['GET'])
async def get_order_route(order_id):
    api_key = request.headers.get('X-API-KEY')
    api_secret = request.headers.get('X-API-SECRET')
    symbol = request.headers.get('Symbol')  # Fetching from headers
    exchange_id = request.headers.get('Exchange')  # Fetching from headers

    if not all([api_key, api_secret, exchange_id, symbol]):
        return jsonify({'error': 'Missing API key, secret, exchange ID, or symbol'}), 401

    trading_bot = TradingBot(exchange_id, api_key, api_secret)
    await trading_bot.initialize_exchange()

    try:
        exchange_order_info = await trading_bot.get_order(order_id, symbol)
        
        # Check if the order was actually found on the exchange
        if not exchange_order_info or 'status' not in exchange_order_info:
            return jsonify({'error': 'Order not found on the exchange'}), 404

        # Retrieve the order from the database
        order = Order.query.filter_by(order_id=order_id).first()
        if order:
            # Update the order in your database based on the exchange order info
            order.status = exchange_order_info.get('status')
            # Optionally update other fields as necessary
            db.session.commit()
            return jsonify({'message': 'Order updated successfully', 'order': exchange_order_info})
        else:
            return jsonify({'error': 'Order not found in the database', 'order': exchange_order_info}), 404

    except OrderNotFound:
        return jsonify({'error': 'Order not found on the exchange'}), 404
    except BaseError as e:
        return jsonify({'error': str(e)}), 500
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'errorCode': 'database_error', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'errorCode': 'generic_error', 'message': str(e)}), 500
    

# @blueprint.route('/fetch-orders', methods=['GET'])
# async def fetch_orders_route():
#     api_key = request.headers.get('X-API-KEY')
#     api_secret = request.headers.get('X-API-SECRET')
#     exchange_id = request.args.get('exchange', default=None)
#     symbol = request.args.get('symbol', default=None)
#     since = request.args.get('since', default=None, type=int)
#     limit = request.args.get('limit', default=None, type=int)

#     if not api_key or not api_secret:
#         return jsonify({'error': 'API key or secret not provided'}), 401

#     trading_bot = TradingBot(exchange_id, api_key, api_secret)  # Replace 'exchange_id' with actual ID
#     await trading_bot.initialize_exchange()  # Make sure to initialize the exchange connection

#     # Convert `since` to milliseconds if necessary (depending on your implementation)
#     orders = await trading_bot.fetch_orders(symbol, since, limit)
#     return jsonify(orders)

@blueprint.route('/fetch-orders', methods=['GET'])
async def fetch_orders_route():
    # Retrieve parameters from request headers
    api_key = request.headers.get('X-API-KEY')
    api_secret = request.headers.get('X-API-SECRET')
    symbol = request.headers.get('Symbol')  # Now fetching from headers
    since = request.headers.get('Since', default=None, type=int)
    limit = request.headers.get('Limit', default=None, type=int)
    exchange_id = request.headers.get('Exchange')  # Now fetching from headers

    if not api_key or not api_secret or not exchange_id:
        return jsonify({'error': 'API key, secret, or exchange ID not provided'}), 401

    trading_bot = TradingBot(exchange_id, api_key, api_secret)
    await trading_bot.initialize_exchange()  # Make sure the bot is initialized

    try:
        # Convert since and limit to integers if they're not None
        since = int(since) if since is not None else None
        limit = int(limit) if limit is not None else None

        orders = await trading_bot.fetch_orders(symbol, since, limit)
        return jsonify(orders)
    except BaseError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'errorCode': 'generic_error', 'message': str(e)}), 500
    

# @blueprint.route('/orders', methods=['GET'])
# def get_orders():
#     exchange_id = request.args.get('exchange', 'phemex')
#     symbol = request.args.get('symbol', 'BTC/USDT')
#     orders = trading_module.get_orders(exchange_id, symbol)
#     return jsonify(orders)

# @blueprint.route('/my_trades', methods=['GET'])
# def get_my_trades():
#     exchange_id = request.args.get('exchange', 'phemex')
#     symbol = request.args.get('symbol', 'BTC/USDT')
#     orders = trading_module.get_orders(exchange_id, symbol)
#     return jsonify(orders)

@blueprint.route('/trades', methods=['GET'])
def get_trades():
    orders = Order.query.order_by(Order.entry_time.desc()).all()
    orders_list = [order.to_dict() for order in orders]
    logger.info(f"Successfully fetched open orders for {orders}.")

    return render_template('trading/trades.html', trades=orders_list)  # Pass 'trades' variable to the template context


# Assuming Strategy is your SQLAlchemy model
@blueprint.route('/strategies', methods=['GET'])
def get_strategies():
    try:
        # Fetch all trading data from the database
        trades = Strategy.query.all()
        # Convert the SQLAlchemy objects to dictionaries
        trades_list = [trade.to_dict() for trade in trades]
        # Render the template with the trading data
        return render_template('trading/strategies.html', trades=trades_list)
    except Exception as e:
        logger.error('Error fetching strategies: %s', str(e))
        return jsonify({'error': 'Error fetching strategies'}), 500


@blueprint.route('/strategies_list', methods=['GET'])
def list_strategies():
    try:
        # Query all trades from the database
        trades = Strategy.query.all()
        # Transform the SQLAlchemy objects into dictionaries
        trades_data = [trade.to_dict() for trade in trades]
        # Return the data as a JSON response
        return jsonify(trades_data), 200
    except Exception as e:
        # Log the exception and return an error response
        logger.error('Error retrieving trades: %s', str(e))
        return jsonify({'error': 'Error retrieving trades'}), 500
    

# @blueprint.route('strategy-detail')
# def trading_strategy():
#     return render_template('trading/strategy-detail.html')
    
@blueprint.route('/strategy-details/<int:strategy_uid>')
def strategy_details(strategy_uid):
    # Fetch the strategy by ID or return 404 if not found
    strategy = Strategy.query.get_or_404(strategy_uid)
    
    # Access the orders directly through the relationship
    orders = strategy.orders

    # Sort orders by date_time in ascending order using sorted() for cumulative calculations
    sorted_orders = sorted(orders, key=lambda order: order.entry_time)

    cumulative_profit = 0
    cumulative_percentage_profit = 0
    orders_list = []

    for order in sorted_orders:
        cumulative_profit += order.profit
        cumulative_percentage_profit += order.percentage_profit

        # Convert order to dict and add cumulative values
        order_dict = order.to_dict()
        order_dict['cumulative_profit'] = round(cumulative_profit, 2)
        order_dict['cumulative_percentage_profit'] = round(cumulative_percentage_profit, 2)

        orders_list.append(order_dict)

    # Correcting the preparation of chart data
    order_dates = [order.entry_time.strftime('%Y-%m-%d') for order in sorted_orders]  # Use dot notation
    profits = [order.profit for order in sorted_orders]

    # Corrected access for cumulative_profits using dictionary key access
    cumulative_profits = [order['cumulative_profit'] for order in orders_list]  # Corrected access

    # Reverse the list for table display to show newest orders at the top
    table_orders_list = list(reversed(orders_list))

    # Convert the strategy to a dictionary for rendering
    strategy_data = strategy.to_dict()

    # Pass both the strategy and its orders to the template, using table_orders_list for the table
    return render_template('trading/strategy-details.html', 
                            data=strategy_data, 
                            orders=table_orders_list,  # Use reversed list for table display
                            order_dates=order_dates,  # Use original sorted list for chart
                            profits=profits,
                            cumulative_profits=cumulative_profits)






@blueprint.route('/upload-settings', methods=['POST'])
def upload_settings():
    if 'file' not in request.files:
        logger.debug('No file part in the request')
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        logger.debug('No selected file')
        return jsonify({'error': 'No selected file'}), 400

    logger.debug('File received: %s', file.filename)

    

      # Extract coin_pair, time_frame, and strategy name from the file name
    match = re.search(r"^(?P<coin_pair>\w+)\.P_(?P<time_frame>\d+[hmd]) (?P<strategy>.+?) (?=\[.*\]|-)", file.filename)

    if match:
        coin_pair = match.group('coin_pair')
        time_frame = match.group('time_frame').replace('m', 'min')  # Convert '15m' to '15min'
        strategy_name = match.group('strategy') + " Strategy by SMK"  # Append "by SMK" to the strategy name
        # Use these fields to form a base string for the UID
        base_string = f"{coin_pair}_{time_frame}_{strategy_name}_{int(time.time())}"

        uid = generate_trade_uid(base_string)
        
        logger.debug(f"Coin pair: {coin_pair}, Timeframe: {time_frame}, Strategy: {strategy_name}, Strategy UID: {uid}")
    else:
        logger.error("Failed to extract metadata from filename.")
        return jsonify({'error': 'Failed to extract metadata from filename'}), 400

    try:
        # Read the CSV file
        df = pd.read_csv(file)
        logger.debug('CSV file loaded successfully')

        # Filter out columns starting with "__"
        filtered_df = df.loc[:, ~df.columns.str.startswith('__')]

        # Convert the first row to a dictionary
        first_row_data = filtered_df.iloc[0].to_dict()

        # Normalize the keys to match the model attributes
        normalized_data = {normalize_key(k): v for k, v in first_row_data.items()}

        # Add the extracted metadata to the normalized data
        normalized_data['uid'] = uid
        normalized_data['coin_pair'] = coin_pair
        normalized_data['time_frame'] = time_frame
        normalized_data['strategy_name'] = strategy_name

        # Create a new Strategy object using the normalized data
        trading_data = Strategy(**normalized_data)
        db.session.add(trading_data)
        db.session.commit()

        # Save the new object to the database
        db.session.add(trading_data)
        db.session.commit()

        logger.debug("Strategy created==============================: %s", trading_data.id)

        return jsonify(first_row_data), 200
    except Exception as e:
        logger.error('Error processing the file: %s', str(e))
        return jsonify({'error': 'Error processing the file'}), 500


def normalize_key(key):
    # Replace problematic characters and convert to lowercase
    return key.replace(' ', '_').replace(':', '').replace('#', 'num').replace('%', 'percent').replace('-', '').replace('&', 'and').replace('_/_', '_').lower()


# def format_value(key, value):
#     if 'percent' in key:
#         return f"{value}%"
#     elif 'return' in key or key.startswith('avg_') or key.startswith('largest_') or 'profit' in key or 'loss' in key or 'drawdown' in key:
#         return f"${value}"
#     return value

@blueprint.context_processor
def utility_processor():
    return dict(format_value=format_value)



@blueprint.route('/encrypt', methods=['POST'])
def encrypt():
    data = request.json
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')
    
    if not api_key or not api_secret:
        return jsonify({"error": "API key and Secret key are required"}), 400

    encrypted_api_key = encrypt_message(api_key, encryption_key)
    encrypted_secret_key = encrypt_message(api_secret, encryption_key)

    return jsonify({
        "status": "success",
        "encrypted_api_key": encrypted_api_key,
        "encrypted_secret_key": encrypted_secret_key
    })

@blueprint.route('/decrypt', methods=['POST'])
def decrypt():
    data = request.json
    encrypted_api_key = data.get('encrypted_api_key')
    encrypted_secret_key = data.get('encrypted_secret_key')
    
    if not encrypted_api_key or not encrypted_secret_key:
        return jsonify({"error": "Encrypted API key and Secret key are required"}), 400

    try:
        decrypted_api_key = decrypt_message(encrypted_api_key, encryption_key)
        decrypted_secret_key = decrypt_message(encrypted_secret_key, encryption_key)
    except InvalidToken:
        # Handling the exception and providing a user-friendly message
        return jsonify({"error": "Decryption failed. Invalid token or key."}), 400


    return jsonify({
        "status": "success",
        "api_key": decrypted_api_key,
        "secret_key": decrypted_secret_key
    })

# def format_value(key, value):
#     if value in [None, 'N/A']:
#         return 'N/A'
#     if 'percent' in key:
#         # Check if the value is already a string that includes '%'
#         # If it is, return as is, to avoid adding an extra '%' character
#         return f"{value}" if isinstance(value, str) and '%' in value else f"{value:.2f}%"
#     if any(x in key for x in ['profit', 'loss', 'return', 'trade']):
#         # Check if the value is already a string that includes '$'
#         # If it is, return as is, to avoid adding an extra '$' character
#         return f"{value}" if isinstance(value, str) and '$' in value else f"${value:,.2f}"
#     return value



# @blueprint.route('/upload-equity-curve', methods=['POST'])
# def upload_equity_curve():
#     file = request.files.get('equity_curve')
#     if file:
#         filename = secure_filename(file.filename)
#         file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         # Return the path to the uploaded image
#         return jsonify({'filePath': file_path})
#     return jsonify({'error': 'No file uploaded'}), 400

# # Serve uploaded files
# @blueprint.route('/static/uploads/<filename>')
# def uploaded_file(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    # if 'file' not in request.files:
    #     return jsonify({'error': 'No file part'}), 400
    # file = request.files['file']
    # if file.filename == '':
    #     return jsonify({'error': 'No selected file'}), 400
    # if file:
    #     # Process the file here (e.g., update settings, save to database)
    #     # For demonstration, we're just returning a success message
    #     return jsonify({'message': 'File successfully uploaded and processed'}), 200


# @blueprint.route('/order', methods=['GET'])
# def get_order_by_id():
#     exchange_id = request.args.get('exchange', 'phemex')
#     order_id = request.args.get('order_id')
#     order = trading_module.get_order_by_id(exchange_id, order_id)
#     return jsonify(order)

# @blueprint.route('/delete_all_orders', methods=['POST'])
# def delete_all_orders():
#     Order.query.delete()
#     db.session.commit()
#     return jsonify({'message': 'All orders deleted successfully'})


# @blueprint.route('/delete_order', methods=['POST'])
# def delete_order():
#     try:
#         order_id = request.form.get('id')
#         order = Order.query.get(order_id)
#         if order:
#             db.session.delete(order)
#             db.session.commit()
#             return jsonify({'message': f'Order {order_id} deleted successfully'})
#         else:
#             return jsonify({'error': f'Order with ID {order_id} not found'}), 404
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500