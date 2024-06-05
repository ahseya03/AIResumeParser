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
# Import statements
# import os
# import re
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# import sqlite3
# import fitz
# from docx import Document
# import spacy
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# from flask import Flask, render_template, request, redirect, url_for
# from werkzeug.utils import secure_filename

# app = Flask(__name__)

# SMTP_SERVER = 'smtp.gmail.com'
# SMTP_PORT = 587
# UPLOAD_FOLDER = '/Users/ayeshamahmood/Downloads/resume_internship/uploads'  # Updated path
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# nlp = spacy.load("en_core_web_sm")
# stop_words = list(spacy.lang.en.stop_words.STOP_WORDS)
# additional_stop_words = ["'ll", "'ve"]
# stop_words.extend(additional_stop_words)

# def create_database():
#     conn = sqlite3.connect('pdf_database.db')
#     c = conn.cursor()
#     c.execute('''
#         CREATE TABLE IF NOT EXISTS documents (
#             id INTEGER PRIMARY KEY,
#             title TEXT,
#             content TEXT
#         )
#     ''')
#     conn.commit()
#     conn.close()

# def send_email(email, subject, body):
#     sender_email = os.environ.get('EMAIL_USERNAME')
#     sender_password = os.environ.get('EMAIL_PASSWORD')

#     if not sender_email or not sender_password:
#         print("Email credentials not found. Please set EMAIL_USERNAME and EMAIL_PASSWORD environment variables.")
#         return

#     msg = MIMEMultipart()
#     msg['From'] = sender_email
#     msg['To'] = email
#     msg['Subject'] = subject

#     # Attach body without re-encoding
#     msg.attach(MIMEText(body, 'plain', 'utf-8'))

#     try:
#         server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
#         server.starttls()
#         server.login(sender_email, sender_password)
#         server.sendmail(sender_email, email, msg.as_string())
#         server.quit()
#         print(f"Feedback email sent to {email}")
#     except Exception as e:
#         print(f"Failed to send email to {email}: {e}")

# @app.route('/upload', methods=['GET', 'POST'])
# def add_files_to_database():
#     if request.method == 'POST':
#         job_description = request.form['job_description']
#         uploaded_files = request.files.getlist('file')
#         for file in uploaded_files:
#             filename = secure_filename(file.filename)
#             file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(file_path)
#             title = os.path.splitext(filename)[0]
#             content = None
#             if filename.endswith('.pdf'):
#                 content = extract_text_from_pdf(file_path)
#             elif filename.endswith('.docx'):
#                 content = extract_text_from_docx(file_path)
#             if content:
#                 conn = sqlite3.connect('pdf_database.db')
#                 c = conn.cursor()
#                 c.execute('SELECT * FROM documents WHERE title = ?', (title,))
#                 existing_resume = c.fetchone()
#                 if not existing_resume:
#                     c.execute('INSERT INTO documents (title, content) VALUES (?, ?)', (title, content))
#                     conn.commit()
#                 else:
#                     print(f"Resume '{title}' already exists in the database. Skipping insertion.")
#                 conn.close()
#         return redirect(url_for('score', job_description=job_description))

#     return render_template('upload.html')

# def extract_text_from_pdf(pdf_path):
#     try:
#         doc = fitz.open(pdf_path)
#         text = ""
#         for page in doc:
#             text += page.get_text()
#         return text.strip()  # Ensure trailing whitespace is removed
#     except Exception as e:
#         print(f"Error reading {pdf_path}: {e}")
#         return None

# def extract_text_from_docx(docx_path):
#     try:
#         doc = Document(docx_path)
#         text = ""
#         for paragraph in doc.paragraphs:
#             text += paragraph.text + "\n"
#         return text.strip()  # Ensure trailing whitespace is removed
#     except Exception as e:
#         print(f"Error reading {docx_path}: {e}")
#         return None

# @app.route('/score')
# def score():
#     job_description = request.args.get('job_description')
#     if not job_description:
#         return "Job description is missing!", 400
    
#     scores = score_resumes_and_evaluate_candidates(job_description)
#     return render_template('score.html', scores=scores)

# def retrieve_all_resumes():
#     conn = sqlite3.connect('pdf_database.db')
#     c = conn.cursor()
#     c.execute("SELECT * FROM documents")
#     all_resumes = c.fetchall()
#     conn.close()
#     return all_resumes

# def score_resumes_and_evaluate_candidates(job_description):
#     resumes = retrieve_all_resumes()
#     if not resumes:
#         print("No resumes found in the database.")
#         return []

#     tfidf_vectorizer = TfidfVectorizer(stop_words='english')
#     all_texts = [resume[2] for resume in resumes if resume[2] is not None]
    
#     if not all_texts:
#         print("No valid resumes found in the database.")
#         return []

#     tfidf_matrix = tfidf_vectorizer.fit_transform(all_texts)
#     job_desc_vector = tfidf_vectorizer.transform([job_description])

#     scores = []
#     for i, resume in enumerate(resumes):
#         similarity = cosine_similarity(job_desc_vector, tfidf_matrix[i])[0][0] * 100
        
#         name, email = extract_name_and_email(resume[2])
#         print(f"Extracted name: {name}, email: {email}")  # Debug print
        
#         job_desc_tokens = set(token.text.lower() for token in nlp(job_description) if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'])
#         resume_tokens = set(token.text.lower() for token in nlp(resume[2]) if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'])
        
#         matched_skills = job_desc_tokens.intersection(resume_tokens)
        
#         scores.append((name, email, resume[1], similarity, matched_skills))

#     scores.sort(key=lambda x: x[3], reverse=True)
    
#     evaluate_candidates(scores, job_description)

#     return scores

# def extract_name_and_email(content):
#     email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
#     name_pattern = r'\b[A-Z][a-z]*\s[A-Z][a-z]*\b'
    
#     emails = re.findall(email_pattern, content)
#     names = re.findall(name_pattern, content)
    
#     email = emails[0] if emails else None
#     name = names[0] if names else None
    
#     print(f"Extracted email: {email}, name: {name}")  # Debug print
    
#     return name, email

# @app.route('/')
# def index():
#     return redirect(url_for('add_files_to_database'))

# def evaluate_candidates(scores, job_description):
#     threshold_score = 70

#     for score in scores:
#         name, email, title, similarity, matched_skills = score
#         feedback = ""
        
#         if similarity < threshold_score:
#             feedback = generate_rejection_feedback(matched_skills)
#             print(f"Sending rejection email to {email}")  # Debug print
#             send_email(email, "Application Feedback", feedback)
#         else:
#             feedback = generate_acceptance_feedback(matched_skills)
#             print(f"Sending acceptance email to {email}")  # Debug print
#             send_email(email, "Application Feedback", feedback)

# def generate_rejection_feedback(matched_skills):
#     feedback = "Your application did not meet our expectations. Please work on the following areas:"
    
#     if len(matched_skills) == 0:
#         feedback += "\n- None"
#     else:
#         for skill in matched_skills:
#             feedback += f"\n- {skill}"  

#     return feedback

# def generate_acceptance_feedback(matched_skills):
#     feedback = "Congratulations! Your application has been accepted. Here are the skills you excelled in:"
    
#     for skill in matched_skills:
#         feedback += f"\n- {skill}"  

#     return feedback




# if __name__ == '__main__':
#     create_database()
#     if not os.path.exists(UPLOAD_FOLDER):
#         os.makedirs(UPLOAD_FOLDER)
#     app.run(debug=True)

# Mentornship Internship Project #1
# Name: Ayesha Mahmood
# Date:
# import sqlite3
# import fitz  
# import os
# from docx import Document
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# import spacy
# from flask import Flask, render_template, request, redirect, url_for
# from werkzeug.utils import secure_filename
# import re
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

# app = Flask(__name__)

# # Load English language model for spaCy
# nlp = spacy.load("en_core_web_sm")

# # Define stop words as a list
# stop_words = list(spacy.lang.en.stop_words.STOP_WORDS)
# # Add tokenized versions of certain stop words to avoid preprocessing warnings
# additional_stop_words = ["'ll", "'ve"]
# stop_words.extend(additional_stop_words)

# # Define the folder where uploaded files will be stored
# UPLOAD_FOLDER = '/Users/ayeshamahmood/Downloads/resume internship'
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# # Function to create the database file named "pdf_database.db" and table
# def create_database():
#     conn = sqlite3.connect('pdf_database.db')
#     c = conn.cursor()
#     c.execute('''
#         CREATE TABLE IF NOT EXISTS documents (
#             id INTEGER PRIMARY KEY,
#             title TEXT,
#             content TEXT
#         )
#     ''')
#     conn.commit()
#     conn.close()

# # Function to extract text from a PDF file
# def extract_text_from_pdf(pdf_path):
#     try:
#         doc = fitz.open(pdf_path)
#         text = ""
#         for page in doc:
#             text += page.get_text()
#         return text if text.strip() else None
#     except Exception as e:
#         print(f"Error reading {pdf_path}: {e}")
#         return None

# # Function to extract text from a DOCX file
# def extract_text_from_docx(docx_path):
#     try:
#         doc = Document(docx_path)
#         text = ""
#         for paragraph in doc.paragraphs:
#             text += paragraph.text + "\n"
#         return text if text.strip() else None
#     except Exception as e:
#         print(f"Error reading {docx_path}: {e}")
#         return None

# # Function to extract name and email from content
# def extract_name_and_email(content):
#     # Regular expression pattern to match email addresses
#     email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
#     # Regular expression pattern to match name
#     name_pattern = r'\b[A-Z][a-z]*\s[A-Z][a-z]*\b'  # Assumes name format: Firstname Lastname
    
#     # Search for email addresses and names in the content
#     emails = re.findall(email_pattern, content)
#     names = re.findall(name_pattern, content)
    
#     # If multiple emails are found, choose the first one
#     email = emails[0] if emails else None
    
#     # If multiple names are found, choose the first one
#     name = names[0] if names else None
    
#     return name, email

# # Function to send email
# def send_email(email, status):
#     # Set up the SMTP server
#     smtp_server = 'in-v3.mailjet.com'  # Use the provided SMTP server address
#     smtp_port = 465  # Use the provided SMTP port, 587 for TLS or 465 for SSL
#     sender_email = 'mahmoodayesha612@gmail.com'  # Use your email account associated with the service
#     api_key = 'cf2630380680877016975026f2449df8'  # Use your API key as the password
    
#     # Create a multipart message and set headers
#     message = MIMEMultipart()
#     message["From"] = sender_email
#     message["To"] = email
    
#     if status == 'accepted':
#         message["Subject"] = "Application Accepted"
#         body = "Congratulations! Your application has been accepted."
#     elif status == 'rejected':
#         message["Subject"] = "Application Rejected"
#         body = "We regret to inform you that your application has been rejected."
#     else:
#         return  # Invalid status
    
#     # Add body to email
#     message.attach(MIMEText(body, "plain"))
    
#     # Send the email
#     try:
#         server = smtplib.SMTP(smtp_server, smtp_port)
#         server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
#         server.login(sender_email, api_key)
#         server.send_message(message)
#         server.quit()
#         print("Email sent successfully")
#     except smtplib.SMTPAuthenticationError as e:
#         print(f"Failed to authenticate: {e}")
#     except Exception as e:
#         print(f"Failed to send email: {e}")

    
# # Route to handle the form submission
# @app.route('/upload', methods=['GET', 'POST'])
# def add_files_to_database():
#     if request.method == 'POST':
#         job_description = request.form['job_description']
#         uploaded_files = request.files.getlist('file')
#         for file in uploaded_files:
#             filename = secure_filename(file.filename)
#             file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(file_path)
#             title = os.path.splitext(filename)[0]
#             content = None
#             if filename.endswith('.pdf'):
#                 content = extract_text_from_pdf(file_path)
#             elif filename.endswith('.docx'):
#                 content = extract_text_from_docx(file_path)
#             if content:
#                 conn = sqlite3.connect('pdf_database.db')
#                 c = conn.cursor()
#                 c.execute('SELECT * FROM documents WHERE title = ?', (title,))
#                 existing_resume = c.fetchone()
#                 if not existing_resume:
#                     c.execute('INSERT INTO documents (title, content) VALUES (?, ?)', (title, content))
#                     conn.commit()
#                     conn.close()
#                 else:
#                     print(f"Resume '{title}' already exists in the database. Skipping insertion.")
#         # Redirect to the score route after uploading files
#         return redirect(url_for('score', job_description=job_description))

#     return render_template('upload.html')

# @app.route('/score')
# def score():
#     job_description = request.args.get('job_description')
#     if not job_description:
#         return "Job description is missing!", 400
    
#     scores = score_resumes(job_description)
#     return render_template('score.html', scores=scores)

# @app.route('/')
# def index():
#     return redirect(url_for('add_files_to_database'))

# # Function to retrieve all resumes from the database
# def retrieve_all_resumes():
#     conn = sqlite3.connect('pdf_database.db')
#     c = conn.cursor()
#     c.execute("SELECT * FROM documents")
#     all_resumes = c.fetchall()
#     conn.close()
#     return all_resumes

# def score_resumes(job_description):
#     resumes = retrieve_all_resumes()
#     if not resumes:
#         print("No resumes found in the database.")
#         return []

#     tfidf_vectorizer = TfidfVectorizer(stop_words='english')
#     all_texts = [resume[2] for resume in resumes if resume[2] is not None]
    
#     if not all_texts:
#         print("No valid resumes found in the database.")
#         return []

#     tfidf_matrix = tfidf_vectorizer.fit_transform(all_texts)
#     job_desc_vector = tfidf_vectorizer.transform([job_description])

#     scores = []
#     for i, resume in enumerate(resumes):
#         similarity = cosine_similarity(job_desc_vector, tfidf_matrix[i])[0][0] * 100
        
#         # Extract name and email from resume content
#         name, email = extract_name_and_email(resume[2])  
        
#         job_desc_tokens = set(token.text.lower() for token in nlp(job_description) if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'])
#         resume_tokens = set(token.text.lower() for token in nlp(resume[2]) if not token.is_stop and token.pos_ in ['NOUN', 'PROPN'])
        
#         matched_skills = job_desc_tokens.intersection(resume_tokens)
        
#         scores.append((name, email, resume[1], similarity, matched_skills))

#     # Sort the scores from highest to lowest percentage
#     scores.sort(key=lambda x: x[3], reverse=True)
    
#     # Send emails based on the scores
#     for score in scores:
#         if score[3] < 70:
#             send_email(score[1], 'rejected')
#         else:
#             send_email(score[1], 'accepted')

#     return scores



# if __name__ == "__main__":
#     create_database()
#     app.run(debug=True)