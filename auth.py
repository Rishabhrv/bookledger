import streamlit as st
import jwt
import requests
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logger = logging.getLogger(__name__)

# Custom filter to exclude watchdog logs
class NoWatchdogFilter(logging.Filter):
    def filter(self, record):
        return not record.name.startswith('watchdog')

# Configure logging
logger = logging.getLogger('streamlit_app')
logger.setLevel(logging.DEBUG)

# Remove any existing handlers to avoid duplicate logs
logger.handlers = []

# Create a rotating file handler (max 1MB, keep 3 backups)
handler = RotatingFileHandler('streamlit.log', maxBytes=1_000_000, backupCount=3)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.addFilter(NoWatchdogFilter())
logger.addHandler(handler)

# Flask endpoints
FLASK_VALIDATE_URL = "https://crmserver.agvolumes.com/validate_token"
FLASK_USER_DETAILS_URL = "https://crmserver.agvolumes.com/user_details"
FLASK_LOGIN_URL = "https://crmserver.agvolumes.com/login"
FLASK_LOGOUT_URL = "https://crmserver.agvolumes.com/logout"

#Secrets and constants
JWT_SECRET = st.secrets["general"]["JWT_SECRET"]
VALID_ROLES = {"admin", "user"}
VALID_APPS = {"main", "operations"}


# # Configuration
# FLASK_VALIDATE_URL = "http://localhost:5001/validate_token"
# FLASK_USER_DETAILS_URL = "http://localhost:5001/user_details"
# FLASK_LOGIN_URL = "http://localhost:5001/login"
# FLASK_LOGOUT_URL = "http://localhost:5001/logout"

ACCESS_TO_BUTTON = {
    # Loop buttons (table)
    "ISBN": "manage_isbn_dialog",
    "Payment": "manage_price_dialog",
    "Authors": "edit_author_dialog",
    "Operations": "edit_operation_dialog",
    "Printing & Delivery": "edit_inventory_delivery_dialog",
    "DatadashBoard": "datadashoard",
    "Advance Search": "advance_search",
    # Non-loop buttons
    "Add Book": "add_book_dialog",
    "Authors Edit": "edit_author_detail"
}


def validate_token():
    # Check if token exists in session state
    if 'token' not in st.session_state:
        # Try to get token from query params (for initial login redirect)
        token = st.query_params.get("token")
        if not token:
            logger.error("No token provided")
            st.error("Access denied: Please log in first")
            st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
            st.stop()
        st.session_state.token = token if isinstance(token, str) else token[0]

    token = st.session_state.token

    try:
        # Local validation
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        if 'user_id' not in decoded or 'exp' not in decoded:
            raise jwt.InvalidTokenError("Missing user_id or exp")

        # Server-side token validation
        response = requests.post(FLASK_VALIDATE_URL, json={"token": token}, timeout=10)
        if response.status_code != 200 or not response.json().get('valid'):
            error = response.json().get('error', 'Invalid token')
            logger.error(f"Token validation failed: {error}")
            raise jwt.InvalidTokenError(error)

        # Fetch user details
        details_response = requests.post(FLASK_USER_DETAILS_URL, json={"token": token}, timeout=10)
        if details_response.status_code != 200 or not details_response.json().get('valid'):
            error = details_response.json().get('error', 'Unable to fetch user details')
            logger.error(f"User details fetch failed: {error}")
            raise jwt.InvalidTokenError(f"User details error: {error}")

        user_details = details_response.json()
        role = user_details['role'].lower()
        app = user_details['app'].lower()
        access = user_details['access']
        email = user_details['email']
        start_date = user_details['start_date']
        username = user_details['username']

        if role not in VALID_ROLES:
            logger.error(f"Invalid role: {role}")
            raise jwt.InvalidTokenError(f"Invalid role '{role}'")
        
        # Skip app and access validation for admins
        if role != 'admin':
            if app not in VALID_APPS:
                logger.error(f"Invalid app: {app}")
                raise jwt.InvalidTokenError(f"Invalid app '{app}'")
            
            # Validate access based on app
            if app == 'main':
                valid_access = set(ACCESS_TO_BUTTON.keys())  # Define or import ACCESS_TO_BUTTON
                if not all(acc in valid_access for acc in access):
                    logger.error(f"Invalid access for main app: {access}")
                    raise jwt.InvalidTokenError(f"Invalid access for main app: {access}")
            elif app == 'operations':
                valid_access = {"writer", "proofreader", "formatter", "cover_designer"}
                if not (len(access) == 1 and access[0] in valid_access):
                    logger.error(f"Invalid access for operations app: {access}")
                    raise jwt.InvalidTokenError(f"Invalid access for operations app: {access}")

        st.session_state.user_id = decoded['user_id']
        st.session_state.email = email
        st.session_state.role = role
        st.session_state.app = app
        st.session_state.access = access
        st.session_state.start_date = start_date
        st.session_state.username = username
        st.session_state.exp = decoded['exp']
        logger.info(f"Token validated successfully for user: {email}")

    except jwt.ExpiredSignatureError as e:
        logger.error(f"Token expired: {str(e)}", exc_info=True)
        st.error("Access denied: Token expired. Please log in again.")
        st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
        clear_auth_session()
        st.stop()
    except jwt.InvalidSignatureError as e:
        logger.error(f"Invalid token signature: {str(e)}", exc_info=True)
        st.error("Access denied: Invalid token signature. Please log in again.")
        st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
        clear_auth_session()
        st.stop()
    except jwt.DecodeError as e:
        logger.error(f"Token decoding failed: {str(e)}", exc_info=True)
        st.error("Access denied: Token decoding failed. Please log in again.")
        st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
        clear_auth_session()
        st.stop()
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}", exc_info=True)
        st.error(f"Access denied: {str(e)}. Please log in again.")
        st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
        clear_auth_session()
        st.stop()
    except requests.RequestException as e:
        logger.error(f"Request to Flask failed: {str(e)}", exc_info=True)
        st.error(f"Access denied: Unable to contact authentication server. Error: {str(e)}")
        st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
        clear_auth_session()
        st.stop()
    except Exception as e:
        logger.error(f"Unexpected error in validate_token: {str(e)}", exc_info=True)
        st.error(f"Access denied: An unexpected error occurred. Error: {str(e)}")
        st.markdown(f"[Go to Login]({FLASK_LOGIN_URL})")
        clear_auth_session()
        st.stop()

def clear_auth_session():
    keys_to_clear = ['token', 'user_id', 'email', 'role', 'app', 'access', 'start_date', 'username', 'exp']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.query_params.clear()
    logger.info("Session and query params cleared")