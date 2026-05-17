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

    is_admin = user['name'].lower() == 'manasa'

    with st.sidebar:
        st.title("AI Based Exam Automation System")
        st.write(f"Welcome, **{user['name']}**")
        if st.button("Logout"):
            auth.logout()

    st.markdown("### 🏫 Teacher Dashboard")

    if is_admin:
        tabs = st.tabs([
            "Manage Subjects",
            "IA Question Paper Generator",
            "SEE Question Paper Generator",
            "Scheme of Evaluation",
            "👑 Admin Panel"
        ])
        tab1, tab2, tab3, tab4, tab5 = tabs
    else:
        tabs = st.tabs([
            "Manage Subjects",
            "IA Question Paper Generator",
            "SEE Question Paper Generator",
            "Scheme of Evaluation"
        ])
        tab1, tab2, tab3, tab4 = tabs
        tab5 = None

    with tab1:
        subjects.render()
    with tab2:
        qp_generator.render(pattern=1)
    with tab3:
        qp_generator.render(pattern=2)
    with tab4:
        scheme_generator.render()
        
    if tab5 is not None:
        with tab5:
            st.subheader("Admin Panel - All Users' Data")
            all_subjects = db.get_all_subjects_for_admin()
            
            if all_subjects:
                # Build a table display using a dataframe or columns
                for subj in all_subjects:
                    sub_id = subj[0]
                    sub_name = subj[2]
                    sub_code = subj[3]
                    sem = subj[4]
                    teacher = subj[5]
                    
                    with st.expander(f"{sub_name} ({sub_code}) - Teacher: {teacher}", expanded=False):
                        st.write(f"**Semester:** {sem}")
                        st.write(f"**Subject ID:** {sub_id}")
                        if st.button(f"Delete Subject (ID: {sub_id})", key=f"admin_del_sub_{sub_id}", type="primary"):
                            db.delete_subject(sub_id)
                            st.success("Subject and all its data deleted!")
                            st.rerun()
            else:
                st.info("No subjects found across any user.")

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