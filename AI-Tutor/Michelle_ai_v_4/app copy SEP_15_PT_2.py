import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from markupsafe import Markup
import json
import requests
import os
import logging
import string
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# Assume MOTIVATIONAL_QUOTES is imported from a separate file
from motivational_quotes import MOTIVATIONAL_QUOTES

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Get the absolute path to the directory containing this script
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Add a global variable to track the number of AI interactions
social_skills_interaction_count = 0

# Constants (SOCIAL_SKILLS_PROMPT, GENERAL_TUTOR_PROMPT, READING_PROMPT)
SOCIAL_SKILLS_PROMPT = """You are a patient, friendly, and knowledgeable Social Skills Coach AI for a student named Michelle. Always address Michelle by her first name to create a personal and engaging interaction. Your task is to guide Michelle through the specific social scenario provided in the question. Do not create new scenarios. Instead, focus on coaching Michelle through the given situation. Follow these guidelines:

1. **Personalized Greeting:** Start each interaction by greeting Michelle by name, using a variety of friendly greetings. For example, "Hey there, Michelle! Ready to tackle some social skills today?" or "Michelle, my friend! How are you feeling about our session today?"

# ... (rest of the SOCIAL_SKILLS_PROMPT)

Maintain a patient, supportive, and positive tone throughout the session, ensuring Michelle feels comfortable and confident as she improves her social skills. Adapt your coaching style based on her needs and responses, always focusing on the specific scenario provided."""

GENERAL_TUTOR_PROMPT = """You are a patient and knowledgeable tutor for Michelle. Always address Michelle by her first name to create a personal and engaging interaction. Your goal is to guide her through learning and problem-solving without giving away answers too quickly. Follow these guidelines:

1. **Personalized Greeting:** Start each session by greeting Michelle by name, using a variety of friendly greetings. For example, "Hi Michelle! Ready to dive into some exciting learning?" or "Michelle, my star student! How are you feeling about today's topic?"

# ... (rest of the GENERAL_TUTOR_PROMPT)

Remember, your goal is to help Michelle develop problem-solving skills and confidence in her abilities. Adjust your teaching style based on Michelle's responses and level of understanding to ensure an effective and encouraging learning experience."""

READING_PROMPT = """You are a helpful reading tutor for Michelle. Always address Michelle by her first name to create a personal and engaging interaction. Your task is to guide her through understanding and analyzing the text she has read. The text includes a question at the end that Michelle needs to answer. Follow these guidelines:

1. **Personalized Greeting:** Start each session by greeting Michelle by name, using a variety of friendly greetings. For example, "Hello, Michelle! Ready to explore an exciting new text?" or "Michelle, my bookworm buddy! How are you feeling about today's reading adventure?"

# ... (rest of the READING_PROMPT)

Remember, your goal is to help Michelle understand the text and answer the final question while developing her critical reading and analysis skills. Maintain a supportive and encouraging tone throughout the interaction."""

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

def basic_prompt(ai_pass, model="gemma2:9b"):
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
        return "I'm sorry, Michelle, I'm having trouble connecting to my knowledge base right now. Can we try again in a moment?"

def get_response_from_api_text(api_response):
    try:
        response_dict = json.loads(api_response)
        response = response_dict.get('response', '').replace('Human:', '').replace('AI:', '').strip()
        return Markup(response)
    except json.JSONDecodeError:
        app.logger.error("Failed to decode API response")
        return Markup("I'm sorry, Michelle, I received an unexpected response. Can you please try again?")
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        topic = request.form['topic']
        if topic == 'free':
            return redirect(url_for('tutor', topic='free'))
        question_number = request.form.get('question_number')
        if question_number:
            try:
                question_number = int(question_number)
            except ValueError:
                error = "Invalid question number. Please enter a valid number."
                return render_template('index.html', error=error)
        else:
            error = "Question number is required."
            return render_template('index.html', error=error)
        
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

    if topic == 'social':
        context = f"{SOCIAL_SKILLS_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{question}]\nCurrent scenario: {question}\n"
    elif topic == 'reading':
        context = f"{READING_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{question}]\nMichelle has just finished reading the following text: {question}\n"
    elif topic == 'math':
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{question}]\nCurrent math problem: {question}\n"
    elif topic == 'free':
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}]\nHey Michelle, ask me a question on any topic!"
    elif topic == 'english':
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{question}]\nCurrent English topic: {question}\n"
    else:
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{question}]\nCurrent question: {question}\n"

    display_question = ""
    if topic == 'reading':
        display_question = "Reading Activity"
    elif topic == 'free':
        display_question = "Free Topic Discussion"
    elif topic == 'english':
        display_question = f"English Topic: {question}"
    else:
        display_question = question if question else "Discussion"

    greeting = "Hello Michelle! I'm here to help you with your studies."

    return render_template('tutor.html', topic=topic, question=display_question, context=context, greeting=greeting)

@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    global social_skills_interaction_count
    user_input = request.json.get('user_input', '').strip()
    context = request.json.get('context', '').strip()

    # Extract topic and question from context
    topic_marker = '[TOPIC:'
    question_marker = '[QUESTION:'
    topic = ''
    question = ''
    if topic_marker in context:
        try:
            topic_start = context.index(topic_marker) + len(topic_marker)
            topic_end = context.index(']', topic_start)
            topic = context[topic_start:topic_end]
        except ValueError:
            app.logger.error("Topic marker not found or malformed in context.")

    if question_marker in context:
        try:
            question_start = context.index(question_marker) + len(question_marker)
            question_end = context.index(']', question_start)
            question = context[question_start:question_end]
        except ValueError:
            app.logger.error("Question marker not found or malformed in context.")

    # Select a random motivational quote
    random_quote = random.choice(MOTIVATIONAL_QUOTES)

    if topic == 'social':
        social_skills_interaction_count += 1

        if social_skills_interaction_count >= 15:
            full_prompt = f"""{context}
Human: {user_input}
AI: This is the 15th interaction. Provide a brief, encouraging summary of Michelle's progress in this session. Then, clearly state that the session is complete and instruct Michelle to hit the reset button if she wants to practice again. Your response should be friendly and supportive. Incorporate this motivational quote if possible: "{random_quote}"
"""
        else:
            full_prompt = f"""{context}

H: {user_input}
AI: Respond to Michelle's input with a focus on the social skills scenario. Ensure you refer to her by name, ask more questions to understand her perspective, engage in role-playing to enhance the learning experience, provide actionable advice and heavy clues, and maintain an encouraging and positive tone. If it fits naturally, incorporate this motivational quote: "{random_quote}"
"""

        ai_response = basic_prompt(full_prompt)

        return jsonify({
            "response": ai_response,
            "interaction_count": social_skills_interaction_count,
            "session_complete": social_skills_interaction_count >= 15
        })

    elif topic == 'math':
        # Step 1: Use qwen2-math to get the solution
        solution_prompt = f"Solve the following math problem and provide a detailed step-by-step solution:\n\n{question}\n"
        solution = basic_prompt(solution_prompt, model="qwen2-math")

        # Step 2: Construct the prompt for gemma2
        full_prompt = f"""{context}

Here is a detailed solution to the problem:

{solution}

Now, using this solution, respond to Michelle's input accordingly. Prioritize the answer provided, but continue to tutor her by guiding through the problem without giving away the answer immediately. Provide additional advice and guidance to help her understand the concepts better. If it fits naturally, incorporate this motivational quote: "{random_quote}"

H: {user_input}
AI:"""

        # Step 3: Get the response from gemma2
        ai_response = basic_prompt(full_prompt, model="gemma2:9b")
        return jsonify({"response": ai_response})

    else:
        # Handle other topics (including English, reading, and free topics)
        full_prompt = f"""{context}
Human: {user_input}
AI: Respond to Michelle's input accordingly. Always address her by name, maintain a positive and encouraging tone, provide constructive feedback, and offer advice and guidance to help her explore the topic effectively. If it fits naturally, incorporate this motivational quote: "{random_quote}"
"""
        ai_response = basic_prompt(full_prompt)
        return jsonify({"response": ai_response})
@app.route('/submit_for_evaluation', methods=['POST'])
def submit_for_evaluation():
    conversation = request.json.get('conversation', '').strip()
    topic = request.json.get('topic', '').strip()
    question_number = request.json.get('question_number', '').strip()

    if not conversation or not topic or not question_number:
        return jsonify({"message": "Invalid submission. Please provide all required fields."}), 400

    # Generate prompts for evaluation
    evaluation_prompt = f"""Evaluate the following tutoring session with Michelle. Focus primarily on Michelle's responses and learning progress. Provide:

1. **Assessment of Michelle's Performance:**
   - Identify potential weaknesses in Michelle's understanding or approach.
   - Highlight strong areas in Michelle's responses or problem-solving skills.
   - Point out areas that can be strengthened in Michelle's learning or communication.

2. **Tips for Improvement:**
   - Provide specific, actionable tips that Michelle could use to improve her understanding or skills.
   - Ensure these tips are appropriate for a 6th-grade level student.

**Tutoring Session:**
{conversation}

Please format your response with clear headings for each section."""

    # Get response from the gemma2:9b model
    evaluation = basic_prompt(evaluation_prompt, model="gemma2:9b")

    # Generate random 3 characters
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

    # Create the output file
    filename = f"{question_number}_{topic}_{random_chars}.pdf"
    output_path = os.path.join(BASE_DIR, 'answers', filename)

    # Ensure the 'answers' directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

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
    doc.build(content)

if __name__ == '__main__':
    app.run(debug=True)
