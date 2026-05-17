"""
Textbook Manager Module
Handles extraction and retrieval of textbook content.
"""

import os
import pdfplumber
import streamlit as st
import database as db
import re
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Basic text cleaning"""
    if not text: return ""
    text = re.sub(r'\s+', ' ', text) # Normalize whitespace
    return text.strip()

import PyPDF2

def extract_text_from_pdf(pdf_path):
    """Extract full text from a PDF file using PyPDF2 for speed"""
    text_content = []
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(clean_text(text))
        return "\n\n".join(text_content)
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        return ""

def get_textbook_content(subject_id):
    """
    Retrieve and cache textbook content for a subject.
    Prioritizes PDF references.
    """
    cache_key = f"textbook_content_{subject_id}"
    
    # Return cached if available
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    logger.info(f"Loading textbook content for Subject ID: {subject_id}")
    refs = db.get_references(subject_id)
    full_text = ""
    
    found_pdf = False
    for ref in refs:
        # ref structure: (id, subject_id, text, pdf_path)
        pdf_path = ref[3] if len(ref) > 3 else None
        
        if pdf_path and os.path.exists(pdf_path):
            logger.info(f"Processing textbook: {pdf_path}")
            extracted = extract_text_from_pdf(pdf_path)
            if extracted:
                full_text += extracted + "\n\n"
                found_pdf = True
    
    if not found_pdf:
        logger.warning("No textbook PDF found for this subject.")
        
    # Cache the result (even if empty, to avoid re-querying)
    st.session_state[cache_key] = full_text
    return full_text

def get_relevant_context(question_text, subject_id, window_size=1000):
    """
    Find the most relevant text chunk from the textbook for a given question.
    Uses simple keyword overlap for robustness.
    """
    textbook_text = get_textbook_content(subject_id)
    if not textbook_text:
        return ""
        
    # Tokenize question
    q_tokens = set(re.findall(r'\w+', question_text.lower()))
    stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'of', 'to', 'in', 'for', 'with', 'by', 'explain', 'define', 'what', 'how'}
    q_keywords = q_tokens - stopwords
    
    if not q_keywords:
        return textbook_text[:2000] # Fallback to start of book
        
    import string
    
    # Pre-tokenize words for extremely fast scoring instead of applying regex in a loop
    words = textbook_text.split()
    word_hits = []
    
    for w in words:
        # crude but highly effective and fast tokenization
        t = w.lower().strip(string.punctuation)
        word_hits.append(1 if t in q_keywords else 0)
    
    chunk_len = 300 # words
    step = 150
    
    best_chunk_idx = 0
    max_score = 0
    
    for i in range(0, len(words), step):
        overlap = sum(word_hits[i:i+chunk_len])
        
        if overlap > max_score:
            max_score = overlap
            best_chunk_idx = i
            
    if max_score <= 1:
        return "" # No strong relevant context found
        
    best_chunk = " ".join(words[best_chunk_idx:best_chunk_idx+chunk_len])
    return best_chunk

