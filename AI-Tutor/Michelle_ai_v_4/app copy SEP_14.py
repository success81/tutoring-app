from flask import Flask, render_template, request, redirect, url_for, jsonify
from markupsafe import Markup
import json
import requests
import os
import random
import logging
import string
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Get the absolute path to the directory containing this script
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SOCIAL_SKILLS_PROMPT = """You are a patient, friendly, and knowledgeable Social Skills Coach AI for a student named Michelle. Your task is to guide Michelle through the specific social scenario provided in the question. Do not create new scenarios. Instead, focus on coaching Michelle through the given situation. Follow these guidelines:

1. Begin by acknowledging the scenario presented in the question.
2. Guide Michelle through the scenario step-by-step, offering advice and asking her to reflect on her approach.
3. Provide constructive feedback, praise, and actionable tips based on Michelle's responses.
4. Encourage Michelle to think about different aspects of the social interaction, such as:
   - How to show interest in the conversation even if the topic doesn't excite her
   - Ways to find common ground or redirect the conversation politely
   - Non-verbal cues and body language to maintain a friendly demeanor
5. If Michelle struggles, offer gentle support and alternative strategies.
6. Throughout the interaction, provide:
   - Specific praise for good social skills demonstrated
   - Constructive feedback for areas of improvement
   - Actionable tips that Michelle can apply in similar real-life situations
7. Ask guiding questions to help Michelle reflect on the interaction and her approach.
8. Wrap up the session with a summary of key takeaways and encourage Michelle to practice the skills discussed.

Maintain a patient, supportive, and positive tone throughout the session, ensuring Michelle feels comfortable and confident as she improves her social skills. Adapt your coaching style based on her needs and responses, always focusing on the specific scenario provided."""

GENERAL_TUTOR_PROMPT = """You are a patient and knowledgeable tutor for Michelle. Your goal is to guide her through learning and problem-solving without giving away answers too quickly. Follow these guidelines:

1. Always address Michelle by name and maintain a friendly, encouraging tone.
2. Begin by assessing Michelle's current understanding of the topic or problem.
3. Break down complex ideas or problems into smaller, manageable steps.
4. Ask guiding questions to lead Michelle towards understanding, rather than providing direct answers.
5. Encourage Michelle to think and reason on her own before offering additional help.
6. Provide constructive feedback and gentle correction when needed.
7. Use analogies or real-world examples to illustrate abstract concepts.
8. Frequently check for understanding throughout the tutoring session.
9. Offer praise for effort and correct reasoning to boost confidence.
10. If Michelle struggles, provide hints or break down the problem further, but avoid giving the full solution.
11. Ask Michelle to explain her thought process and reasoning at each step.
12. Be prepared to explain concepts in different ways if Michelle doesn't understand at first.

Remember to maintain a supportive and encouraging tone throughout the interaction. Adjust your teaching style based on Michelle's responses and level of understanding. Your goal is to help Michelle develop problem-solving skills and confidence in her abilities."""

READING_PROMPT = """You are a helpful reading tutor for Michelle. Your task is to guide her through understanding and analyzing the text she has read. The text includes a question at the end that Michelle needs to answer. Follow these guidelines:

1. Start by asking Michelle about the main ideas, characters, plot, or themes of the text.
2. Encourage her to think critically and provide explanations for her answers.
3. Guide her towards answering the question at the end of the text through a series of smaller, guiding questions.
4. Offer guidance and clarification when needed, but allow Michelle to develop her own interpretations and insights.
5. If Michelle struggles, provide hints or break down the question into smaller parts.
6. Ask Michelle to support her answers with evidence from the text.
7. Encourage Michelle to make connections between different parts of the text or to her own experiences.
8. Praise Michelle's efforts and good observations throughout the discussion.

Remember, your goal is to help Michelle understand the text and answer the final question while developing her critical reading and analysis skills."""

GREETINGS = [
    "Hello Michelle! I'm your AI tutor. Are you ready to get started?",
    "Hi Michelle! Excited to help you learn today. Shall we begin?",
    "Welcome, Michelle! I'm here to assist you. Ready for today's session?",
    "Greetings, Michelle! Let's dive into some learning. Are you prepared?",
    "Hey there, Michelle! Looking forward to our tutoring session. Ready to go?",
    "Good to see you, Michelle! Eager to help you learn. Shall we start?",
    "Hi Michelle! Hope you're having a great day. Ready to expand your knowledge?",
    "Hello Michelle! I'm your friendly AI tutor. Prepared for some learning?",
    "Welcome back, Michelle! Excited for another tutoring session. Ready to begin?",
    "Hey Michelle! Great to have you here. Shall we kick off our lesson?",
    "Greetings, Michelle! I'm here to support your learning journey. Ready to start?",
    "Hi there, Michelle! Excited to explore new concepts with you. Shall we?",
    "Hello Michelle! Looking forward to our tutoring session. Are you set?",
    "Welcome, Michelle! I'm your AI learning companion. Ready to dive in?",
    "Hey Michelle! Glad you're here for some learning. Prepared to begin?",
    "Greetings, Michelle! Let's make this a great tutoring session. Ready?",
    "Hi Michelle! Excited to help you grow your knowledge. Shall we start?",
    "Hello there, Michelle! I'm here to guide your learning. Ready to go?",
    "Welcome aboard, Michelle! Let's embark on this learning journey. Prepared?",
    "Hey Michelle! Looking forward to our productive session. Ready to begin?"
]

def load_question(topic, question_number):
    file_path = os.path.join(BASE_DIR, 'questions', f"{topic}.txt")
    app.logger.debug(f"Attempting to load question from file: {file_path}")
    
    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            questions = content.split('@')[1:]  # Split by '@' and remove the first empty element
            if question_number <= len(questions):
                return questions[question_number - 1].strip()
            else:
                app.logger.warning(f"Question number {question_number} not found in {file_path}")
                return None
    except Exception as e:
        app.logger.error(f"Error reading file {file_path}: {str(e)}")
        return None

def basic_prompt(ai_pass, model="gemma2:27b"):
    ai_prompt = ai_pass
    url = 'http://localhost:11434/api/generate'
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": model,
        "prompt": ai_prompt,
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        local_output = response.text
        formatted_local_output = get_response_from_api_text(local_output)
        return formatted_local_output
    except requests.RequestException as e:
        app.logger.error(f"Error in API request: {str(e)}")
        return "I'm sorry, I'm having trouble connecting to my knowledge base right now. Can we try again in a moment?"

def get_response_from_api_text(api_response):
    try:
        response_dict = json.loads(api_response)
        response = response_dict.get('response', '').replace('Human:', '').replace('AI:', '').strip()
        return Markup(response)
    except json.JSONDecodeError:
        app.logger.error("Failed to decode API response")
        return Markup("I'm sorry, I received an unexpected response. Can you please try again?")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        topic = request.form['topic']
        if topic == 'free':
            return redirect(url_for('tutor', topic='free'))
        question_number = int(request.form['question_number'])
        question = load_question(topic, question_number)
        if question:
            return redirect(url_for('tutor', topic=topic, question=question))
        else:
            error = f"Question not found for topic '{topic}' and number {question_number}. Please try again."
            return render_template('index.html', error=error)
    return render_template('index.html')

@app.route('/tutor')
def tutor():
    topic = request.args.get('topic')
    question = request.args.get('question')
    greeting = random.choice(GREETINGS)
    
    if topic == 'social':
        context = f"{SOCIAL_SKILLS_PROMPT}\n\nCurrent scenario: {question}\n"
    elif topic == 'reading':
        context = f"{READING_PROMPT}\n\nMichelle has just finished reading the following text: {question}\n"
    elif topic == 'free':
        context = f"{GENERAL_TUTOR_PROMPT}\n\nHey Michelle, ask me a question on any topic!"
    else:
        context = f"{GENERAL_TUTOR_PROMPT}\n\nCurrent question: {question}\n"
    
    display_question = "Reading Activity" if topic == 'reading' else (question if question else "Free Topic Discussion")
    
    return render_template('tutor.html', topic=topic, question=display_question, greeting=greeting, context=context)

@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    user_input = request.json['user_input']
    context = request.json['context']
    topic = request.json.get('topic', '')

    if topic == 'math':
        # First, get the math solution from the qwen2-math model
        math_prompt = f"Solve this math problem and provide a detailed breakdown of the solution: {user_input}"
        math_solution = basic_prompt(math_prompt, model="qwen2-math")

        # Then, prepare the prompt for the general model
        full_prompt = f"{context}\nHuman: {user_input}\nMath Solution: {math_solution}\nAI: Based on the provided math solution, guide Michelle through the problem-solving process. Ask a single guiding question or provide a hint to encourage her to think through the next step. Do not provide the full solution."
    else:
        full_prompt = f"{context}\nHuman: {user_input}\nAI: Respond to Michelle's input with a single thoughtful comment or question to guide the conversation. Do not answer your own questions or continue the conversation without waiting for Michelle's response."

    ai_response = basic_prompt(full_prompt)
    return jsonify({"response": ai_response})

@app.route('/submit_for_evaluation', methods=['POST'])
def submit_for_evaluation():
    conversation = request.json['conversation']
    topic = request.json['topic']
    question_number = request.json['question_number']

    # Generate prompts for evaluation
    evaluation_prompt = f"""Evaluate the following tutoring session with Michelle. Focus primarily on Michelle's responses and learning progress. Provide:

1. Assessment of Michelle's Performance:
   - Identify potential weaknesses in Michelle's understanding or approach.
   - Highlight strong areas in Michelle's responses or problem-solving skills.
   - Point out areas that can be strengthened in Michelle's learning or communication.

2. Tips for Improvement:
   - Provide specific, actionable tips that Michelle could use to improve her understanding or skills.
   - Ensure these tips are appropriate for a 6th-grade level student.

3. Similar Problems:
   - Generate two similar problems related to the topic discussed.
   - Provide step-by-step solutions for these problems.
   - Ensure the problems and solutions are appropriate for a 6th-grade level.

Tutoring Session:
{conversation}

Please format your response with clear headings for each section."""

    # Get response from the phi3.5 model
    evaluation = basic_prompt(evaluation_prompt, model="phi3.5")

    # Generate random 3 characters
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

    # Create the output file
    filename = f"{question_number}_{topic}_{random_chars}.pdf"
    output_path = os.path.join(BASE_DIR, 'answers', filename)

    # Generate PDF
    generate_pdf(output_path, conversation, evaluation)

    return jsonify({"message": "Evaluation submitted successfully", "filename": filename})

def generate_pdf(output_path, conversation, evaluation):
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=14, leading=18))

    # Create the content for the PDF
    content = []

    # Title
    content.append(Paragraph("Tutoring Session Evaluation", styles['Title']))
    content.append(Spacer(1, 24))

    # Original Conversation
    content.append(Paragraph("Original Conversation", styles['Heading2']))
    content.append(Spacer(1, 6))
    conversation_lines = conversation.split('\n')
    for line in conversation_lines:
        if line.strip():
            content.append(Paragraph(line, styles['Justify']))
            content.append(Spacer(1, 4))
    content.append(Spacer(1, 12))

    # Evaluation
    content.append(Paragraph("Evaluation", styles['Heading2']))
    content.append(Spacer(1, 6))
    evaluation_lines = evaluation.split('\n')
    current_heading = None
    for line in evaluation_lines:
        if line.strip():
            if line.strip().endswith(':'):
                current_heading = line.strip()
                content.append(Paragraph(f"<u><b>{current_heading}</b></u>", styles['Heading3']))
            else:
                content.append(Paragraph(line, styles['Justify']))
            content.append(Spacer(1, 4))

    # Build the PDF
    try:
        doc.build(content)
    except Exception as e:
        app.logger.error(f"Error generating PDF: {str(e)}")
        # If PDF generation fails, create a simple text file instead
        with open(output_path.replace('.pdf', '.txt'), 'w') as f:
            f.write("Original Conversation:\n\n")
            f.write(conversation)
            f.write("\n\nEvaluation:\n\n")
            f.write(evaluation)

if __name__ == '__main__':
    app.run(debug=True)