from flask_login import current_user, login_user, logout_user
from werkzeug.security import generate_password_hash
from apps import db
from apps.authentication.util import verify_pass
from apps.authentication.models import Role, User, UserProfile

class UserService:
    @staticmethod
    def register_user(user_data):
        if 'username' not in user_data or 'email' not in user_data or 'password' not in user_data:
            return {'status': 'error', 'message': 'Missing required fields.'}

        existing_user = User.query.filter((User.username == user_data['username']) | (User.email == user_data['email'])).first()
        if existing_user:
            return {'status': 'error', 'message': 'User with this username or email already exists.'}

        # Hash password here as before
        new_user = User(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password']
        )

        try:
            new_user.save()
            UserService.initialize_user_profile(new_user.id)
            
            # Assign roles if any are provided
            if 'roles' in user_data and user_data['roles']:
                for role_name in user_data['roles']:
                    UserService.assign_role_to_user(new_user.id, role_name)

            return {'status': 'success', 'message': 'User registered successfully.', 'user': new_user.username}
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'An error occurred: {str(e)}'}
        
    @staticmethod
    def authenticate_user(credentials):
        """
        Authenticates a user's login attempt.
        :param credentials: Dictionary containing the username/email and password.
        :return: Authentication status and user session information.
        """
        username_or_email = credentials.get('username_or_email')
        password = credentials.get('password')

        # Check if user exists
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if user and verify_pass(password, user.password):
            # Assuming the use of Flask-Login for session management
            login_user(user)
            return {'status': 'success', 'message': 'User authenticated successfully.'}
        
        return {'status': 'error', 'message': 'Invalid username/email or password.'}

    @staticmethod
    def initialize_user_profile(user_id):
        """
        Initializes a new profile for the user with default settings.
        :param user_id: ID of the newly registered user.
        """
        # Create a new UserProfile instance with default settings
        new_profile = UserProfile(
            user_id=user_id,
            bio="",  # Example: Leave empty or provide a default bio
            location="",  # Example: Leave empty or set a default location
            profile_picture="",  # Example: URL to a default profile picture or leave empty
            contact_number="",  # Example: Leave empty or set a default contact number
            kyc_status='pending',  # Set KYC status to 'pending' by default
            kyc_submission_date=None,  # No KYC submission date initially
            
        )

        # Save the new profile to the database
        try:
            new_profile.save
        except Exception as e:
            # Handle potential exceptions, such as database errors
            db.session.rollback()
            print(f"Error initializing user profile: {e}")
            # Depending on your application's error handling strategy, you might log this error or handle it differently.

    @staticmethod
    def get_user_profile(user_id):
        """
        Retrieves a user's profile details.
        :param user_id: ID of the user.
        :return: User profile details.
        """
        # Attempt to find the user profile by user_id
        user_profile = UserProfile.find_by_user_id(user_id=user_id)

        if user_profile:
            # Serialize the user profile using to_dict method and return it
            return {'status': 'success', 'data': user_profile.to_dict()}
        
        # Return an error message if the profile is not found
        return {'status': 'error', 'message': 'User profile not found.'}
    
    @staticmethod
    def create_role(role_name):
        """Create a new role."""
        existing_role = Role.query.filter_by(name=role_name).first()
        if existing_role:
            return {'status': 'error', 'message': 'Role already exists.'}

        try:
            new_role = Role(name=role_name)
            db.session.add(new_role)
            db.session.commit()
            return {'status': 'success', 'message': 'Role created successfully.', 'role_id': new_role.id}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create role: {e}'}
        
    @staticmethod
    def assign_role_to_user(user_id, role_name):
        """Assign a role to a user."""
        user = User.query.get(user_id)
        role = Role.query.filter_by(name=role_name).first()

        if not user or not role:
            return {'status': 'error', 'message': 'User or Role not found.'}

        if role in user.roles:
            return {'status': 'error', 'message': 'User already has this role.'}

        user.roles.append(role)
        db.session.commit()
        return {'status': 'success', 'message': f'Role {role_name} assigned to user {user.username} successfully.'}

    @staticmethod
    def list_user_roles(user_id):
        """List all roles of a user."""
        user = User.query.get(user_id)
        if not user:
            return {'status': 'error', 'message': 'User not found.'}

        roles = [role.name for role in user.roles]
        return {'status': 'success', 'roles': roles}
    
    @staticmethod
    def remove_role_from_user(user_id, role_name):
        """Remove a role from a user."""
        user = User.query.get(user_id)
        role = Role.query.filter_by(name=role_name).first()

        if not user or not role:
            return {'status': 'error', 'message': 'User or Role not found.'}

        if role not in user.roles:
            return {'status': 'error', 'message': 'User does not have this role.'}

        user.roles.remove(role)
        db.session.commit()
        return {'status': 'success', 'message': f'Role {role_name} removed from user {user.username} successfully.'}
    
    @staticmethod
    def get_all_roles():
        """
        Retrieves all available roles.
        :return: A list of role names.
        """
        roles = Role.query.all()
        return [role.name for role in roles]