import streamlit as st
import requests
import io
from supabase import create_client, Client
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Configuration & Setup
st.set_page_config(page_title="Questionnaire AI", layout="wide", page_icon="📝")

# Load Secrets
try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except FileNotFoundError:
    st.error("Secrets file not found! Please create .streamlit/secrets.toml")
    st.stop()
except KeyError as e:
    st.error(f"Missing key in secrets file: {e}")
    st.stop()

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Helper Functions ---

def get_auth_headers():
    if "access_token" not in st.session_state:
        return {}
    return {"Authorization": f"Bearer {st.session_state.access_token}"}

def api_get(endpoint):
    try:
        res = requests.get(f"{API_BASE_URL}{endpoint}", headers=get_auth_headers())
        if res.status_code == 401:
            st.warning("Session expired. Please login again.")
            st.session_state.access_token = None
            st.rerun()
        return res
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def api_post(endpoint, data=None, files=None):
    try:
        res = requests.post(f"{API_BASE_URL}{endpoint}", headers=get_auth_headers(), data=data, files=files)
        if res.status_code == 401:
            st.warning("Session expired. Please login again.")
            st.session_state.access_token = None
            st.rerun()
        return res
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def api_put(endpoint, json_data):
    try:
        res = requests.put(f"{API_BASE_URL}{endpoint}", headers=get_auth_headers(), json=json_data)
        return res
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# --- PDF Export Logic (Updated with Summary) ---
def create_pdf(answer_set, q_filename):
    """Generates a PDF file with Summary, Questions, Answers, and Unique Citations."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = []

    # Custom Styles
    styles.add(ParagraphStyle(name='QuestionHeader', parent=styles['Heading3'], spaceAfter=6, textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='AnswerBody', parent=styles['BodyText'], spaceAfter=6, leading=14))
    styles.add(ParagraphStyle(name='Citation', parent=styles['BodyText'], fontSize=9, textColor=colors.grey, leftIndent=20))
    styles.add(ParagraphStyle(name='Meta', parent=styles['BodyText'], fontSize=8, textColor=colors.green))

    # Title
    story.append(Paragraph(f"Questionnaire Response: {q_filename}", styles['Title']))
    story.append(Spacer(1, 12))

    # --- NEW: Summary Section ---
    if 'summary' in answer_set:
        summ = answer_set['summary']
        story.append(Paragraph("Coverage Summary", styles['Heading3']))
        
        # Create Table Data
        data = [
            ["Total Questions", str(summ['total'])],
            ["Answered with Citations", str(summ['covered'])],
            ["Not Found / No Context", str(summ['not_found'])],
            ["Coverage Percentage", f"{summ['percentage']}%"]
        ]
        
        t = Table(data, colWidths=[200, 100], hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('PADDING', (0,0), (-1,-1), 6),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('TEXTCOLOR', (0,2), (1,2), colors.red), # Highlight 'Not Found' row in red
        ]))
        story.append(t)
        story.append(Spacer(1, 20))
    # ----------------------------

    if not answer_set or 'answers' not in answer_set:
        story.append(Paragraph("No answers available.", styles['BodyText']))
    else:
        for i, ans in enumerate(answer_set['answers']):
            block = []
            
            # Question Text
            q_text = ans.get('question_text', f"Question {i+1}")
            block.append(Paragraph(f"{i+1}. {q_text}", styles['QuestionHeader']))
            
            # Answer
            ans_text = ans.get('text', '(No answer generated)')
            block.append(Paragraph(ans_text, styles['AnswerBody']))
            
            # Confidence
            conf = ans.get('confidence_score', 0)
            if conf:
                block.append(Paragraph(f"Confidence: {conf:.2f}", styles['Meta']))

            # Citations
            if ans.get('citations'):
                unique_docs = set()
                for cit in ans['citations']:
                    unique_docs.add(cit.get('reference_document_name', 'Unknown Document'))
                
                if unique_docs:
                    block.append(Paragraph("<b>Sources:</b>", styles['BodyText']))
                    for doc_name in unique_docs:
                        citation_text = f"• {doc_name}" 
                        block.append(Paragraph(citation_text, styles['Citation']))
            
            block.append(Spacer(1, 12))
            story.append(KeepTogether(block))

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- UI Pages ---

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 DocuAnswer Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            c1, c2 = st.columns(2)
            with c1:
                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
            with c2:
                signup = st.form_submit_button("Sign Up", use_container_width=True)

        if submitted:
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.access_token = res.session.access_token
                st.session_state.user_email = res.user.email
                st.success("Login successful!")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
        
        if signup:
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.info("Signup successful! Please check your email for confirmation.")
            except Exception as e:
                st.error(f"Signup failed: {str(e)}")

def dashboard_page():
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_email}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.access_token = None
            st.rerun()
        
        st.divider()
        
        st.subheader("1. References")
        ref_files = st.file_uploader("Upload Docs (PDF, TXT)", accept_multiple_files=True, key="ref_up")
        if st.button("Upload References", use_container_width=True):
            if ref_files:
                progress_bar = st.progress(0)
                for idx, f in enumerate(ref_files):
                    api_post("/references/upload", files={"file": (f.name, f.getvalue(), f.type)})
                    progress_bar.progress((idx + 1) / len(ref_files))
                st.success("References uploaded!")
                st.rerun()

        st.divider()

        st.subheader("2. Questionnaires")
        q_file = st.file_uploader("Upload Questionnaire", type=["pdf", "xlsx"], key="q_up")
        if st.button("Upload Questionnaire", use_container_width=True):
            if q_file:
                with st.spinner("Parsing..."):
                    res = api_post("/questionnaires/upload", files={"file": (q_file.name, q_file.getvalue(), q_file.type)})
                    if res and res.status_code == 200:
                        st.success("Uploaded!")
                        st.rerun()
                    else:
                        st.error("Failed to upload.")

    st.title("📂 My Questionnaires")
    q_res = api_get("/questionnaires")
    qs = q_res.json() if (q_res and q_res.status_code == 200) else []

    if not qs:
        st.info("No questionnaires yet. Upload one from the sidebar.")
    else:
        for q in qs:
            with st.container():
                c1, c2 = st.columns([5, 1])
                c1.subheader(f"📄 {q['filename']}")
                c1.caption(f"Uploaded: {q['created_at'][:10]}")
                if c2.button("Open", key=q['id'], use_container_width=True):
                    st.session_state.selected_q_id = q['id']
                    st.session_state.selected_q_name = q['filename']
                    st.rerun()
                st.divider()
    
    with st.expander("View Indexed Reference Documents"):
        ref_res = api_get("/references")
        if ref_res and ref_res.status_code == 200:
            seen_refs = set()
            for r in ref_res.json():
                if r['filename'] not in seen_refs:
                    st.text(f"• {r['filename']}")
                    seen_refs.add(r['filename'])

def results_page():
    q_id = st.session_state.selected_q_id
    q_name = st.session_state.selected_q_name

    c1, c2 = st.columns([1, 5])
    if c1.button("← Back"):
        del st.session_state.selected_q_id
        st.rerun()
    
    st.title(f"📝 {q_name}")

    col_gen, col_pdf = st.columns([1, 4])
    
    if col_gen.button("✨ Generate Answers", type="primary"):
        with st.spinner("Analyzing documents and answering questions..."):
            res = api_post(f"/questionnaires/{q_id}/generate")
            if res and res.status_code == 200:
                data = res.json()
                st.session_state.active_set_id = data.get("answer_set_id") or data.get("id")
                st.success("Done!")
                st.rerun()
            else:
                st.error("Generation failed. Ensure you have reference docs.")

    if "active_set_id" in st.session_state:
        ans_res = api_get(f"/answer-sets/{st.session_state.active_set_id}")
        if ans_res and ans_res.status_code == 200:
            answer_set = ans_res.json()
            answers = answer_set.get("answers", [])
            
            # --- NEW: Display Coverage Metrics ---
            if 'summary' in answer_set:
                st.markdown("### 📊 Coverage Summary")
                summ = answer_set['summary']
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Questions", summ['total'])
                m2.metric("Answered", summ['covered'])
                m3.metric("Not Found", summ['not_found'])
                m4.metric("Coverage %", f"{summ['percentage']}%")
                st.divider()
            # -------------------------------------

            pdf_file = create_pdf(answer_set, q_name)
            col_pdf.download_button("⬇️ Download PDF", data=pdf_file, file_name=f"{q_name}_answers.pdf", mime="application/pdf")
            
            st.write("")

            for i, ans in enumerate(answers):
                q_text = ans.get('question_text', f"Question {i+1}")
                with st.expander(f"{i+1}. {q_text}", expanded=True):
                    
                    new_text = st.text_area("Answer", value=ans['text'], height=150, key=f"txt_{ans['id']}")
                    if new_text != ans['text']:
                        if st.button("Save Changes", key=f"save_{ans['id']}"):
                            api_put(f"/answers/{ans['id']}", {"text": new_text})
                            st.toast("Saved!")
                    
                    bot_c1, bot_c2 = st.columns([1, 3])
                    score = ans.get("confidence_score") or 0
                    color = "green" if score > 0.7 else "orange" if score > 0.4 else "red"
                    bot_c1.markdown(f"**Confidence:** :{color}[{score:.2f}]")
                    
                    if ans.get("citations"):
                        unique_docs = set()
                        for cit in ans['citations']:
                            unique_docs.add(cit.get('reference_document_name', 'Unknown'))
                        
                        if unique_docs:
                            bot_c2.markdown("**Sources:**")
                            for doc_name in unique_docs:
                                bot_c2.caption(f"📄 {doc_name}")

        else:
            st.warning("Could not load answers.")
    else:
        st.info("Click 'Generate Answers' to start.")

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if not st.session_state.access_token:
    login_page()
else:
    if "selected_q_id" in st.session_state:
        results_page()
    else:
        dashboard_page()