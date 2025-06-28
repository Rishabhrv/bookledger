
import streamlit as st
import pandas as pd
from sqlalchemy import text


def connect_db():
    try:
        # Use st.cache_resource to only connect once
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# Connect to MySQL
conn = connect_db()



def display_activity_log(conn):
    try:
        with conn.session as s:
            logs = s.execute(
                text("SELECT * FROM activity_log ORDER BY timestamp DESC")
            ).mappings().all()

            if logs:
                log_data = [{
                    "Timestamp": log["timestamp"],
                    "User ID": log["user_id"],
                    "Username": log["username"],
                    "Action": log["action"],
                    "Details": log["details"]
                } for log in logs]

                st.dataframe(pd.DataFrame(log_data), use_container_width=True)
            else:
                st.info("No activities logged yet.")
    except Exception as e:
        st.error(f"Error fetching activity log: {e}")



display_activity_log(conn)