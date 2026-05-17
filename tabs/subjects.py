import streamlit as st
import database as db
import pandas as pd
import os

def render():
    # st.subheader("Manage Subjects") # Removed redundant header
    
    user_id = st.session_state['user']['id']
    
    # --- Add New Subject Section ---
    with st.expander("Add New Subject", expanded=False):
        with st.form("add_subject_form"):
            col1, col2 = st.columns(2)
            with col1:
                subject_name = st.text_input("Subject Name")
                course_code = st.text_input("Course Code")
            with col2:
                semester = st.selectbox("Semester", [str(i) for i in range(1, 9)])
            
            st.markdown("#### Syllabus (Modules)")
            num_modules = st.number_input("Number of Modules", min_value=1, max_value=5, value=5, step=1)
            
            # We can't dynamically add fields inside a form easily based on another input in the same form without rerun.
            # So we will ask for module details AFTER creating the subject or use a text area for bulk input.
            # Let's use a text area for now for simplicity or just create placeholders.
            # Better approach: Create subject first, then add details.
            
            submitted = st.form_submit_button("Create Subject")
            
            if submitted:
                if subject_name and course_code:
                    if num_modules > 5:
                        st.error("A subject can have a maximum of 5 modules.")
                    else:
                        try:
                            subject_id = db.add_subject(user_id, subject_name, course_code, semester)
                            st.success(f"Subject '{subject_name}' created! Now add syllabus details below.")
                            st.session_state['current_subject_id'] = subject_id
                            st.rerun()
                        except ValueError as ve:
                            st.error(str(ve))
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please fill all required fields.")

    # --- Edit Subject Details Section ---
    subjects = db.get_subjects(user_id)
    if subjects:
        subject_options = {s[2]: s[0] for s in subjects} # Name -> ID
        selected_subject_name = st.selectbox("Select Subject to Edit/View", list(subject_options.keys()))
        selected_subject_id = subject_options[selected_subject_name]
        
        # Tabs for details
        tab_syllabus, tab_co, tab_ref = st.tabs(["Syllabus", "Course Outcomes", "References"])
        
        # 1. Syllabus Tab
        with tab_syllabus:
            st.write(f"**Manage Syllabus for {selected_subject_name}**")
            current_syllabus = db.get_syllabus(selected_subject_id)
            
            # Display existing
            if current_syllabus:
                st.markdown("---")
                for mod in current_syllabus:
                    mod_id, _, mod_num, mod_content = mod
                    
                    with st.expander(f"Module {mod_num}", expanded=False):
                        # Edit Mode
                        new_content = st.text_area("Content", value=mod_content, key=f"mod_content_{mod_id}")
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("Save Changes", key=f"save_mod_{mod_id}"):
                                db.update_syllabus(mod_id, new_content)
                                st.success("Updated!")
                                st.rerun()
                        with col2:
                            if st.button("Delete Module", key=f"del_mod_{mod_id}"):
                                db.delete_syllabus(mod_id)
                                st.success("Deleted!")
                                st.rerun()
            
            # Add new module
            if len(current_syllabus) >= 5:
                st.warning("Maximum of 5 modules allowed per subject. You cannot add more.")
            else:
                with st.form("add_module_form"):
                    mod_num = st.number_input("Module Number", min_value=1, step=1)
                    mod_content = st.text_area("Module Content")
                    add_mod = st.form_submit_button("Add Module")
                    
                    if add_mod and mod_content:
                        # Hard limit check
                        if len(db.get_syllabus(selected_subject_id)) >= 5:
                            st.error("Only 5 modules are allowed per subject.")
                        elif db.check_syllabus_exists(selected_subject_id, mod_num):
                            st.warning(f"Module {mod_num} has already been added. Duplicate modules are not allowed.")
                        else:
                            try:
                                db.add_syllabus(selected_subject_id, mod_num, mod_content)
                                st.success("Module added!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))

        # 2. CO Tab
        with tab_co:
            st.write(f"**Manage COs for {selected_subject_name}**")
            current_cos = db.get_cos(selected_subject_id)
            
            if current_cos:
                st.markdown("---")
                for co in current_cos:
                    co_id, _, co_num, co_desc = co
                    
                    with st.expander(f"{co_num}", expanded=False):
                        new_desc = st.text_area("Description", value=co_desc, key=f"co_desc_{co_id}")
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("💾 Save Changes", key=f"save_co_{co_id}"):
                                db.update_co(co_id, new_desc)
                                st.success("Updated!")
                                st.rerun()
                        with col2:
                            if st.button("Delete CO", key=f"del_co_{co_id}"):
                                db.delete_co(co_id)
                                st.success("Deleted!")
                                st.rerun()
                
            if len(current_cos) >= 5:
                st.warning("Maximum of 5 Course Outcomes allowed per subject. You cannot add more.")
            else:
                with st.form("add_co_form"):
                    co_num = st.text_input("CO Number (e.g., CO1)")
                    co_desc = st.text_area("Description")
                    add_co_btn = st.form_submit_button("Add CO")
                    
                    if add_co_btn and co_num and co_desc:
                        # Hard limit check
                        if len(db.get_cos(selected_subject_id)) >= 5:
                            st.error("Only 5 Course Outcomes are allowed per subject.")
                        elif db.check_co_exists(selected_subject_id, co_num):
                            st.warning(f"CO {co_num} already exists for this subject. Duplicate COs are not allowed.")
                        else:
                            try:
                                db.add_co(selected_subject_id, co_num, co_desc)
                                st.success("CO added!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))

        # 3. References Tab
        with tab_ref:
            st.write(f"**Manage References for {selected_subject_name}**")
            current_refs = db.get_references(selected_subject_id)
            
            if current_refs:
                st.markdown("---")
                for ref in current_refs:
                    ref_id = ref[0]
                    text_content = ref[2]
                    pdf_path = ref[3] if len(ref) > 3 else None
                    
                    with st.expander(f"Reference: {text_content[:50]}...", expanded=False):
                        new_text = st.text_input("Text/Link", value=text_content, key=f"ref_text_{ref_id}")
                        new_pdf = st.file_uploader("Replace PDF (Optional)", type=['pdf'], key=f"ref_pdf_{ref_id}")
                        
                        if pdf_path:
                            st.write(f"Current PDF: {os.path.basename(pdf_path)}")
                            try:
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label="Download Current PDF",
                                        data=f,
                                        file_name=os.path.basename(pdf_path),
                                        mime="application/pdf",
                                        key=f"dl_edit_{ref_id}"
                                    )
                            except FileNotFoundError:
                                st.error("File not found on server.")

                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("Save Changes", key=f"save_ref_{ref_id}"):
                                final_pdf_path = None
                                if new_pdf:
                                    save_dir = "reference_materials"
                                    if not os.path.exists(save_dir):
                                        os.makedirs(save_dir)
                                    file_path = os.path.join(save_dir, f"{selected_subject_id}_{new_pdf.name}")
                                    with open(file_path, "wb") as f:
                                        f.write(new_pdf.getbuffer())
                                    final_pdf_path = file_path
                                
                                db.update_reference(ref_id, new_text, final_pdf_path)
                                st.success("Updated!")
                                st.rerun()
                        
                        with col2:
                            if st.button("🗑Delete Reference", key=f"del_ref_{ref_id}"):
                                # Delete file if exists
                                ref_data = db.get_reference_by_id(ref_id)
                                if ref_data and len(ref_data) > 3 and ref_data[3]:
                                    try:
                                        os.remove(ref_data[3])
                                    except Exception:
                                        pass
                                db.delete_reference(ref_id)
                                st.success("Deleted!")
                                st.rerun()

            if len(current_refs) >= 5:
                st.warning("Maximum of 5 References allowed per subject. You cannot add more.")
            else:
                with st.form("add_ref_form"):
                    ref_text = st.text_input("Reference Material (Text or Link)")
                    ref_file = st.file_uploader("Upload Reference PDF (Optional)", type=['pdf'])
                    add_ref_btn = st.form_submit_button("Add Reference")
                    
                    if add_ref_btn:
                        # Hard limit check
                        if len(db.get_references(selected_subject_id)) >= 5:
                             st.error("Only 5 references are allowed per subject.")
                        elif not ref_text and not ref_file:
                            st.warning("Please provide either text or a PDF file.")
                        else:
                            try:
                                pdf_path = None
                                if ref_file:
                                    save_dir = "reference_materials"
                                    if not os.path.exists(save_dir):
                                        os.makedirs(save_dir)
                                    
                                    # Save file
                                    file_path = os.path.join(save_dir, f"{selected_subject_id}_{ref_file.name}")
                                    with open(file_path, "wb") as f:
                                        f.write(ref_file.getbuffer())
                                    pdf_path = file_path
                                
                                db.add_reference(selected_subject_id, ref_text, pdf_path)
                                st.success("Reference added!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
        
        # Delete Subject
        st.markdown("---")
        if st.button("Delete Subject", type="primary"):
            db.delete_subject(selected_subject_id)
            st.success("Subject deleted.")
            st.rerun()
            
    else:
        st.info("No subjects found. Add one above.")
