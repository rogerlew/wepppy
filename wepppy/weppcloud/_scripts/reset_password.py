import os
import sys
import getpass

# Add the project's root directory to the Python path.
# This ensures that we can import the application modules.
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from wepppy.weppcloud.app import app, db, User  # Import the Flask app, database, and User model
from flask_security.utils import hash_password, config_value # Import the password hashing utility

def reset_user_password(email, new_password):
    """
    Finds a user by email and resets their password.
    
    Args:
        email (str): The email address of the user to update.
        new_password (str): The new password to set for the user.
    """
    with app.app_context():
        # Diagnostic print to confirm which hashing algorithm is being used.
        # This should match your application's 'SECURITY_PASSWORD_HASH' setting.
        print(f"Using password hash algorithm: {app.config.get('SECURITY_PASSWORD_HASH', 'default (sha512_crypt)')}")
#        print((config_value("PASSWORD_HASH"), config_value("PASSWORD_SALT")))

        # Find the user in the database
        user = User.query.filter_by(email=email).first()

        if user is None:
            print(f"Error: User with email '{email}' not found.", file=sys.stderr)
            sys.exit(1)

        # Hash the new password and update the user object
        user.password = hash_password(new_password)
        
        # Commit the changes to the database
        db.session.add(user)
        db.session.commit()
        
        print(f"Successfully reset password for user '{email}'.")

if __name__ == '__main__':
    # Ensure the script is called with an email address argument
    if len(sys.argv) != 2:
        print("Usage: python reset_password.py <email>", file=sys.stderr)
        sys.exit(1)
        
    user_email = sys.argv[1]

    # Securely prompt for the new password without showing it on the screen
    print(f"Resetting password for {user_email}")
    try:
        password = getpass.getpass("Enter new password: ")
        password_confirm = getpass.getpass("Confirm new password: ")
    except Exception as error:
        print('ERROR: ', error, file=sys.stderr)
        sys.exit(1)

    # Check if the entered passwords match
    if password != password_confirm:
        print("Passwords do not match. Aborting.", file=sys.stderr)
        sys.exit(1)
        
    if not password:
        print("Password cannot be empty. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Call the function to perform the password reset
    reset_user_password(user_email, password)

