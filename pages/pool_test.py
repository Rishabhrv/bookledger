import streamlit as st
import pandas as pd

# 1. Simple Password Protection
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        with st.form("login_form"):
            password = st.text_input("Enter Admin Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                if password == "7869799272": # Change this!
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
        return False
    return True

if check_password():
    st.title("🗄️ Database Connection Monitor")
    
    # List of your connection keys from secrets.toml
    db_keys = ["mysql", "ijisem", "ebook", "attendance", "ict", "ag"]
    
    db_stats = []

    for key in db_keys:
        try:
            # Connect using Streamlit's native connection handler
            conn = st.connection(key, type="sql")
            engine = conn.engine
            pool = engine.pool
            
            # Calculate Utilization
            total_capacity = pool.size() + pool._max_overflow
            active = pool.checkedout()
            utilization = (active / total_capacity) * 100 if total_capacity > 0 else 0
            
            # Gather pool data
            db_stats.append({
                "Database": key,
                "Status": "✅ Connected",
                "Pool Size": pool.size(),
                "Max Overflow": pool._max_overflow,
                "Recycle (sec)": pool._recycle,
                "Pre-Ping": getattr(pool, "pre_ping", False),
                "Checked Out": active,
                "Checked In": pool.checkedin(),
                "Utilization": utilization
            })
        except Exception as e:
            db_stats.append({
                "Database": key, 
                "Status": f"❌ Error: {str(e)[:30]}...",
                "Pool Size": 0, "Max Overflow": 0, "Recycle (sec)": "N/A", 
                "Pre-Ping": "N/A", "Checked Out": 0, "Checked In": "N/A",
                "Utilization": 0
            })

    # Display as a Table
    df = pd.DataFrame(db_stats)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detailed Cards
    st.divider()
    cols = st.columns(3)
    for i, stat in enumerate(db_stats):
        with cols[i % 3]:
            with st.container(border=True):
                # Header and Metric
                st.metric(label=f"DB: {stat['Database']}", 
                          value=f"{stat['Checked Out']} Active", 
                          delta=f"{stat['Utilization']:.1f}% Utilization",
                          delta_color="inverse" if stat['Utilization'] > 80 else "normal")
                
                # Visual Utilization Bar
                st.progress(stat['Utilization'] / 100)
                
                # Capacity Details
                st.caption(f"Capacity: {stat['Pool Size']} (Base) + {stat['Max Overflow']} (Overflow)")
                
                # Technical Details in Expandable section to keep it clean
                with st.expander("View Details"):
                    st.write(f"**Recycle:** {stat['Recycle (sec)']}s")
                    st.write(f"**Pre-Ping:** {stat['Pre-Ping']}")
                    st.write(f"**Idle:** {stat['Checked In']}")

    if st.button("Log Out"):
        st.session_state.authenticated = False
        st.rerun()