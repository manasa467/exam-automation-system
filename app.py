import streamlit as st
import auth
import database as db
from tabs import subjects, qp_generator, scheme_generator

st.set_page_config(
    page_title="AI Based Exam Automation System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

db.init_db()

if auth.check_authentication():
    user = st.session_state['user']

    with st.sidebar:
        st.title("AI Based Exam Automation System")
        st.write(f"Welcome, **{user['name']}**")
        if st.button("Logout"):
            auth.logout()
        

    st.markdown("### 🏫 Teacher Dashboard")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Manage Subjects",
        "IA Question Paper Generator",
        "SEE Question Paper Generator",
        "Scheme of Evaluation"
    ])

    with tab1:
        subjects.render()
    with tab2:
        qp_generator.render(pattern=1)
    with tab3:
        qp_generator.render(pattern=2)
    with tab4:
        scheme_generator.render()

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 75, 75, 0.1) !important;
        border-bottom: 2px solid #ff4b4b;
        color: #ff4b4b !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(150, 150, 150, 0.1);
        color: #ff4b4b;
    }
    .stExpander {
        border-radius: 10px;
        border: 1px solid rgba(150, 150, 150, 0.2);
    }
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)