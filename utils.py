import streamlit as st

def authenticate_user(username, password, conn):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}';"
    user = conn.query(query, ttl=0).to_dict(orient='records')
    return user[0] if user else None

def logout():
    st.session_state.user = None
    st.rerun()