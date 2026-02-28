import streamlit as st
import jwt
import requests
import logging
from logging.handlers import RotatingFileHandler
import time
from constants import ACCESS_TO_BUTTON


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


# Secrets and constants
JWT_SECRET = st.secrets["general"]["JWT_SECRET"]
VALID_ROLES = {"admin", "user"}
VALID_APPS = {
    "Main": "main",
    "Operations": "operations",
    "IJISEM": "ijisem",
    "Tasks": "tasks",
    "Sales": "sales"
} 

# Configuration
FLASK_AUTH_URL = st.secrets["general"]["FLASK_AUTH_URL"]
FLASK_LOGIN_URL = st.secrets["general"]["FLASK_LOGIN_URL"]
FLASK_LOGOUT_URL = st.secrets["general"]["FLASK_LOGOUT_URL"]

def clear_auth_session():
    # Clear all session state related to authentication
    for key in ['token', 'user_id', 'email', 'role', 'app', 'access', 'start_date', 'username', 'exp', 
                'user_details', 'level', 'report_to', 'associate_id', 'designation']:
        if key in st.session_state:
            del st.session_state[key]


@st.dialog("Authentication Failed", dismissible=False)
def error_dialog(error_message):
    st.error(error_message)
    if st.link_button("Login:material/open_in_new:", url=FLASK_LOGIN_URL, type="tertiary"):
        clear_auth_session()
        st.stop()

def validate_token():
    # Check if token and user details are cached and not near expiry
    current_time = time.time()
    if ('token' in st.session_state and
        'session_id' in st.session_state and  # ✅ Added session_id check
        'exp' in st.session_state and
        st.session_state.exp > current_time + 300):  # 5-minute buffer
        logger.info("Using cached token validation")
        return  # Exit early if cache is valid

    # Token fetching
    if 'token' not in st.session_state:
        token = st.query_params.get("token")
        if not token:
            logger.error("No token provided")
            error_dialog("Access denied: Please log in first.")
            return
        st.session_state.token = token if isinstance(token, str) else token[0]

    token = st.session_state.token

    try:
        # Local JWT validation
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        if 'user_id' not in decoded or 'exp' not in decoded:
            raise jwt.InvalidTokenError("Missing user_id or exp")

        # Server-side validation and user details
        response = requests.post(FLASK_AUTH_URL, json={"token": token}, timeout=3)
        if response.status_code != 200 or not response.json().get('valid'):
            error = response.json().get('error', 'Invalid token')
            logger.error(f"Auth failed: {error}")
            raise jwt.InvalidTokenError(error)

        # ✅ Extract session_id and details from response
        resp_json = response.json()
        session_id = resp_json.get('session_id')
        user_details = resp_json.get('user_details', {})

        role = user_details.get('role', '').lower()
        app = user_details.get('app', '').lower()
        access = user_details.get('access', [])
        email = user_details.get('email', '')
        start_date = user_details.get('start_date', '')
        username = user_details.get('username', '')
        level = user_details.get('level', None)
        report_to = user_details.get('report_to', None)
        associate_id = user_details.get('associate_id', None)
        designation = user_details.get('designation', None)

        # Convert access to list if it's a string or None
        if isinstance(access, str):
            access = [access] if access else []
        elif access is None:
            access = []

        # Role and access validation
        if role not in VALID_ROLES:
            logger.error(f"Invalid role: {role}")
            raise jwt.InvalidTokenError(f"Invalid role '{role}'")
        if role != 'admin':
            if app not in VALID_APPS.values():
                logger.error(f"Invalid app: {app}")
                raise jwt.InvalidTokenError(f"Invalid app '{app}'")
            if app == 'main':
                valid_access = set(ACCESS_TO_BUTTON.keys())
                if not all(acc in valid_access for acc in access):
                    logger.error(f"Invalid access for main app: {access}")
                    raise jwt.InvalidTokenError(f"Invalid access for main app: {access}")
            elif app == 'operations':
                valid_access = {"writer", "proofreader", "formatter", "cover_designer"}
                if not (len(access) == 1 and access[0] in valid_access):
                    logger.error(f"Invalid access for operations app: {access}")
                    raise jwt.InvalidTokenError(f"Invalid access for operations app: {access}")
            elif app == 'ijisem':
                valid_access = {"Full Access"}
                if not (len(access) == 1 and access[0] in valid_access):
                    logger.error(f"Invalid access for ijisem app: {access}")
                    raise jwt.InvalidTokenError(f"Invalid access for ijisem app: {access}")

        # ✅ Cache user details and the NEW session_id
        st.session_state.user_id = decoded['user_id']
        st.session_state.session_id = session_id  # ✅ NEW: Store session_id for logging
        st.session_state.email = email
        st.session_state.role = role
        st.session_state.app = app
        st.session_state.access = access
        st.session_state.start_date = start_date
        st.session_state.username = username
        st.session_state.exp = decoded['exp']
        st.session_state.level = level
        st.session_state.report_to = report_to
        st.session_state.associate_id = associate_id
        st.session_state.designation = designation

        logger.info(f"Token validated successfully for user: {email}, session: {session_id}")

    except jwt.ExpiredSignatureError as e:
        logger.error(f"Token expired: {str(e)}", exc_info=True)
        error_dialog("Access denied: Token expired. Please log in again.")
    except jwt.InvalidSignatureError as e:
        logger.error(f"Invalid token signature: {str(e)}", exc_info=True)
        error_dialog("Access denied: Invalid token signature. Please log in again.")
    except jwt.DecodeError as e:
        logger.error(f"Token decoding failed: {str(e)}", exc_info=True)
        error_dialog("Access denied: Token decoding failed. Please log in again.")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}", exc_info=True)
        error_dialog(f"Access denied: {str(e)}. Please log in again.")
    except requests.RequestException as e:
        logger.error(f"Request to Flask failed: {str(e)}", exc_info=True)
        error_dialog(f"Access denied: Unable to contact authentication server.")
    except Exception as e:
        logger.error(f"Unexpected error in validate_token: {str(e)}", exc_info=True)
        error_dialog(f"Unexpected error in validate_token: {str(e)}")