import streamlit as st
from utils import authenticate_user, logout

# Set page configuration
st.set_page_config(
    menu_items={
        'About': "AGPH",
        'Get Help': None,
        'Report a bug': None,   
    },
    layout="wide",  # Set layout to wide mode
    initial_sidebar_state="expanded",  
    page_title="AGPH Books",
)

try:
    conn = st.connection('mysql', type='sql')
    st.toast("Database Connected!")
except Exception as e:
    st.error(f"Error connecting to MySQL: {e}")
    st.stop()

def main():
    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.user:
        st.title("BookTrackr - Login")  # Only show title when login form is visible
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
        
        if submit:
            user = authenticate_user(username, password, conn)
            if user:
                st.session_state.user = user
                st.success(f"Welcome, {user['username']}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    else:
        st.sidebar.subheader(f"Logged in as {st.session_state.user['username']}")
        role = st.session_state.user['role']

        if st.sidebar.button("Logout"):
            logout()

        # Define navigation based on role
        pages = {
            "Admin Dashboard": [st.Page("admin.py", title="Admin Dashboard")],
            "User Dashboard": [st.Page("user.py", title="User Dashboard")]
        }

        pg = st.navigation(pages["Admin Dashboard"] if role == "admin" else pages["User Dashboard"])
        pg.run()

if __name__ == "__main__":
    main()