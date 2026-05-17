import streamlit as st
import ai_engine as ai
import database as db
import utils.textbook_manager as tm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, LongTable
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import io
import os



def generate_scheme_pdf(subject_name, schemes):
    """Generate a PDF for the full scheme of evaluation."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

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

    # Resolve logo paths directly (no header_meta needed for scheme PDF)
    _assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
    _college_logo = os.path.join(_assets_dir, "college_logo.png")
    _vtu_logo = os.path.join(_assets_dir, "vtu_logo.png")

    logos_table = Table(
        [[
            load_logo(_college_logo),
            center_cell,
            load_logo(_vtu_logo)
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
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Scheme of Evaluation — {subject_name}", subtitle_style))
    elements.append(Spacer(1, 12))

    def xml_safe(text):
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))

    for item in schemes:
        q_no = item.get("q_no", "")
        marks = item.get("marks", 0)
        q_text = str(item.get("question_text", item.get("text", ""))).strip()
        rubric = item.get("marking_rubric", [])

        q_header_style = ParagraphStyle('QHeader', parent=styles['Normal'],
                                         fontSize=10, fontName='Helvetica-Bold',
                                         spaceAfter=4, spaceBefore=10)
        q_text_style = ParagraphStyle('QText', parent=styles['Normal'],
                                       fontSize=9, leading=13,
                                       spaceAfter=6, leftIndent=8)
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'],
                                     fontSize=9, leading=12,
                                     leftIndent=4, rightIndent=4)
        # Question header (only once)
        elements.append(Paragraph(f"{q_no} ({marks} Marks)", q_header_style))

        # Question text in italics (always shown)
        q_text_display = q_text if q_text else "(Question text not available)"
        elements.append(Paragraph(f"<i>{xml_safe(q_text_display)}</i>", q_text_style))

        # Rubric table
        table_data = [
            [Paragraph("<b>Section</b>", cell_style), Paragraph("<b>Marks</b>", cell_style)]
        ]
        for row in rubric:
            table_data.append([
                Paragraph(xml_safe(row.get("Section", "")), cell_style),
                Paragraph(str(row.get("Marks", "")), cell_style)
            ])
        table_data.append([
            Paragraph("<b>Total</b>", cell_style),
            Paragraph(f"<b>{marks}</b>", cell_style)
        ])

        t = Table(table_data, colWidths=[5.8*inch, 0.8*inch])
        t.setStyle(TableStyle([
            ('GRID',          (0, 0),  (-1, -1), 0.5, colors.black),
            ('BACKGROUND',    (0, 0),  (-1,  0), colors.lightgrey),
            ('BACKGROUND',    (0, -1), (-1, -1), colors.lightgrey),
            ('VALIGN',        (0, 0),  (-1, -1), 'TOP'),
            ('ALIGN',         (1, 0),  (1,  -1), 'CENTER'),
            ('TOPPADDING',    (0, 0),  (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0),  (-1, -1), 4),
            ('LEFTPADDING',   (0, 0),  (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0),  (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def render():
    st.markdown("### 📋 Scheme of Evaluation Generator")

    if not ai.is_api_configured():
        st.error("⚠️ Claude API not configured. Please set CLAUDE_API_KEY in .env file.")
        return

    user_id = st.session_state['user']['id']
    subjects = db.get_subjects(user_id)
    if not subjects:
        st.warning("Please add subjects first.")
        return

    subject_options = {s[2]: s[0] for s in subjects}

    # --- Check if questions were passed from QP Generator ---
    from_qp = st.session_state.get('scheme_from_qp')

    if from_qp:
        st.success("✅ Questions loaded from Question Paper Generator.")
        selected_subject_name = from_qp['subject_name']
        selected_subject_id = from_qp['subject_id']
        st.markdown(f"**Subject:** {selected_subject_name}")

        questions = from_qp['questions']

        # Display loaded questions (read-only preview)
        with st.expander("📄 Loaded Questions", expanded=False):
            for q in questions:
                st.markdown(f"**{q['q_no']}** ({q['marks']} Marks): {q['text']}")

        if st.button("🔄 Clear & Enter Manually"):
            del st.session_state['scheme_from_qp']
            st.rerun()

        if st.button("⚡ Generate Scheme for Full Question Paper"):
            all_schemes = []
            progress = st.progress(0)
            total = len(questions)
            st.write(questions)

            with st.spinner("Generating scheme for all questions..."):
                syllabus = db.get_syllabus(selected_subject_id)
                syllabus_text = "\n".join([f"Module {m[2]}: {m[3]}" for m in syllabus]) if syllabus else ""

                for i, q in enumerate(questions):
                    context = tm.get_relevant_context(q['text'], selected_subject_id)
                    combined_context = f"Syllabus:\n{syllabus_text}\n\nReference:\n{context}"

                    scheme_data = ai.generate_scheme(
                        selected_subject_name,
                        f"Question: {q['text']} ({q['marks']} Marks)",
                        context_text=combined_context
                    )

                    if scheme_data and "scheme" in scheme_data and scheme_data["scheme"]:
                        rubric = scheme_data["scheme"][0].get("marking_rubric", [])
                        all_schemes.append({
                            "q_no": q["q_no"],
                            "marks": q["marks"],
                            "question_text": q.get("text", ""),
                            "marking_rubric": rubric
                        })
                    else:
                        all_schemes.append({
                            "q_no": q["q_no"],
                            "marks": q["marks"],
                            "question_text": q.get("text", ""),
                            "marking_rubric": [{"Section": "Answer", "Marks": q["marks"]}]
                        })

                    progress.progress((i + 1) / total)

            st.session_state['full_scheme'] = {
                "subject_name": selected_subject_name,
                "schemes": all_schemes
            }
            st.success("✅ Scheme generated for all questions!")

    else:
        # --- Manual single-question mode ---
        st.markdown("#### Enter Question Manually")
        selected_subject_name = st.selectbox("Select Subject", list(subject_options.keys()),
                                              key="scheme_subject_manual")
        selected_subject_id = subject_options[selected_subject_name]

        paper_text = st.text_area("Paste Question Text Here", height=150, key="scheme_text_area")
        marks = st.number_input("Marks", min_value=1, max_value=100, value=10, key="scheme_marks")

        if st.button("⚡ Generate Scheme"):
            if not paper_text.strip():
                st.error("Please provide the question content.")
            else:
                with st.spinner("Generating scheme..."):
                    syllabus = db.get_syllabus(selected_subject_id)
                    syllabus_text = "\n".join([f"Module {m[2]}: {m[3]}" for m in syllabus]) if syllabus else ""
                    context = tm.get_relevant_context(paper_text, selected_subject_id)
                    combined_context = f"Syllabus:\n{syllabus_text}\n\nReference:\n{context}"

                    scheme_data = ai.generate_scheme(
                        selected_subject_name,
                        f"Question: {paper_text} ({marks} Marks)",
                        context_text=combined_context
                    )

                    if scheme_data and "scheme" in scheme_data:
                        rubric = scheme_data["scheme"][0].get("marking_rubric", [])
                        total_marks = scheme_data["scheme"][0].get("marks", marks)
                        st.session_state['full_scheme'] = {
                            "subject_name": selected_subject_name,
                            "schemes": [{
                                "q_no": "Q1",
                                "marks": total_marks,
                                "question_text": paper_text,
                                "marking_rubric": rubric
                            }]
                        }
                        st.success("Scheme generated!")
                    else:
                        st.error("Failed to generate scheme.")

    # --- Display & Download ---
    if 'full_scheme' in st.session_state:
        full = st.session_state['full_scheme']
        st.markdown("---")
        st.markdown("### 📊 Scheme of Evaluation")

        for item in full['schemes']:
            st.markdown(f"**{item['q_no']} ({item['marks']} Marks)**")
            display_data = item['marking_rubric'].copy()
            display_data.append({"Section": "**Total**", "Marks": f"**{item['marks']}**"})
            st.table(display_data)

        # PDF Download
        pdf_buffer = generate_scheme_pdf(full['subject_name'], full['schemes'])
        st.download_button(
            label="⬇️ Download Scheme PDF",
            data=pdf_buffer,
            file_name=f"Scheme_{full['subject_name']}.pdf",
            mime="application/pdf",
            key="download_scheme_pdf"
        )