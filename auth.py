import streamlit as st
import database as db


def _restore_session_from_params():
    """Restore login state from URL query params on browser refresh."""
    if 'user' not in st.session_state:
        username = st.query_params.get('u')
        if username:
            teacher = db.get_or_create_teacher(username)
            st.session_state['user'] = {'id': teacher[0], 'name': teacher[1]}


def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Teacher Login")

        with st.form("login_form"):
            name = st.text_input("Enter your name please")
            password = st.text_input("Enter your password", type="password")
            submit = st.form_submit_button("Login")

            if submit and name and password:
                if name == password:
                    teacher = db.get_or_create_teacher(name)
                    st.session_state['user'] = {'id': teacher[0], 'name': teacher[1]}
                    # Persist login across refreshes via URL param
                    st.query_params['u'] = name
                    st.success(f"Welcome, {name}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Password must match username.")


def logout():
    if 'user' in st.session_state:
        del st.session_state['user']
    # Clear the URL param so refresh doesn't auto-login
    st.query_params.clear()
    st.rerun()


def check_authentication():
    # Try to restore session from URL param on refresh
    _restore_session_from_params()

    if 'user' not in st.session_state:
        login()
        return False
    return True
