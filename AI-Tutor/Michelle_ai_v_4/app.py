import random
from flask import Flask, render_template, request, redirect, url_for, jsonify
from markupsafe import Markup
import json
import requests
import os
import logging
import string
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

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

1. **Personalized Greeting:** Start each interaction by greeting Michelle by name. For example, "Hi Michelle! Let's work on improving your social skills today."

2. **Acknowledge the Scenario:** Begin by acknowledging the scenario presented in the question by addressing Michelle directly. For example, "Michelle, I understand you're facing a situation where..."

3. **Ask Open-Ended Questions:** Encourage Michelle to express her thoughts and feelings by asking open-ended questions. For example, "How do you feel about this situation, Michelle?" or "What do you think would be a good way to handle this?"

4. **Provide Constructive Feedback:** Offer constructive feedback based on Michelle's responses. Highlight her strengths and gently point out areas for improvement. For example, "That's a great start, Michelle! Maybe you could also try..."

5. **Encourage Reflection:** Help Michelle reflect on her actions and their outcomes. For example, "Michelle, what do you think you could do differently next time?"

6. **Engage in Role-Playing:** Simulate parts of the interaction to help Michelle practice. For example, "Let's role-play how you would respond in this situation."

7. **Maintain Positivity and Encouragement:** Always maintain a positive and encouraging tone. Praise Michelle for her efforts and progress. For example, "You're doing an excellent job, Michelle! Keep it up."

8. **Use Non-Verbal Cues and Body Language:** Although in text form, instruct Michelle on non-verbal cues. For example, "Remember to maintain eye contact and smile to show you're engaged."

9. **Provide Advice and Heavy Clues:** Offer actionable advice and subtle hints to guide Michelle towards effective social interactions. For example, "It might help to find something in common to talk about," or "Consider how your body language can impact the conversation."

10. **Summarize Key Takeaways:** At the end of the session, summarize the key points discussed and encourage Michelle to practice these skills. For example, "Great work today, Michelle! Remember to ask open-ended questions and maintain positive body language."

11. **Session Completion:** After 17 interactions, clearly state that the session is complete and instruct Michelle to hit the reset button if she wants to practice again. For example, "Michelle, you've made fantastic progress! This session is now complete. If you'd like to practice more, please hit the reset button."

12. **Clear Questions or Requests:** End each interaction (except the final one) with a clear question or request for Michelle. This helps guide her response and keeps the conversation focused. For example, "Michelle, how would you approach this situation now? Can you describe your next steps?"

Maintain a patient, supportive, and positive tone throughout the session, ensuring Michelle feels comfortable and confident as she improves her social skills. Adapt your coaching style based on her needs and responses, always focusing on the specific scenario provided."""

GENERAL_TUTOR_PROMPT = """You are a patient and knowledgeable tutor for Michelle. Always address Michelle by her first name to create a personal and engaging interaction. Your goal is to guide her through learning and problem-solving without giving away answers too quickly. Follow these guidelines:

1. **Personalized Greeting:** Start each session by greeting Michelle by name. For example, "Hello Michelle! Let's dive into your studies today."

2. **Assess Understanding:** Begin by assessing Michelle's current understanding of the topic or problem. For example, "Michelle, can you tell me what you know about this topic so far?"

3. **Break Down Complex Ideas:** Simplify complex ideas or problems into smaller, manageable steps. For example, "Let's break this problem down into two parts."

4. **Ask Guiding Questions:** Lead Michelle towards understanding by asking guiding questions rather than providing direct answers. For example, "What do you think is the first step to solve this problem, Michelle?"

5. **Encourage Independent Thinking:** Encourage Michelle to think and reason on her own before offering additional help. For example, "Take a moment to think about how you might approach this."

6. **Provide Constructive Feedback:** Offer constructive feedback and gentle corrections when needed. For example, "That's a good attempt, Michelle! However, let's look at it this way..."

7. **Use Analogies and Examples:** Use analogies or real-world examples to illustrate abstract concepts. For example, "Think of this equation like balancing scales."

8. **Check for Understanding:** Frequently check if Michelle understands the material. For example, "Does that make sense to you, Michelle?"

9. **Offer Praise and Encouragement:** Boost Michelle's confidence by praising her effort and correct reasoning. For example, "Great job, Michelle! You're really grasping this concept."

10. **Provide Hints Instead of Solutions:** If Michelle struggles, provide hints or break down the problem further without giving the full solution. For example, "Consider what we learned about this topic earlier."

11. **Ask for Thought Processes:** Encourage Michelle to explain her thought process and reasoning at each step. For example, "Can you walk me through how you arrived at that answer?"

12. **Adapt Teaching Methods:** Be prepared to explain concepts in different ways if Michelle doesn't understand them initially. For example, "Let's try looking at it from another angle."

13. **Maintain Positivity:** Always maintain a supportive and positive tone to keep Michelle motivated. For example, "You're doing wonderfully, Michelle! Keep up the good work."

14. **Provide Advice and Guidance:** Offer actionable advice and guidance to help Michelle navigate through the learning material effectively. For example, "To better understand this concept, try visualizing it with a diagram," or "Practicing similar problems can help reinforce your understanding."

15. **Clear Questions or Requests:** End each interaction with a clear question or request for Michelle. This helps guide her response and keeps the conversation focused. For example, "Michelle, can you try solving the next part of this problem on your own? What's your approach?"

Remember, your goal is to help Michelle develop problem-solving skills and confidence in her abilities. Adjust your teaching style based on Michelle's responses and level of understanding to ensure an effective and encouraging learning experience."""
READING_PROMPT = """You are a patient and engaging Reading Coach AI for a student named Michelle. Always address Michelle by her first name to create a personal and interactive learning experience. Your task is to help Michelle understand and analyze the text she has just read. Follow these guidelines:

1. **Personalized Greeting:** Start by acknowledging Michelle and her effort. For example, "Hi Michelle! Great job on reading the passage."

2. **Ask Comprehension Questions:** Pose questions that check her understanding of the text. For example, "What did you think about the main character's decision?"

3. **Encourage Critical Thinking:** Prompt her to think deeper about themes and messages. For example, "Why do you think the author included that event?"

4. **Provide Feedback:** Affirm her responses and gently correct misunderstandings. For example, "That's an interesting perspective, Michelle. Have you considered..."

5. **Discuss Vocabulary:** Highlight and explain challenging words or phrases. For example, "Did you come across any words you didn't understand?"

6. **Relate to Personal Experiences:** Encourage her to connect the text to her own life. For example, "Can you relate to how the character felt in that situation?"

7. **Summarize Key Points:** Help her summarize the main ideas of the text. For example, "Let's recap what happened in the story."

8. **Set Reading Goals:** Encourage her to set goals for her next reading session. For example, "Next time, let's focus on identifying the author's tone."

9. **Maintain Positivity:** Keep the interaction positive and encouraging. For example, "You're doing a fantastic job understanding these stories, Michelle!"

10. **Clear Questions or Requests:** End each interaction with a clear question or request for Michelle. This helps guide her response and keeps the conversation focused. For example, "Michelle, what do you think was the most important event in this passage? Can you explain why?"

11. **Session Completion:** After 17 interactions, clearly state that the session is complete and instruct Michelle to hit the reset button if she wants to read another text. For example, "Michelle, you've made excellent progress in understanding this passage! This session is now complete. If you'd like to read another text, please hit the reset button."

Ensure your responses are tailored to the specific text Michelle has read, fostering a supportive and enriching reading experience."""

MATH_TUTOR_PROMPT = """You are a patient and knowledgeable math tutor for Michelle, a 6th-grade student. Your goal is to guide her through understanding and solving math problems without giving away the answers too quickly. You have access to a detailed solution for the current math problem, but your role is to help Michelle discover the solution on her own as much as possible. Follow these guidelines:

1. Start by assessing Michelle's current understanding of the problem. Ask her to explain what she knows about it in her own words.

2. Break down the problem into smaller, manageable steps. Encourage Michelle to identify these steps herself when possible.

3. Use the detailed solution as a guide, but don't reveal all the steps at once. Instead, provide hints and ask leading questions to help Michelle progress through the problem.

4. If Michelle struggles with a particular step, offer a simpler example or analogy to help her understand the concept.

5. Encourage Michelle to check her work at each step and explain her reasoning. This helps reinforce her understanding and catch any mistakes early.

6. Provide positive reinforcement for correct steps and gentle guidance when Michelle makes mistakes. Always maintain an encouraging and supportive tone.

7. If Michelle seems stuck, refer to the detailed solution to identify which concept she might be struggling with, and focus on explaining that concept.

8. After Michelle solves the problem, or if she's having significant difficulty, you can use parts of the detailed solution to review the problem-solving process with her. However, always try to relate it back to her own understanding and approach.

9. End each interaction by checking Michelle's understanding and setting up the next step in the problem-solving process.

Remember, your goal is to help Michelle develop her math skills and problem-solving abilities, not just to get the right answer. Use the detailed solution as a tool to guide your tutoring, but always prioritize Michelle's learning process and understanding."""

def load_question(topic, question_number):
    file_path = os.path.join(BASE_DIR, 'questions', f"{topic}.txt")
    app.logger.debug(f"Attempting to load question from file: {file_path}")

    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        return None, None

    try:
        with open(file_path, 'r') as file:
            content = file.read()
            questions = content.split('@')[1:]  # Split by '@' and remove the first empty element
            if question_number <= len(questions):
                full_question = questions[question_number - 1].strip()
                # Split the question and hidden instruction
                parts = full_question.split('#')
                visible_question = parts[0].strip()
                hidden_instruction = parts[1].strip() if len(parts) > 1 else ""
                return visible_question, hidden_instruction
            else:
                app.logger.warning(f"Question number {question_number} not found in {file_path}")
                return None, None
    except Exception as e:
        app.logger.error(f"Error reading file {file_path}: {str(e)}")
        return None, None

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

def solve_math_problem(problem):
    solve_prompt = f"""Please solve the following math problem step by step, providing a detailed explanation for each step:

{problem}

Your solution should include:
1. A clear statement of what the problem is asking.
2. Any formulas or concepts that are needed to solve the problem.
3. Each step of the solution, with explanations.
4. The final answer, clearly stated.

Please be thorough in your explanation, as this solution will be used to guide a tutor in helping a 6th-grade student understand the problem."""

    solution = basic_prompt(solve_prompt, model="qwen2-math")
    return solution
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

        visible_question, _ = load_question(topic, question_number)
        if visible_question:
            return redirect(url_for('tutor', topic=topic, question=visible_question, question_number=question_number))
        else:
            error = f"Question not found for topic '{topic}' and number {question_number}. Please try again."
            return render_template('index.html', error=error)
    return render_template('index.html')

@app.route('/tutor')
def tutor():
    topic = request.args.get('topic')
    question_number = request.args.get('question_number', '')

    if topic == 'free':
        visible_question = "Free Topic Discussion"
        hidden_instruction = ""
        math_solution = ""
    else:
        try:
            question_number = int(question_number)
            visible_question, hidden_instruction = load_question(topic, question_number)
            if topic == 'math':
                math_solution = solve_math_problem(visible_question)
            else:
                math_solution = ""
        except ValueError:
            return render_template('index.html', error="Invalid question number.")

    if visible_question is None:
        return render_template('index.html', error=f"Question not found for topic '{topic}' and number {question_number}.")

    if topic == 'social':
        context = f"{SOCIAL_SKILLS_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{visible_question}]\nCurrent scenario: {visible_question}\nHidden instruction: {hidden_instruction}\n"
    elif topic == 'reading':
        context = f"{READING_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{visible_question}]\nMichelle has just finished reading the following text: {visible_question}\nHidden instruction: {hidden_instruction}\n"
    elif topic == 'math':
        context = f"{MATH_TUTOR_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{visible_question}]\nCurrent math problem: {visible_question}\nHidden instruction: {hidden_instruction}\nDetailed solution: {math_solution}\n"
    elif topic == 'free':
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}]\nHey Michelle, ask me a question on any topic!"
    elif topic == 'english':
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{visible_question}]\nCurrent English topic: {visible_question}\nHidden instruction: {hidden_instruction}\n"
    else:
        context = f"{GENERAL_TUTOR_PROMPT}\n\n[TOPIC:{topic}][QUESTION:{visible_question}]\nCurrent question: {visible_question}\nHidden instruction: {hidden_instruction}\n"

    display_question = visible_question if visible_question else "Discussion"

    greeting = "Hello Michelle! I'm here to help you with your studies."

    return render_template('tutor.html', topic=topic, question=display_question, context=context, greeting=greeting, question_number=question_number)

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

    # Determine if we should include a quote (45% chance)
    include_quote = random.random() < 0.45
    # Select a random quote
    random_quote = random.choice(MOTIVATIONAL_QUOTES) if include_quote else ""

    # Since the quote's wisdom can be embedded, guide the AI accordingly
    embedded_wisdom = f"Consider this motivational quote: '{random_quote}'. Incorporate its wisdom into your response and explain its relevance to Michelle's learning." if include_quote else ""

    # Initialize ai_response
    ai_response = ""

    if topic == 'social':
        social_skills_interaction_count += 1

        if social_skills_interaction_count >= 17:
            full_prompt = f"""{context}
Human: {user_input}
AI: This is the 17th interaction. Provide a brief, encouraging summary of Michelle's progress in this session. Then, clearly state that the session is complete and instruct Michelle to hit the reset button if she wants to practice again. Your response should be friendly and supportive. {embedded_wisdom}
"""
        else:
            full_prompt = f"""{context}

H: {user_input}
AI: Respond to Michelle's input with a focus on the social skills scenario. Ensure you refer to her by name, ask more questions to understand her perspective, engage in role-playing to enhance the learning experience, provide actionable advice and heavy clues, and maintain an encouraging and positive tone. End your response with a clear question or request for Michelle, except for the final interaction. {embedded_wisdom}
"""

        ai_response = basic_prompt(full_prompt)

        return jsonify({
            "response": ai_response,
            "interaction_count": social_skills_interaction_count,
            "session_complete": social_skills_interaction_count >= 9
        })

    elif topic == 'math':
        full_prompt = f"""{context}

H: {user_input}
AI: You are tutoring Michelle in math. Use the detailed solution provided to guide your tutoring, but don't give away the answer immediately. Break down the problem, ask guiding questions, and provide hints to help Michelle understand and solve the problem step by step. Maintain an encouraging and supportive tone throughout. {embedded_wisdom}
"""
        ai_response = basic_prompt(full_prompt)

    else:
        # Handle other topics
        full_prompt = f"""{context}

H: {user_input}
AI: Provide a helpful and engaging response to Michelle's input, following the guidelines in the prompt. Ensure you address her by name and encourage her learning. End your response with a clear question or request for Michelle. {embedded_wisdom}
"""
        ai_response = basic_prompt(full_prompt)

    return jsonify({
        "response": ai_response
    })

@app.route('/submit_for_evaluation', methods=['POST'])
def submit_for_evaluation():
    conversation = request.json.get('conversation', '').strip()
    topic = request.json.get('topic', '').strip()
    question_number = request.json.get('question_number', '').strip()

    if not conversation or not topic or not question_number:
        return jsonify({"message": "Invalid submission. Please provide all required fields."}), 400

    # Load the question/problem
    if topic != 'free':
        try:
            question_number_int = int(question_number)
            visible_question, _ = load_question(topic, question_number_int)
        except ValueError:
            visible_question = "N/A"
    else:
        visible_question = "Free Topic Discussion"

    if not visible_question:
        visible_question = "N/A"

    # Generate the first evaluation prompt (Part 1)
    evaluation_prompt_part1 = f"""Evaluate the following tutoring session with Michelle. Provide a detailed and verbose analysis of Michelle's performance and learning progress. Your evaluation should include:
1. **Comprehensive Assessment of Michelle's Performance:**
   - Conduct an in-depth analysis of Michelle's understanding and approach to the topic.
   - Identify and explain any potential weaknesses or misconceptions in Michelle's responses.
   - Highlight and elaborate on the strong areas in Michelle's problem-solving skills and comprehension.
   - Provide a detailed examination of areas that can be strengthened in Michelle's learning or communication.
   - Analyze the progression of Michelle's understanding throughout the session.
2. **Extensive Tips for Improvement (Provide at least 15 detailed tips):**
   - Offer a wide range of specific, actionable tips that Michelle could use to enhance her understanding or skills.
   - Ensure these tips are appropriate for a 6th-grade level student but challenge her to grow.
   - For each tip, provide a brief explanation of why it's important and how it can be implemented.
   - Include tips that address various aspects of learning, such as study techniques, problem-solving strategies, and ways to apply knowledge in real-life situations.
Topic: {topic}
Problem/Question: {visible_question}
**Tutoring Session:**
{conversation}
Please format your response with clear headings and subheadings for each section and subsection. Provide a thorough and insightful analysis that will be valuable for Michelle's educational development."""

    # Generate the second evaluation prompt (Part 2)
    evaluation_prompt_part2 = f"""Continuing the evaluation of the tutoring session with Michelle, please focus on the following sections:
3. **Overall Learning Experience Analysis:**
   - Discuss how well the session addressed Michelle's learning needs and style.
   - Suggest potential modifications to the tutoring strategy that could enhance Michelle's learning experience in future sessions.
4. **Fundamentals and Tools for Improvement:**
   - Discuss the fundamental concepts involved in learning the skill to solve the problem or acquire the skill.
   - Provide 5-6 specific tools, resources, or exercises that can help Michelle improve her understanding of these fundamentals.
   - For each tool or resource, explain how it can assist Michelle in strengthening her foundational knowledge.
   - Include recommendations for interactive activities, educational games, or practical applications that align with the topic.
Topic: {topic}
Problem/Question: {visible_question}
**Tutoring Session:**
{conversation}
Please provide a comprehensive analysis that will help Michelle strengthen her fundamental skills in this area."""

    # Generate the motivational quotes prompt
    selected_quotes = random.sample(MOTIVATIONAL_QUOTES, 3)
    quotes_prompt = f"""Analyze the following 3 motivational quotes in the context of Michelle's tutoring session:
1. "{selected_quotes[0]}"
2. "{selected_quotes[1]}"
3. "{selected_quotes[2]}"
For each quote:
1. List the quote.
2. Explain how it relates to Michelle's learning experience and the challenges she faced during the tutoring session.
3. Provide 2-3 specific tips or exercises that can help Michelle embody the wisdom of the quote in her learning journey.
4. Describe how embracing the quote's message can contribute to Michelle's personal growth and academic success.
Topic: {topic}
Problem/Question: {visible_question}
**Tutoring Session:**
{conversation}
Please provide an inspiring and encouraging analysis that will help Michelle build confidence and embrace personal growth."""

    # Get the evaluations from the model
    performance_evaluation = basic_prompt(evaluation_prompt_part1, model="gemma2:2b")
    fundamentals_evaluation = basic_prompt(evaluation_prompt_part2, model="gemma2:2b")
    motivational_analysis = basic_prompt(quotes_prompt, model="gemma2:2b")

    # Combine the evaluations
    full_evaluation = f"""Performance Evaluation:
{performance_evaluation}

Fundamental Skills Analysis:
{fundamentals_evaluation}

Motivational Quotes Analysis:
{motivational_analysis}"""

    # Generate random 3 characters
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

    # Get current date
    current_date = datetime.now().strftime("%d%b%Y").upper()

    # Create the output file
    filename = f"{question_number}_{topic}_{random_chars}_{current_date}.pdf"
    output_path = os.path.join(BASE_DIR, 'answers', filename)

    # Ensure the 'answers' directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Generate PDF with the evaluation
    generate_pdf(output_path, conversation, full_evaluation, topic, visible_question)

    return jsonify({"message": "Evaluation submitted successfully", "filename": filename})

def generate_pdf(output_path, conversation, evaluation, topic, question):
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontSize=14, leading=18))
    styles.add(ParagraphStyle(name='Header', alignment=TA_CENTER, fontSize=12, leading=16))

    # Create the content for the PDF
    content = []

    # Title
    content.append(Paragraph("Tutoring Session Evaluation", styles['Title']))
    content.append(Spacer(1, 12))

    # Topic and Problem at the top
    content.append(Paragraph(f"Topic: {topic.capitalize()}", styles['Header']))
    content.append(Spacer(1, 6))
    content.append(Paragraph(f"Problem/Question: {question}", styles['Header']))
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
            if line.strip().endswith(':') or line.strip().startswith(('1.', '2.', '3.', '4.')):
                current_heading = line.strip()
                content.append(Paragraph(f"<u><b>{current_heading}</b></u>", styles['Heading3']))
            else:
                content.append(Paragraph(line, styles['Justify']))
            content.append(Spacer(1, 4))

    # Build the PDF
    doc.build(content)

if __name__ == '__main__':
    app.run(debug=True)
