import os
import json
import re
import streamlit as st
from anthropic import Anthropic

# Works locally (.env) AND on Streamlit Cloud (secrets)
try:
    CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"]
except Exception:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=_env_path, override=True)
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
_MODEL = "claude-sonnet-4-6"


def _call_claude(prompt: str) -> str:
    """Single entry point for all Claude API calls."""
    if not CLAUDE_API_KEY:
        raise ValueError("CLAUDE_API_KEY is not configured.")
    client = Anthropic(api_key=CLAUDE_API_KEY)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    if not response or not response.content or not response.content[0].text:
        raise Exception("Empty response from Claude API.")
    return response.content[0].text


def clean_json_text(text: str) -> str:
    """Extract the outermost JSON object or array from a string."""
    try:
        md_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if md_match:
            text = md_match.group(1)
        text = text.strip()
        start_obj = text.find('{')
        start_arr = text.find('[')
        end_obj = text.rfind('}')
        end_arr = text.rfind(']')
        if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
            text = text[start_arr:end_arr + 1]
        elif start_obj != -1:
            text = text[start_obj:end_obj + 1]
    except Exception as e:
        print(f"JSON cleaning error: {e}")
    return text


def configure_ia_engine():
    return is_api_configured()

def configure_see_engine():
    return is_api_configured()
    
def is_api_configured() -> bool:
    return bool(CLAUDE_API_KEY)

# --- IA Question Generation ---

def _validate_ia_content(data: dict) -> bool:
    """Check that generated IA questions are self-contained (no placeholders)."""
    if not data or "sets" not in data:
        return False
    forbidden = ["refer to", "main question", "above question", "mentioned above",
                 "previous question", "same as above"]
    try:
        for s in data["sets"]:
            for q in s["questions"]:
                if any(p in q.get("question_text", "").lower() for p in forbidden):
                    return False
                if len(q.get("question_text", "")) < 10:
                    return False
                for sub in q.get("subparts", []):
                    if any(p in sub.get("text", "").lower() for p in forbidden):
                        return False
                    if len(sub.get("text", "")) < 5:
                        return False
        return True
    except Exception:
        return False


def generate_ia_set(subject_name: str, set_number: int, config: dict):
    """Generate questions for a single IA set."""
    if not CLAUDE_API_KEY:
        return None

    subpattern = config['subpattern']
    if subpattern == "10":
        subparts_rule = (
            "Each question is a SINGLE question worth 10 marks with NO sub-questions. "
            "The subparts list must have exactly ONE item with marks=10."
        )
        subparts_template = '[{"text": "Full question text here", "marks": 10}]'
    else:
        mark_values = [int(m) for m in subpattern.split("+")]
        labels = [chr(97 + i) for i in range(len(mark_values))]
        subparts_rule = (
            f"Each question MUST be split into {len(mark_values)} sub-parts: "
            + ", ".join([f"part ({l}) worth {m} marks" for l, m in zip(labels, mark_values)])
            + f". Total = {sum(mark_values)} marks. "
            "The subparts list must have exactly that many items with those exact marks."
        )
        subparts_template = json.dumps(
            [{"text": f"Sub-question ({l}) text here", "marks": m} for l, m in zip(labels, mark_values)]
        )

    prompt = f"""You are an MCA university examiner. Generate exactly ONE set for an Internal Assessment paper.

Subject: {subject_name}
Set Number: {set_number}
Module Content: {config['module_text']}
Course Outcome: {', '.join(config['cos'])}
Bloom's Level: {config['bloom_level']}

MARKS PATTERN RULE (STRICTLY ENFORCE):
{subparts_rule}

TASK: Generate exactly 2 alternative questions (student answers ONE). Each question carries 10 marks total.

REQUIREMENTS:
1. MCA postgraduate depth. Every question is fully self-contained.
2. No placeholders. No cross-references to other questions.
3. Include algorithms/pseudocode, numerical problems, or comparisons where relevant — keep them BRIEF.
4. Each sub-part question text must be independently meaningful and answerable.
5. LENGTH CONSTRAINT: Each question/subpart must be 2-3 sentences maximum. Be direct and concise.

FORMATTING RULES:
- Write question text as structured prose, NOT a wall of text.
- If the question involves a dataset or list: put EACH entry on its own line using \\n inside the JSON string.
- If the question involves algorithm steps: number each step and put each on its own line.
- Example: "Given the following data:\\nName: Alice, Age: 25\\nName: Bob, Age: 30\\nFind the average age."

OUTPUT: Return ONLY a raw JSON object with no markdown and no explanation:
{{
  "set_number": {set_number},
  "questions": [
    {{
      "question_text": "Overall topic or context (can be empty string if sub-parts are self-contained)",
      "subparts": {subparts_template},
      "cos": ["{', '.join(config['cos'])}"],
      "bloom_level": "{config['bloom_level']}"
    }},
    {{
      "question_text": "Overall topic or context (can be empty string if sub-parts are self-contained)",
      "subparts": {subparts_template},
      "cos": ["{', '.join(config['cos'])}"],
      "bloom_level": "{config['bloom_level']}"
    }}
  ]
}}

CRITICAL: The subparts array MUST match exactly the structure shown — same number of items, same marks values. Escape internal double-quotes with backslash. Return raw JSON only."""

    for attempt in range(2):
        try:
            text = _call_claude(prompt)
            data = json.loads(clean_json_text(text))
            if "questions" in data and len(data["questions"]) == 2:
                return data
            print(f"Set {set_number} structure invalid, retrying...")
        except Exception as e:
            st.error(f"Error generating Set {set_number} (Attempt {attempt + 1}): {e}")
    return None


# --- SEE Question Generation ---

def generate_see_set(subject_name: str, set_number: int, config: dict):
    """Generate questions for a single SEE set (one module)."""
    if not CLAUDE_API_KEY:
        return None

    q1_num = (set_number - 1) * 2 + 1
    q2_num = q1_num + 1

    prompt = f"""You are an MCA university examiner. Generate questions for ONE set of a Semester End Examination (SEE) paper.

Subject: {subject_name}
Set Number: {set_number} (Module {set_number})
Module Content: {config['module_text']}
Part (a): CO = {config['co_a']}, Bloom's Level = {config['bloom_a']}
Part (b): CO = {config['co_b']}, Bloom's Level = {config['bloom_b']}

TASK: Generate exactly 2 questions (internal choice) for this single set.
- Question {q1_num} has parts (a) and (b), each worth 10 marks.
- Question {q2_num} is an internal choice with the SAME COs and Bloom levels.

REQUIREMENTS:
1. MCA postgraduate depth. Every question is fully self-contained.
2. No placeholders or cross-references.
3. Include algorithms, numerical problems or comparisons where relevant — keep them BRIEF.
4. LENGTH CONSTRAINT: Each question part must be 2-3 sentences maximum.
a
FORMATTING RULES:
- Write question text as structured prose, NOT a wall of text.
- If the question involves a dataset or list: put EACH entry on its own line using \\n inside the JSON string.
- If the question involves algorithm steps: number each step on its own line.
- Example: "Given the following relations:\\nEmployee(EmpID, Name, DeptID)\\nDepartment(DeptID, DeptName)\\nWrite an SQL query to list all employees with their department names."

OUTPUT: Return ONLY a raw JSON object (no markdown, no explanation):
{{
  "set_number": {set_number},
  "module_number": {set_number},
  "questions": [
    {{
      "question_number": "{q1_num}",
      "parts": [
        {{"part": "a", "text": "...", "co": "{config['co_a']}", "bloom": "{config['bloom_a']}", "marks": 10}},
        {{"part": "b", "text": "...", "co": "{config['co_b']}", "bloom": "{config['bloom_b']}", "marks": 10}}
      ]
    }},
    {{
      "question_number": "{q2_num}",
      "parts": [
        {{"part": "a", "text": "...", "co": "{config['co_a']}", "bloom": "{config['bloom_a']}", "marks": 10}},
        {{"part": "b", "text": "...", "co": "{config['co_b']}", "bloom": "{config['bloom_b']}", "marks": 10}}
      ]
    }}
  ]
}}
Escape all internal double-quotes with backslash. Return raw JSON only."""

    for attempt in range(2):
        try:
            text = _call_claude(prompt)
            data = json.loads(clean_json_text(text))
            if "questions" in data and len(data["questions"]) == 2:
                return data
            print(f"SEE Set {set_number} structure invalid, retrying...")
        except Exception as e:
            st.error(f"Error generating SEE Set {set_number} (Attempt {attempt + 1}): {e}")
    return None


# --- Scheme Generation ---

def generate_scheme(subject_name: str, questions_text: str, context_text: str = ""):
    """Generate a scheme of evaluation for a given question."""
    if not CLAUDE_API_KEY:
        return None

    prompt = f"""You are an expert university-level academic examiner for MCA (Master of Computer Applications).
Subject: {subject_name}

Your task is to generate a Scheme of Evaluation ONLY for the given Target Question.
Do NOT add extra questions. Do NOT deviate from what is asked.

Target Question:
{questions_text}

Reference Context (Syllabus & Textbook):
{context_text if context_text else 'No additional context provided.'}

INSTRUCTIONS:
1. Focus ONLY on the exact requirement of the question.
2. Generate a simple table format for the scheme of evaluation.
3. Keep each expected key answer very short (1-2 words or a concise phrase).

MARKING RUBRIC GUIDELINES:
1. Break marks into granular components (e.g., Introduction, Algorithm Steps, Dataset, etc.).
2. Each component must have a clear, extremely short expected answer.
3. Allow fractional marks (e.g., 0.5, 1.5).

OUTPUT FORMAT (STRICT JSON ONLY):
Return a JSON object with key "scheme" containing a list of objects.
Each object must contain:
- marking_rubric: list of objects:
  {{"Section": "1-2 word key answer", "Marks": float}}
- marks: float (total marks for that question)

VALIDATION:
- Ensure total marks = sum of rubric marks
- Strict JSON format (no markdown, no explanation outside JSON)

Output ONLY the raw JSON string."""

    try:
        text = _call_claude(prompt)
        return json.loads(clean_json_text(text))
    except Exception as e:
        st.error(f"Error generating scheme: {e}")
        return None