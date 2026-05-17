import streamlit as st
import database as db
import ai_engine as ai
from reportlab.lib.pagesizes import letter
import os
import re

from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, LongTable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

COLLEGE_LOGO_FIXED_PATH = None
VTU_LOGO_FIXED_PATH = None
KANNADA_HEADER_FIXED_PATH = None


def generate_custom_pdf(paper_type, questions_data, subject_info, cos_list, header_meta):
    """Unified PDF generator for both IA and SEE question papers in BMSIT format"""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=4)

    def load_logo(path, width=0.72 * inch, height=0.72 * inch):
        if path and os.path.exists(path):
            return Image(path, width=width, height=height)
        return Paragraph("", styles["Normal"])

    def resolve_kannada_header_image():
        local_path = os.path.join(os.path.dirname(__file__), "..", "assets", "kannada_header.png")
        local_path = os.path.abspath(local_path)
        if os.path.exists(local_path):
            return local_path
        return None

    # Header
    kannada_header_path = resolve_kannada_header_image()
    english_header = (
        "<font size='13'><b>BMS Institute of Technology and Management</b></font><br/>"
        "<font size='11'>(An Autonomous Institution Affiliated to VTU, Belagavi)</font><br/>"
        "<font size='11'>Avalahalli, Doddaballapur Main Road, Bengaluru - 560064</font>"
    )
    center_rows = []
    if kannada_header_path:
        center_rows.append([Image(kannada_header_path, width=4.9 * inch, height=0.23 * inch)])
    center_rows.append([Paragraph(english_header, ParagraphStyle("HeaderCenter", parent=subtitle_style, alignment=TA_CENTER, leading=12))])
    center_cell = Table(center_rows, colWidths=[5.7 * inch])
    center_cell.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    logos_table = Table(
        [[
            load_logo(header_meta.get("college_logo_path")),
            center_cell,
            load_logo(header_meta.get("vtu_logo_path"))
        ]],
        colWidths=[0.9 * inch, 5.7 * inch, 0.9 * inch]
    )
    logos_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(logos_table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Programme: MCA - Master of Computer Applications</b>", subtitle_style))
    elements.append(Paragraph(f"<b>{paper_type}</b>", subtitle_style))
    elements.append(Spacer(1, 12))

    # Information Table
    max_marks = str(header_meta.get("max_marks", "100" if "SEE" in paper_type else "40"))
    info_data = [
        [f"TERM : {header_meta.get('term', '')}", f"COURSE NAME : {subject_info['name']}"],
        [f"DATE : {header_meta.get('date', '')}            TIME : {header_meta.get('time', '')}", f"COURSE CODE : {subject_info['code']}"],
        [f"SEMESTER : {subject_info['semester']}            MAX MARKS : {max_marks}", f"COURSE COORDINATORS : {header_meta.get('course_coordinators', '')}"]
    ]
    info_table = Table(info_data, colWidths=[3.25*inch, 3.25*inch])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    COL_QNUM  = 0.45 * inch
    COL_Q     = 4.75 * inch
    COL_BLOOM = 0.75 * inch
    COL_CO    = 0.50 * inch
    COL_MARKS = 0.55 * inch

    question_style = ParagraphStyle(
        'QBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        alignment=TA_LEFT,
        spaceAfter=0,
        leftIndent=0,
        rightIndent=0,
    )

    def xml_safe(text):
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('\u2192', '-&gt;')
                .replace('\u2190', '&lt;-')
                )

    question_table_data = [['Q. No', 'Questions', "Bloom's\nLevel", 'CO', 'Marks']]
    question_block_end_rows = []

    for q in questions_data:
        raw_text = q.get('text', '')
        bloom_raw = q.get('bloom', 'L2')
        co_raw = q.get('co', 'CO1')

        co_matches = re.findall(r'(\d+)', str(co_raw))
        co = ', '.join([f"CO{m}" for m in co_matches]) if co_matches else co_raw

        bloom_match = re.search(r'(L[1-6])', str(bloom_raw))
        bloom = bloom_match.group(1) if bloom_match else 'L2'

        lines = [l.rstrip() for l in raw_text.split('\n') if l.strip()]
        if not lines:
            continue

        first_line = lines[0]
        is_see = "SEE" in paper_type
        q_label = ""

        if is_see:
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                see_q_match = re.match(r'^Q(\d+)\(([ab])\)\.?\s*(.*?)\s*(?:\(\d+\s*Marks?\))?$', line, re.IGNORECASE)
                if see_q_match:
                    q_num = see_q_match.group(1)
                    q_part = see_q_match.group(2)
                    q_content = see_q_match.group(3).strip()
                    if not q_label:
                        q_label = f"Q{q_num}({q_part})"
                    if q_content:
                        cleaned_lines.append(q_content)
                else:
                    cleaned_line = re.sub(r'^Q\d+\([ab]\)\.?\s*', '', line, flags=re.IGNORECASE)
                    cleaned_line = re.sub(r'\s*\(\d+\s*Marks?\)\s*$', '', cleaned_line, flags=re.IGNORECASE)
                    if cleaned_line.strip():
                        cleaned_lines.append(cleaned_line.strip())
            lines = cleaned_lines
            if not lines:
                continue
            first_line = lines[0]
            first_content_clean = first_line
        else:
            q_num_match = re.match(r'^(Q\d+[\w\(\)]*\.?)\s*', first_line, re.IGNORECASE)
            q_label = q_num_match.group(1) if q_num_match else ''
            first_content = first_line[len(q_label):].strip() if q_label else first_line
            first_content_clean = re.sub(r'\s*\(?\d+\s*Marks?\)?\s*$', '', first_content, flags=re.IGNORECASE).strip()

        marks_text = "10" if is_see else str(q.get('marks', '10'))

        question_table_data.append([q_label, Paragraph(xml_safe(first_content_clean), question_style), bloom, co, marks_text])
        for rl in lines[1:]:
            rl = rl.strip()
            if rl:
                rl_clean = re.sub(r'^Q\d+\([ab]\)\.?\s*', '', rl, flags=re.IGNORECASE)
                rl_clean = re.sub(r'^Q\d+[\w\(\)]*\.?\s*', '', rl_clean, flags=re.IGNORECASE)
                rl_clean = re.sub(r'\s*\(\d+\s*Marks?\)\s*$', '', rl_clean, flags=re.IGNORECASE)
                rl_clean = rl_clean.strip()
                if rl_clean:
                    question_table_data.append(['', Paragraph(xml_safe(rl_clean), question_style), '', '', ''])
        question_block_end_rows.append(len(question_table_data) - 1)

        if q.get("is_or_after", False):
            or_style = ParagraphStyle('OR', alignment=TA_CENTER, fontSize=9, textColor=colors.black)
            question_table_data.append(['', Paragraph('<b>OR</b>', or_style), '', '', ''])
            question_block_end_rows.append(len(question_table_data) - 1)

    q_table = LongTable(
        question_table_data,
        colWidths=[COL_QNUM, COL_Q, COL_BLOOM, COL_CO, COL_MARKS],
        repeatRows=1,
        splitByRow=1
    )
    table_style_commands = [
        ('BOX',          (0, 0), (-1, -1), 0.5, colors.black),
        ('LINEBELOW',    (0, 0), (-1,  0), 0.5, colors.black),
        ('LINEAFTER',    (0, 0), (0, -1),  0.5, colors.black),
        ('LINEAFTER',    (1, 0), (1, -1),  0.5, colors.black),
        ('LINEAFTER',    (2, 0), (2, -1),  0.5, colors.black),
        ('LINEAFTER',    (3, 0), (3, -1),  0.5, colors.black),
        ('FONTNAME',     (0, 0), (-1,  0), 'Helvetica-Bold'),
        ('BACKGROUND',   (0, 0), (-1,  0), colors.lightgrey),
        ('ALIGN',        (0, 0), (-1,  0), 'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE',     (0, 0), (-1, -1), 9),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    table_style_commands.append(('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 0.5, colors.black))
    table_style_commands.append(('LINEABOVE', (0, 'splitfirst'), (-1, 'splitfirst'), 0.5, colors.black))
    for row_idx in question_block_end_rows:
        table_style_commands.append(('LINEBELOW', (0, row_idx), (-1, row_idx), 0.5, colors.black))
    q_table.setStyle(TableStyle(table_style_commands))
    elements.append(q_table)

    # Course Outcomes
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Course Outcomes (COs)</b>", ParagraphStyle('COH', alignment=TA_CENTER, fontSize=11, spaceAfter=8)))
    co_data = [['CO Number', 'Description']] + [[c[2], c[3]] for c in cos_list]
    cot = Table(co_data, colWidths=[1*inch, 5.5*inch])
    cot.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    elements.append(cot)

    # Bloom's Levels
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Bloom's Levels:</b>", ParagraphStyle('BH', alignment=TA_CENTER, fontSize=11, spaceAfter=6)))
    bt = Table(
        [['Remember (L1)', 'Understand (L2)', 'Apply (L3)'],
         ['Analyze (L4)',  'Evaluate (L5)',   'Create (L6)']],
        colWidths=[2.17*inch, 2.17*inch, 2.16*inch]
    )
    bt.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    elements.append(bt)

    # Signature Table
    elements.append(Spacer(1, 15))
    sig_data = [['Course Coordinator', 'Chief Course Coordinator', 'Program Coordinator', 'BoE Chairman'], ['', '', '', '']]
    sig_table = Table(sig_data, colWidths=[1.625*inch]*4)
    sig_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _resolve_default_logo_paths():
    """Resolve logo paths from local assets folder."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    local_assets_dir = os.path.join(project_root, "assets")
    os.makedirs(local_assets_dir, exist_ok=True)
    college_logo = os.path.join(local_assets_dir, "college_logo.png")
    vtu_logo = os.path.join(local_assets_dir, "vtu_logo.png")
    return (
        college_logo if os.path.exists(college_logo) else None,
        vtu_logo if os.path.exists(vtu_logo) else None,
    )


def _build_ia_scheme_questions(selected_subject_id):
    """Extract clean IA questions for scheme generation."""
    scheme_questions = []

    for i in range(1, 5):
        s = st.session_state.get(f"ia_set_{i}_{selected_subject_id}", {})

        for idx, q in enumerate(s.get("questions", []), 1):

            q_num = (i - 1) * 2 + idx
            subparts = q.get("subparts", [])

            # Case 1: Questions with subparts
            if subparts and len(subparts) > 1:

                for sp_idx, sp in enumerate(subparts):
                    label = chr(97 + sp_idx)

                    text = (
                        sp.get("text")
                        or sp.get("question_text")
                        or q.get("question_text")
                        or ""
                    ).strip()

                    scheme_questions.append({
                        "q_no": f"Q{q_num}({label})",
                        "text": text,
                        "marks": sp.get("marks", 10)
                    })

            # Case 2: Single question
            else:

                text = ""

                if subparts:
                    text = (
                        subparts[0].get("text")
                        or subparts[0].get("question_text")
                        or ""
                    )

                if not text:
                    text = q.get("question_text", "")

                text = str(text).strip()

                scheme_questions.append({
                    "q_no": f"Q{q_num}",
                    "text": text,
                    "marks": 10
                })

    return scheme_questions


def _build_see_scheme_questions(selected_subject_id):
    """Extract clean SEE questions for scheme generation."""
    scheme_questions = []

    for i in range(1, 6):

        s = st.session_state.get(f"see_set_{i}_{selected_subject_id}", {})

        for q in s.get("questions", []):

            q_num = q.get("question_number", "")

            for part in q.get("parts", []):

                text = (
                    part.get("text")
                    or part.get("question_text")
                    or q.get("question_text")
                    or ""
                ).strip()

                scheme_questions.append({
                    "q_no": f"Q{q_num}({part.get('part', 'a')})",
                    "text": text,
                    "marks": 10
                })

    return scheme_questions

def render(pattern):
    st.markdown(f"#### 📄 Question Paper Generator - {'IA' if pattern == 1 else 'SEE'}")

    if not ai.is_api_configured():
        st.error("⚠️ Engine not configured. Please set CLAUDE_API_KEY in .env file.")
        return

    user_id = st.session_state['user']['id']
    subjects = db.get_subjects(user_id)

    if not subjects:
        st.warning("Please add subjects first in the 'Manage Subjects' tab.")
        return

    subject_options = {s[2]: s[0] for s in subjects}
    selected_subject_name = st.selectbox("Select Subject", list(subject_options.keys()), key=f"subject_select_{pattern}")
    selected_subject_id = subject_options[selected_subject_name]
    st.session_state[f'selected_subject_id_{pattern}'] = selected_subject_id

    syllabus = db.get_syllabus(selected_subject_id)
    cos = db.get_cos(selected_subject_id)

    if not syllabus:
        st.warning("No syllabus found for this subject. Please add modules.")
        return

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # IA MODE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if pattern == 1:
        st.markdown("##### Edit Module Content for IA (Temporary)")

        edited_modules = {}
        for mod in syllabus:
            m_num = mod[2]
            m_content = mod[3]
            edited_content = st.text_area(f"Module {m_num} Content", value=m_content, height=150, key=f"ia_mod_{m_num}_{selected_subject_id}")
            if edited_content.strip():
                edited_modules[m_num] = edited_content

        st.markdown("---")
        st.subheader("IA Paper Configuration (Total 40 marks — 4 sets)")

        co_map = {f"{c[2]} - {c[3]}": c[2] for c in cos} if cos else {"General": "General"}
        co_display_list = list(co_map.keys())

        sets_config = {}
        for i in range(1, 5):
            with st.expander(f"Set {i} Configuration (10 Marks)", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    available_mod_nums = list(edited_modules.keys())
                    if not available_mod_nums:
                        st.error("No module content available.")
                        mod_select = None
                    else:
                        mod_select = st.selectbox(f"Select Module for Set {i}", available_mod_nums, key=f"set_{i}_mod")
                with c2:
                    subpattern = st.selectbox(f"Subpattern for Set {i}", ["10", "6+4", "5+5", "4+3+3"], key=f"set_{i}_pat")

                c3, c4 = st.columns(2)
                with c3:
                    selected_co_display = st.selectbox(f"Select CO for Set {i}", co_display_list, key=f"set_{i}_cos")
                    selected_co_num = co_map[selected_co_display]
                with c4:
                    bloom = st.selectbox(f"Bloom's Level for Set {i}", ["L2 - Understand", "L3 - Apply", "L4 - Analyze", "L5 - Evaluate", "L6 - Create"], key=f"set_{i}_bloom")

                if mod_select:
                    sets_config[i] = {
                        "module_text": edited_modules[mod_select],
                        "cos": [selected_co_num],
                        "bloom_level": bloom,
                        "subpattern": subpattern
                    }

                set_key = f"ia_set_{i}_{selected_subject_id}"
                is_generated = set_key in st.session_state
                btn_label = f"🔄 Regenerate Set {i}" if is_generated else f"⚡ Generate Set {i}"

                if st.button(btn_label, key=f"ia_gen_btn_{i}_{selected_subject_id}"):
                    if not mod_select:
                        st.error(f"Please configure Set {i} completely before generating.")
                    else:
                        with st.spinner(f"Generating Set {i}..."):
                            set_data = ai.generate_ia_set(selected_subject_name, i, sets_config[i])
                        if set_data:
                            st.session_state[set_key] = set_data
                            st.success(f"✅ Set {i} generated!")
                            st.rerun()
                        else:
                            st.error(f"Failed to generate Set {i}. Please try again.")

                if is_generated:
                    s = st.session_state[set_key]
                    st.markdown(f"**Generated Questions — Set {i}:**")
                    for idx, q in enumerate(s.get("questions", []), 1):
                        q_num = (i - 1) * 2 + idx
                        subparts = q.get("subparts", [])
                        if len(subparts) > 1:
                            lines = []
                            for sp_idx, sp in enumerate(subparts):
                                label = chr(97 + sp_idx)
                                lines.append(f"Q{q_num}({label}). {sp.get('text')} ({sp.get('marks')} Marks)")
                            default_text = "\n".join(lines)
                        else:
                            text_content = subparts[0].get('text') if subparts else q.get("question_text", "")
                            default_text = f"Q{q_num}. {text_content} (10 Marks)"
                        st.text_area(
                            f"Question {q_num} (Set {i} - Option {idx})",
                            value=default_text,
                            height=130,
                            key=f"edit_ia_q{i}_{idx}_{selected_subject_id}"
                        )
                    if len(s.get("questions", [])) > 0:
                        st.markdown("<p style='text-align:center; color:gray;'>— OR —</p>", unsafe_allow_html=True)
                    st.markdown("---")

        all_ia_sets_done = all(f"ia_set_{i}_{selected_subject_id}" in st.session_state for i in range(1, 5))

        if all_ia_sets_done:
            st.success("✅ All 4 sets generated! Review above and download.")

            st.markdown("##### IA Header Details")
            ia_title = st.selectbox(
                "Internal Assessment",
                ["Internal Assessment - I", "Internal Assessment - II", "Internal Assessment - III"],
                key=f"ia_title_{selected_subject_id}"
            )
            ia_term = st.text_input("Term", key=f"ia_term_{selected_subject_id}")
            ia_date = st.text_input("Date", key=f"ia_date_{selected_subject_id}")
            ia_time = st.text_input("Time", key=f"ia_time_{selected_subject_id}")
            ia_course_coords = st.text_input("Course Coordinators", value="", key=f"ia_coords_{selected_subject_id}")

            pdf_questions = []
            for i in range(1, 5):
                s = st.session_state[f"ia_set_{i}_{selected_subject_id}"]
                for idx, q in enumerate(s.get("questions", []), 1):
                    q_num = (i - 1) * 2 + idx
                    edit_key = f"edit_ia_q{i}_{idx}_{selected_subject_id}"
                    subparts = q.get("subparts", [])
                    if len(subparts) > 1:
                        lines = []
                        for sp_idx, sp in enumerate(subparts):
                            label = chr(97 + sp_idx)
                            lines.append(f"Q{q_num}({label}). {sp.get('text')}")
                        default_text = "\n".join(lines)
                    else:
                        text_content = subparts[0].get('text') if subparts else q.get("question_text", "")
                        default_text = f"Q{q_num}. {text_content}"
                    edited_text = st.session_state.get(edit_key, default_text)

                    if len(subparts) > 1:
                        for sp_idx, sp in enumerate(subparts):
                            label = chr(97 + sp_idx)
                            line_text = f"Q{q_num}({label}). {sp.get('text', '')}"
                            is_last_subpart = (sp_idx == len(subparts) - 1)
                            pdf_questions.append({
                                "set": i,
                                "choice": sp_idx,
                                "text": line_text,
                                "subparts": [],
                                "marks": sp.get("marks", 10),
                                "bloom": q.get("bloom_level", "L2"),
                                "co": ', '.join(q.get("cos", ["CO1"])),
                                "is_or_after": (idx == 1 and is_last_subpart)
                            })
                    else:
                        pdf_questions.append({
                            "set": i,
                            "choice": idx,
                            "text": edited_text,
                            "subparts": [],
                            "marks": 10,
                            "bloom": q.get("bloom_level", "L2"),
                            "co": ', '.join(q.get("cos", ["CO1"])),
                            "is_or_after": (idx == 1)
                        })

            subject_details = db.get_subjects(user_id)
            selected_subject_full = next((s for s in subject_details if s[0] == selected_subject_id), None)
            subject_info = {
                "name": selected_subject_full[2] if selected_subject_full else selected_subject_name,
                "code": selected_subject_full[3] if selected_subject_full else "N/A",
                "semester": selected_subject_full[4] if selected_subject_full else "N/A"
            }
            cos_list = db.get_cos(selected_subject_id)
            college_logo_path, vtu_logo_path = _resolve_default_logo_paths()
            pdf_buffer = generate_custom_pdf(
                ia_title,
                pdf_questions,
                subject_info,
                cos_list,
                {
                    "term": ia_term,
                    "date": ia_date,
                    "time": ia_time,
                    "course_coordinators": ia_course_coords,
                    "max_marks": "40",
                    "college_logo_path": college_logo_path,
                    "vtu_logo_path": vtu_logo_path,
                }
            )

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download IA Question Paper PDF",
                    data=pdf_buffer,
                    file_name=f"IA_{selected_subject_name}.pdf",
                    mime="application/pdf",
                    key=f"download_ia_{selected_subject_id}"
                )
            with col2:
                if st.button("📋 Generate Scheme of Evaluation", key=f"scheme_btn_ia_{selected_subject_id}"):
                    scheme_questions = _build_ia_scheme_questions(selected_subject_id)
                    st.session_state['scheme_from_qp'] = {
                        "subject_name": selected_subject_name,
                        "subject_id": selected_subject_id,
                        "questions": scheme_questions
                    }
                    if 'full_scheme' in st.session_state:
                        del st.session_state['full_scheme']
                    st.info("✅ Questions loaded! Please click the **'Scheme of Evaluation'** tab to generate.")

        else:
            generated_count = sum(1 for i in range(1, 5) if f"ia_set_{i}_{selected_subject_id}" in st.session_state)
            if generated_count > 0:
                st.info(f"📋 {generated_count}/4 sets generated. Generate all sets to enable download.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SEE MODE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    else:
        st.markdown("##### SEE Question Paper Configuration")
        st.info("📋 SEE Pattern: 5 Sets (one per module), each with 2 questions (internal choice). Each question has parts (a) and (b) worth 10 marks each.")

        if len(syllabus) < 5:
            st.warning(f"⚠️ SEE requires 5 modules. Currently only {len(syllabus)} module(s) found. Please add all 5 modules in 'Manage Subjects' tab.")
            return

        co_map = {f"{c[2]} - {c[3]}": c[2] for c in cos} if cos else {"General": "General"}
        co_display_list = list(co_map.keys())
        bloom_options = ["L2 - Understand", "L3 - Apply", "L4 - Analyze", "L5 - Evaluate", "L6 - Create"]

        sets_config = {}
        for i in range(1, 6):
            module = syllabus[i-1]
            module_content = module[3]

            with st.expander(f"Set {i} Configuration (Module {i})", expanded=True):
                st.caption(f"Questions {2*i-1} and {2*i} will be generated from this module")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Q{2*i-1}(a) & Q{2*i}(a):**")
                    co_a_display = st.selectbox(f"CO for part (a)", co_display_list, key=f"see_set{i}_co_a")
                    co_a = co_map[co_a_display]
                    bloom_a = st.selectbox(f"Bloom for part (a)", bloom_options, key=f"see_set{i}_bloom_a")
                with col2:
                    st.markdown(f"**Q{2*i-1}(b) & Q{2*i}(b):**")
                    co_b_display = st.selectbox(f"CO for part (b)", co_display_list, key=f"see_set{i}_co_b")
                    co_b = co_map[co_b_display]
                    bloom_b = st.selectbox(f"Bloom for part (b)", bloom_options, key=f"see_set{i}_bloom_b")

                sets_config[i] = {
                    "module_text": module_content,
                    "co_a": co_a,
                    "bloom_a": bloom_a,
                    "co_b": co_b,
                    "bloom_b": bloom_b
                }

                set_key = f"see_set_{i}_{selected_subject_id}"
                is_generated = set_key in st.session_state
                btn_label = f"🔄 Regenerate Set {i}" if is_generated else f"⚡ Generate Set {i}"

                if st.button(btn_label, key=f"see_gen_btn_{i}_{selected_subject_id}"):
                    with st.spinner(f"Generating SEE Set {i}..."):
                        set_data = ai.generate_see_set(selected_subject_name, i, sets_config[i])
                    if set_data:
                        st.session_state[set_key] = set_data
                        st.success(f"✅ Set {i} generated!")
                        st.rerun()
                    else:
                        st.error(f"Failed to generate Set {i}. Please try again.")

                if is_generated:
                    s = st.session_state[set_key]
                    st.markdown(f"**Generated Questions — Set {i}:**")
                    questions = s.get("questions", [])
                    question_count = 0
                    for q_idx, q in enumerate(questions):
                        q_num = q.get("question_number", str((i-1)*2 + q_idx + 1))
                        parts = q.get("parts", [])
                        for part_idx, part in enumerate(parts):
                            question_count += 1
                            part_letter = part.get('part', 'a')
                            question_text = f"Q{q_num}({part_letter}). {part.get('text','')} (10 Marks)"
                            if question_count == 3:
                                st.markdown("<h5 style='text-align:center; color:gray;'>OR</h5>", unsafe_allow_html=True)
                            st.text_area(f"Q{q_num}({part_letter})", value=question_text, height=80, key=f"see_edit_q{q_num}_{part_letter}_{selected_subject_id}")
                    st.markdown("---")

        all_see_sets_done = all(f"see_set_{i}_{selected_subject_id}" in st.session_state for i in range(1, 6))

        if all_see_sets_done:
            st.success("✅ All 5 sets generated! Review above and download.")
            st.markdown("##### SEE Header Details")
            see_term = st.text_input("Term", key=f"see_term_{selected_subject_id}")
            see_date = st.text_input("Date", key=f"see_date_{selected_subject_id}")
            see_time = st.text_input("Time", key=f"see_time_{selected_subject_id}")
            see_course_coords = st.text_input("Course Coordinators", value="", key=f"see_coords_{selected_subject_id}")

            edited_questions = []
            for i in range(1, 6):
                s = st.session_state[f"see_set_{i}_{selected_subject_id}"]
                questions = s.get("questions", [])
                for q_idx, q in enumerate(questions):
                    q_num = q.get("question_number", str((i-1)*2 + q_idx + 1))
                    parts = q.get("parts", [])
                    for part_idx, part in enumerate(parts):
                        part_letter = part.get('part', 'a')
                        edit_key = f"see_edit_q{q_num}_{part_letter}_{selected_subject_id}"
                        question_text = f"Q{q_num}({part_letter}). {part.get('text','')} (10 Marks)"
                        edited_text = st.session_state.get(edit_key, question_text)
                        edited_questions.append({
                            "set": i,
                            "question_number": q_num,
                            "part_letter": part_letter,
                            "text": edited_text,
                            "parts": [part],
                            "choice": 1 if q_idx == 0 else 2,
                            "marks": 10,
                            "bloom": part.get("bloom", "L2"),
                            "co": part.get("co", "CO1"),
                            "is_or_after": (q_idx == 0 and part_idx == 1)
                        })

            subject_details = db.get_subjects(user_id)
            selected_subject_full = next((s for s in subject_details if s[0] == selected_subject_id), None)
            subject_info = {
                "name": selected_subject_full[2] if selected_subject_full else selected_subject_name,
                "code": selected_subject_full[3] if selected_subject_full else "N/A",
                "semester": selected_subject_full[4] if selected_subject_full else "N/A"
            }
            cos_list = db.get_cos(selected_subject_id)
            college_logo_path, vtu_logo_path = _resolve_default_logo_paths()
            pdf_buffer = generate_custom_pdf(
                "Semester End Examination",
                edited_questions,
                subject_info,
                cos_list,
                {
                    "term": see_term,
                    "date": see_date,
                    "time": see_time,
                    "course_coordinators": see_course_coords,
                    "max_marks": "100",
                    "college_logo_path": college_logo_path,
                    "vtu_logo_path": vtu_logo_path,
                }
            )

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download SEE Question Paper PDF",
                    data=pdf_buffer,
                    file_name=f"SEE_{selected_subject_name}.pdf",
                    mime="application/pdf",
                    key=f"download_see_{selected_subject_id}"
                )
            with col2:
                if st.button("📋 Generate Scheme of Evaluation", key=f"scheme_btn_see_{selected_subject_id}"):
                    scheme_questions = _build_see_scheme_questions(selected_subject_id)
                    st.session_state['scheme_from_qp'] = {
                        "subject_name": selected_subject_name,
                        "subject_id": selected_subject_id,
                        "questions": scheme_questions
                    }
                    if 'full_scheme' in st.session_state:
                        del st.session_state['full_scheme']
                    st.info("✅ Questions loaded! Please click the **'Scheme of Evaluation'** tab to generate.")

        else:
            generated_count = sum(1 for i in range(1, 6) if f"see_set_{i}_{selected_subject_id}" in st.session_state)
            if generated_count > 0:
                st.info(f"📋 {generated_count}/5 sets generated. Generate all sets to enable download.")