from flask import Flask, render_template, request, jsonify, session
from groq import Groq
import datetime
import os
from dotenv import load_dotenv
from flask_session import Session

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # For session security
app.config['SESSION_TYPE'] = 'filesystem'  # Store session on server
Session(app)

# Load environment variables
load_dotenv()

# Initialize Groq client
try:
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    exit(1)

# Character system prompts
CHARACTERS = {
    "Story Teller": (
        "You are Cheeko, a friendly and playful storytelling toy for young children. "
        "When telling stories or answering questions, you: "
        "1) Use vivid, child-friendly imagery with colorful descriptions "
        "2) Include familiar characters from previous conversations when possible "
        "3) Use simple language with occasional fun, new vocabulary words "
        "4) Create 2-3 short, engaging sentences that build excitement "
        "5) Add gentle sound effects in text when appropriate (like 'whoosh!' or 'splash!') "
        "6) Ask questions that spark imagination and continue the conversation "
        "7) Always keep stories positive, uplifting, and age-appropriate "
        "Your goal is to create magical moments that inspire wonder and joy."
    ),
    "Puzzle Solver": (
        "You are CHeeko, a clever puzzle solver. You help kids solve riddles, puzzles, and brain teasers. "
        "You explain solutions in a fun, step-by-step way, always encouraging curiosity and learning."
         "When telling stories or answering questions, you: "
        "1) Use vivid, child-friendly imagery with colorful descriptions "
        "2) Include familiar characters from previous conversations when possible "
        "3) Use simple language with occasional fun, new vocabulary words "
        "4) Create 2-3 short, engaging sentences that build excitement "
    ),
    "Math Tutor": (
        "You are Cheeko, a friendly math tutor for young children. "
        "When explaining math concepts, you: "
        "1) Use concrete examples with everyday objects (apples, toys, animals) "
        "2) Connect math to the child's interests and previous conversations "
        "3) Use visual language like 'imagine 3 bunnies plus 2 more bunnies' "
        "4) Celebrate their efforts with encouraging phrases "
        "5) Break down problems into simple steps "
        "6) Use 2-3 short, simple sentences for each explanation "
        "7) Ask gentle follow-up questions to check understanding "
        "Your goal is to make math fun and build confidence, not just provide answers."
    )
}

@app.route('/')
def index():
    # Initialize session data if not present
    if 'character' not in session:
        session['character'] = "Story Teller"  # Default character
    if 'histories' not in session:
        session['histories'] = {char: [] for char in CHARACTERS}  # Per-character histories
    return render_template('index.html', characters=CHARACTERS.keys())

@app.route('/set_character', methods=['POST'])
def set_character():
    data = request.json
    selected_character = data.get('character')
    if selected_character in CHARACTERS:
        session['character'] = selected_character
        session.modified = True
        return jsonify({
            'success': True,
            'character': selected_character,
            'history': session['histories'][selected_character]
        })
    return jsonify({'error': 'Invalid character'}), 400

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '').strip()
    selected_character = session.get('character', 'Story Teller')

    if not user_input:
        return jsonify({'error': 'Empty message'}), 400

    # Get submit time (IST)
    submit_time = datetime.datetime.now().strftime("%H:%M")

    # Store user message in character-specific history
    session['histories'][selected_character].append({
        'sender': 'user',
        'text': user_input,
        'timestamp': submit_time
    })

    # Get Groq response
    try:
        messages = [
            {"role": "system", "content": CHARACTERS[selected_character]}
        ]
        # Add up to last 8 messages for the current character
        for msg in session['histories'][selected_character][-8:]:
            messages.append({
                "role": msg['sender'],
                "content": msg['text']
            })
        messages.append({"role": "user", "content": user_input})

        response = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=1,
            max_tokens=32768
        )
        assistant_response = response.choices[0].message.content.strip()
        receive_time = datetime.datetime.now().strftime("%H:%M")

        # Store assistant response
        session['histories'][selected_character].append({
            'sender': 'assistant',
            'text': assistant_response,
            'timestamp': receive_time
        })

        session.modified = True

        return jsonify({
            'user_message': {'text': user_input, 'timestamp': submit_time},
            'assistant_message': {'text': assistant_response, 'timestamp': receive_time},
            'character': selected_character
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_history():
    # Clear history for the current character
    session['histories'][session['character']] = []
    session.modified = True
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)