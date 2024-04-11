# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import logging
from flask import jsonify, render_template, redirect, request, url_for, flash, session
from flask_login import (
    current_user,
    login_user,
    logout_user
)

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import User


# Additional imports
from flask_login import login_required, current_user
from apps.authentication.forms import UpdateProfileForm, ChangePasswordForm
from apps.authentication.service import UserService
from apps.authentication.util import verify_pass
# Assume these services are implemented in your service layer
logger = logging.getLogger(__name__)

@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login'))


# Login & Registration

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if request.method == 'POST' and login_form.validate_on_submit():
        # Collect form data
        credentials = {
            'username_or_email': request.form['username'],
            'password': request.form['password']
        }

        # Authenticate user through the UserService
        response = UserService.authenticate_user(credentials)
        
        if response['status'] == 'success':
            # Redirect to the default route after successful login
            return redirect(url_for('home_blueprint.index'))
        else:
            # Display error message if authentication failed
            flash(response['message'], 'error')
            return render_template('accounts/login.html', form=login_form, msg=response['message'])
    else:
        # Display the login form
        if not current_user.is_authenticated:
            return render_template('accounts/login.html', form=login_form)
        return redirect(url_for('strategies_blueprint.list_strategies'))

@blueprint.route('/roles', methods=['GET'])
def list_roles():
    roles = UserService.get_all_roles()
    return jsonify(roles)

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    roles = UserService.get_all_roles()  # Fetch roles to display in the form
    
    if request.method == 'POST' and 'register' in request.form:
        user_data = {
            'username': request.form['username'],
            'email': request.form['email'],
            'password': request.form['password'],
            'roles': request.form.getlist('roles')  # Collect selected roles from the form
        }

        response = UserService.register_user(user_data)
        
        if response['status'] == 'success':
            return redirect(url_for('authentication_blueprint.login', success='User created successfully. Please login.'))
        else:
            return render_template('accounts/register.html', msg=response['message'], success=False, form=create_account_form, roles=roles)
    else:
        return render_template('accounts/register.html', form=create_account_form, roles=roles)

@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Initialize the form
    update_profile_form = UpdateProfileForm(request.form)

    if request.method == 'POST' and update_profile_form.validate_on_submit():
        # Extract form data
        profile_data = {
            'bio': request.form.get('bio'),
            'location': request.form.get('location'),
            'profile_picture': request.form.get('profile_picture'),
            'contact_number': request.form.get('contact_number')
        }

        # Call a method to update the user's profile (method to be implemented in UserService)
        result = UserService.update_user_profile(current_user.id, profile_data)
        
        if result['status'] == 'success':
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'error')
        return redirect(url_for('accounts.profile'))

    else:
        # On GET request, fetch the user's current profile details to prefill the form
        profile_result = UserService.get_user_profile(current_user.id)
        if profile_result['status'] == 'success':
            update_profile_form.process(data=profile_result['data'])
        else:
            flash(profile_result['message'], 'error')
    
    return render_template('accounts/profile.html', form=update_profile_form)

@blueprint.route('/roles', methods=['POST'])
def create_role():
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'status': 'error', 'message': 'Role name is required.'}), 400

    result = UserService.create_role(data['name'])
    
    if result['status'] == 'success':
        return jsonify({'status': 'success', 'message': 'Role created successfully.', 'role_id': result['role_id']}), 201
    else:
        return jsonify({'status': 'error', 'message': result['message']}), 400
    
    
# @blueprint.route('/change-password', methods=['GET', 'POST'])
# @login_required
# def change_password():
#     change_password_form = ChangePasswordForm(request.form)
#     if request.method == 'POST' and change_password_form.validate_on_submit():
#         old_password = request.form.get('old_password')
#         new_password = request.form.get('new_password')
#         if change_user_password(current_user.id, old_password, new_password):
#             flash('Password changed successfully.', 'success')
#             return redirect(url_for('authentication_blueprint.profile'))
#         else:
#             flash('Failed to change password. Please check your old password.', 'error')
#     return render_template('accounts/change_password.html', form=change_password_form)

# @blueprint.route('/deactivate-account', methods=['POST'])
# @login_required
# def deactivate_account():
#     if deactivate_user_account(current_user.id):
#         flash('Account deactivated successfully. We are sad to see you go.', 'success')
#         logout_user()
#         return redirect(url_for('authentication_blueprint.login'))
#     else:
#         flash('Failed to deactivate account.', 'error')
#         return redirect(url_for('authentication_blueprint.profile'))


@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('authentication_blueprint.login'))


# Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500
