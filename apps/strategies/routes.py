import json
import os
from flask import Blueprint, flash, request, jsonify, redirect, url_for, render_template
from flask_login import login_required, current_user
from apps.strategies.form import CreateStrategyForm, UpdateStrategyForm
from apps.strategies.service import StrategyService # Adjust import paths as needed
from apps.strategies.models import Strategy  # Adjust import path as needed
from apps.strategies import blueprint
import logging
from apps import db
from werkzeug.utils import secure_filename
from apps.strategies.util import process_csv

from apps.trading.routes import allowed_file
from apps.trading.utillity import generate_trade_uid

logger = logging.getLogger(__name__)

# Define the base directory of your Flask app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use a relative path for the upload folder within your project directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'strategies')

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@blueprint.route('/create', methods=['POST'])
@login_required
def create_strategy():
    if not current_user.has_role('Developer'):
        logger.info('You must be a developer to create strategies.')
        flash('You must be a developer to create strategies.', 'error')
        return redirect(url_for('strategies_blueprint.list_strategies'))  # Redirect to a different page as appropriate

    # Extracting form data
    strategy_name = request.form.get('strategy_name')
    description = request.form.get('description')
    settings_file = request.files['settings_file']

    # Validate file presence
    if settings_file and allowed_file(settings_file.filename):
        filename = secure_filename(settings_file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        settings_file.save(filepath)
        
        # Process CSV to extract strategy details and metrics
        coin_pair, time_frame, strategy_name2, strategy_metrics, strategy_settings = process_csv(filepath, filename)

        # Convert strategy_metrics dictionary to JSON string
        # Log the JSON string
        logging.info(f'Strategy Metrics: {json.dumps(strategy_metrics)}')
        logging.info(f'Strategy Metrics: {json.dumps(strategy_settings)}')
        
        # Construct strategy data dictionary
        strategy_data = {
            'strategy_name': strategy_name or strategy_name2,  # Fallback to filename if no name provided
            'developer_id': current_user.id,
            'description': description,
            'coin_pair': coin_pair,
            'time_frame': time_frame,
            'settings_file_path': filepath,
            'status': 'active'
        }

        # Delegate to StrategyService to create strategy and related metadata
        result = StrategyService.create_strategy(strategy_data, strategy_metrics, strategy_settings)
        
        if result['status'] == 'success':
            logger.info('Strategy created successfully')
            flash('Strategy created successfully.', 'success')
        else:
            logger.error(f'Strategy creation failed {result["message"]}')
            flash(result['message'], 'error')
    else:
        flash('Invalid file format or no file uploaded.', 'error')
    
    return redirect(url_for('strategies_blueprint.list_strategies'))


@blueprint.route('/update/<int:strategy_id>', methods=['POST'])
@login_required
def update_strategy(strategy_id):
    form = UpdateStrategyForm(request.form)

    if form.validate_on_submit():
        strategy_data = {
            # Extract strategy fields from form
            'strategy_name': form.strategy_name.data,
            'description': form.description.data,
            'coin_pair': form.coin_pair.data,
            'time_frame': form.time_frame.data,
            # Add other fields as necessary
        }

        # Optional: Verify current_user is authorized to update this strategy
        strategy = Strategy.query.get(strategy_id)
        if not strategy or strategy.developer_id != current_user.id:
            flash('Unauthorized to update this strategy.', 'error')
            return redirect(url_for('strategies.view', strategy_id=strategy_id))

        result = StrategyService.update_strategy(strategy_id, strategy_data)
        
        if result['status'] == 'success':
            flash('Strategy updated successfully.', 'success')
            return redirect(url_for('strategies.view', strategy_id=strategy_id))
        else:
            flash(result['message'], 'error')

    # In case of form validation failure or GET request
    return redirect(url_for('strategies.edit_form', strategy_id=strategy_id))

@blueprint.route('/upload-settings/<int:strategy_id>', methods=['POST'])
@login_required
def upload_strategy_settings(strategy_id):
    if 'settings_file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    
    file = request.files['settings_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)
    
    if file:  # Assuming validation of file type, name, etc.
        file_path = f'/path/to/uploaded/{file.filename}'  # Adjust path handling as necessary
        file.save(file_path)
        result = StrategyService.upload_strategy_settings(strategy_id, file_path)
        flash(result['message'], 'success' if result['status'] == 'success' else 'error')

    return redirect(url_for('strategies.edit', strategy_id=strategy_id))

@blueprint.route('/list', methods=['GET'])
@login_required
def list_strategies():
    # Example of simple filtering: get filter criteria from query parameters
    filter_criteria = {key: value for key, value in request.args.items()}
    
    strategies_list = StrategyService.list_strategies(filter_criteria=filter_criteria)
    if strategies_list['status'] == 'success':
        # return jsonify(strategies_list['strategies']), 200
        return render_template('strategies/list_strategies.html', strategies=strategies_list['strategies'])
    else:
        return jsonify({'message': strategies_list['message']}), 400

@blueprint.route('/delete-strategy/<int:strategy_id>', methods=['POST'])
@login_required
def delete_strategy(strategy_id):
    # Optional: Check if the current_user is authorized to delete the strategy
    strategy = Strategy.query.get(strategy_id)
    if strategy.developer_id != current_user.id:
        flash('Unauthorized to delete this strategy.', 'error')
        return redirect(url_for('strategies.list_strategies'))

    result = StrategyService.delete_strategy(strategy_id)
    
    flash(result['message'], 'success' if result['status'] == 'success' else 'error')
    return redirect(url_for('strategies.list_strategies'))

@blueprint.route('/details/<int:strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    result = StrategyService.get_strategy(strategy_id)
    if result['status'] == 'success':
        # For API endpoints, you might return JSON
        # return jsonify(result['data']), 200

        # For web applications, render a template with the strategy details
        return render_template('strategies/detail.html', strategy=result['data'])
    else:
        # For API endpoints
        # return jsonify({'message': result['message']}), 404

        # For web applications, show an error page or redirect with an error message
        flash(result['message'], 'error')
        return redirect(url_for('strategies.index'))
    
@blueprint.route('/subscribe/<int:strategy_id>', methods=['POST'])
@login_required
def subscribe(strategy_id):
    result = StrategyService.subscribe_to_strategy(user_id=current_user.id, strategy_id=strategy_id)
    
    if result['status'] == 'success':
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('strategies.view_strategy', strategy_id=strategy_id))

@blueprint.route('/unsubscribe/<int:strategy_id>', methods=['POST'])
@login_required
def unsubscribe(strategy_id):
    result = StrategyService.unsubscribe_from_strategy(user_id=current_user.id, strategy_id=strategy_id)
    
    flash(result['message'], 'success' if result['status'] == 'success' else 'error')
    return redirect(url_for('strategies.list_strategies'))

@blueprint.route('/subscriptions', methods=['GET'])
@login_required
def list_subscriptions():
    result = StrategyService.list_user_subscriptions(current_user.id)
    
    if result['status'] == 'success':
        return jsonify(result), 200
    else:
        return jsonify({'message': result['message']}), 404
    
@blueprint.route('/upload-performance/<int:strategy_id>', methods=['POST'])
@login_required
def upload_performance(strategy_id):
    if 'performance_file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    
    file = request.files['performance_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('/path/to/upload/directory', filename)
        file.save(file_path)
        
        result = StrategyService.record_strategy_performance(strategy_id, file_path)
        
        flash(result['message'], 'success' if result['status'] == 'success' else 'error')
        return redirect(url_for('strategies.view_strategy', strategy_id=strategy_id))    

@blueprint.route('/strategy-performance/<int:strategy_id>', methods=['GET'])
def get_performance(strategy_id):
    result = StrategyService.get_strategy_performance(strategy_id)
    
    if result['status'] == 'success':
        return jsonify(result['metrics']), 200
    else:
        return jsonify({'message': result['message']}), 404

# ============OLD==========

# @blueprint.route('/strategies', methods=['POST'])
# @login_required
# def add_strategy():
#     data = request.form
#     result = create_strategy(
#         uid=data.get('uid'),
#         # developer_id=current_user.id,
#         strategy_name=data.get('strategy_name'),
#         description=data.get('description'),
#         coin_pair=data.get('coin_pair'),
#         time_frame=data.get('time_frame'),
#         settings_file_path=data.get('settings_file_path')
#     )
#     if result:
#         logger.info("Strategy created successfully.")
#     else:
#         logger.error("Failed to create strategy.")
#     return redirect(url_for('strategies.list_strategies'))

# @blueprint.route('/strategies/<int:strategy_id>', methods=['GET'])
# def get_strategy(strategy_id):
#     strategy = Strategy.query.get_or_404(strategy_id)
#     return render_template('strategies/detail.html', strategy=strategy)

# # @blueprint.route('/strategies', methods=['GET'])
# # def list_strategies():
# #     strategies = Strategy.query.all()
# #     return render_template('strategies/list.html', strategies=strategies)

# @blueprint.route('/strategies/<int:strategy_id>', methods=['PUT'])
# @login_required
# def update_strategy_route(strategy_id):
#     data = request.form
#     result = update_strategy(strategy_id, **data)
#     if result:
#         logger.info("Strategy updated successfully.")
#     else:
#         logger.info("Failed to update strategy.")
#     return redirect(url_for('strategies.get_strategy', strategy_id=strategy_id))











# @blueprint.route('/strategies/<int:strategy_id>', methods=['DELETE'])
# @login_required
# def delete_strategy(strategy_id):
#     Strategy.query.filter_by(id=strategy_id).delete()
#     db.session.commit()
#     logger.info("Strategy deleted successfully.")
#     return redirect(url_for('strategies.list_strategies'))

# @blueprint.route('/strategies/<int:strategy_id>/subscribe', methods=['POST'])
# @login_required
# def subscribe(strategy_id):
#     duration_days = request.form.get('duration_days', type=int)
#     result = subscribe_to_strategy(strategy_id, current_user.id, duration_days)
#     if result:
#         logger.info("Successfully subscribed to strategy.")
#     else:
#         logger.info("Failed to subscribe to strategy.")
#     return redirect(url_for('strategies.get_strategy', strategy_id=strategy_id))

# @blueprint.route('/strategies/<int:strategy_id>/review', methods=['POST'])
# @login_required
# def add_review(strategy_id):
#     rating = request.form.get('rating', type=int)
#     comment = request.form.get('comment')
#     result = review_strategy(strategy_id, current_user.id, rating, comment)
#     if result:
#         logger.info("Review added successfully.")
#     else:
#         logger.info("Failed to add review.")
#     return redirect(url_for('strategies.get_strategy', strategy_id=strategy_id))
