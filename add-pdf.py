# Mentornship Internship Project #1
# Name: Ayesha Mahmood
# Date:
import sqlite3
import fitz  
import os
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)

# Load English language model for spaCy
nlp = spacy.load("en_core_web_sm")

# Define stop words as a list
stop_words = list(spacy.lang.en.stop_words.STOP_WORDS)
# Add tokenized versions of certain stop words to avoid preprocessing warnings
additional_stop_words = ["'ll", "'ve"]
stop_words.extend(additional_stop_words)

# Define the folder where uploaded files will be stored
UPLOAD_FOLDER = '/Users/ayeshamahmood/Downloads/resume internship'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to create the database file named "pdf_database.db" and table
def create_database():
    conn = sqlite3.connect('pdf_database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text if text.strip() else None
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None

# Function to extract text from a DOCX file
def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text if text.strip() else None
    except Exception as e:
        print(f"Error reading {docx_path}: {e}")
        return None
def extract_name_and_email(content):
    # Regular expression pattern to match email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Regular expression pattern to match name
    name_pattern = r'\b[A-Z][a-z]*\s[A-Z][a-z]*\b'  # Assumes name format: Firstname Lastname
    
    # Search for email addresses and names in the content
    emails = re.findall(email_pattern, content)
    names = re.findall(name_pattern, content)
    
    # If multiple emails are found, choose the first one
    email = emails[0] if emails else None
    
    # If multiple names are found, choose the first one
    name = names[0] if names else None
    
    return name, email
# Route to handle the form submission
@app.route('/upload', methods=['GET', 'POST'])
def add_files_to_database():
    if request.method == 'POST':
        job_description = request.form['job_description']
        uploaded_files = request.files.getlist('file')
        for file in uploaded_files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            title = os.path.splitext(filename)[0]
            content = None
            if filename.endswith('.pdf'):
                content = extract_text_from_pdf(file_path)
            elif filename.endswith('.docx'):
                content = extract_text_from_docx(file_path)
            if content:
                conn = sqlite3.connect('pdf_database.db')
                c = conn.cursor()
                c.execute('SELECT * FROM documents WHERE title = ?', (title,))
                existing_resume = c.fetchone()
                if not existing_resume:
                    c.execute('INSERT INTO documents (title, content) VALUES (?, ?)', (title, content))
                    conn.commit()
                    conn.close()
                else:
                    print(f"Resume '{title}' already exists in the database. Skipping insertion.")
        # Redirect to the score route after uploading files
        return redirect(url_for('score', job_description=job_description))

    return render_template('upload.html')

@app.route('/score')
def score():
    job_description = request.args.get('job_description')
    if not job_description:
        return "Job description is missing!", 400
    
    scores = score_resumes(job_description)
    return render_template('score.html', scores=scores)

@app.route('/')
def index():
    return redirect(url_for('add_files_to_database'))

# Function to retrieve all resumes from the database
def retrieve_all_resumes():
    conn = sqlite3.connect('pdf_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM documents")
    all_resumes = c.fetchall()
    conn.close()
    return all_resumes

def score_resumes(job_description):
    resumes = retrieve_all_resumes()
    if not resumes:
        print("No resumes found in the database.")
        return []

    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    all_texts = [resume[2] for resume in resumes if resume[2] is not None]
    
    if not all_texts:
        print("No valid resumes found in the database.")
        return []

    tfidf_matrix = tfidf_vectorizer.fit_transform(all_texts)
    job_desc_vector = tfidf_vectorizer.transform([job_description])

    scores = []
    for i, resume in enumerate(resumes):
        similarity = cosine_similarity(job_desc_vector, tfidf_matrix[i])[0][0] * 100
        
        # Extract name and email from resume content
        name, email = extract_name_and_email(resume[2])  
        
        job_desc_tokens = set(token.text.lower() for token in nlp(job_description) if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'])
        resume_tokens = set(token.text.lower() for token in nlp(resume[2]) if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'])
        
        matched_skills = job_desc_tokens.intersection(resume_tokens)
        
        scores.append((name, email, resume[1], similarity, matched_skills))

    # Sort the scores from highest to lowest percentage
    scores.sort(key=lambda x: x[3], reverse=True)

    return scores


if __name__ == "__main__":
    create_database()
    app.run(debug=True)