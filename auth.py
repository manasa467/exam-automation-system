import streamlit as st
import database as db


def _restore_session_from_token():
    """Restore login state from a secure opaque session token stored in the URL."""
    if 'user' not in st.session_state:
        token = st.query_params.get('t')
        if token:
            row = db.get_session(token)
            if row:
                st.session_state['user'] = {'id': row[0], 'name': row[1]}
                st.session_state['session_token'] = token
            else:
                # Token invalid / expired — clear it
                st.query_params.clear()


def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 AI Exam Automation System")
        st.markdown("---")

        login_tab, register_tab = st.tabs(["Login", "Register"])

        # ── Login ──────────────────────────────────────────────
        with login_tab:
            with st.form("login_form"):
                name = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True)

                if submit:
                    if not name or not password:
                        st.error("Please enter both username and password.")
                    else:
                        teacher = db.verify_login(name, password)
                        if teacher:
                            token = db.create_session(teacher[0])
                            st.session_state['user'] = {'id': teacher[0], 'name': teacher[1]}
                            st.session_state['session_token'] = token
                            # Store opaque token in URL — NOT the username
                            st.query_params['t'] = token
                            st.success(f"Welcome, {teacher[1]}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")

        # ── Register ───────────────────────────────────────────
        with register_tab:
            with st.form("register_form"):
                new_name = st.text_input("Choose a Username")
                new_pw = st.text_input("Choose a Password", type="password")
                confirm_pw = st.text_input("Confirm Password", type="password")
                register_btn = st.form_submit_button("Create Account", use_container_width=True)

                if register_btn:
                    if not new_name or not new_pw or not confirm_pw:
                        st.error("Please fill in all fields.")
                    elif new_name.lower() == "manasa":
                        st.error("That username is reserved.")
                    elif new_pw != confirm_pw:
                        st.error("Passwords do not match.")
                    elif len(new_pw) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        try:
                            teacher = db.register_teacher(new_name, new_pw)
                            st.success(f"Account created for '{teacher[1]}'! You can now log in.")
                        except ValueError as ve:
                            st.error(str(ve))


def logout():
    token = st.session_state.get('session_token')
    db.delete_session(token)
    st.session_state.pop('user', None)
    st.session_state.pop('session_token', None)
    st.query_params.clear()
    st.rerun()


def check_authentication():
    _restore_session_from_token()

    if 'user' not in st.session_state:
        login()
        return False
    return True
