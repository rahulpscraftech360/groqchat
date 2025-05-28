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

@app.route('/')
def index():
    # Initialize session history if not present
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400

    # Get submit time (in IST, matching your timezone)
    submit_time = datetime.datetime.now().strftime("%H:%M")

    # Store user message in session
    session['history'].append({
        'sender': 'user',
        'text': user_input,
        'timestamp': submit_time
    })

    # Get Grok response
    try:
        messages = [
            {"role": "system", "content": "You are Grok, a helpful AI assistant. Provide clear, concise answers suitable for all ages."}
        ]
        # Add up to last 8 messages to manage context
        for msg in session['history'][-8:]:
            messages.append({
                "role": msg['sender'],
                "content": msg['text']
            })
        messages.append({"role": "user", "content": user_input})

        response = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=500
        )
        assistant_response = response.choices[0].message.content.strip()
        receive_time = datetime.datetime.now().strftime("%H:%M")

        # Store assistant response in session
        session['history'].append({
            'sender': 'assistant',
            'text': assistant_response,
            'timestamp': receive_time
        })

        # Ensure session is saved
        session.modified = True

        return jsonify({
            'user_message': {'text': user_input, 'timestamp': submit_time},
            'assistant_message': {'text': assistant_response, 'timestamp': receive_time}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_history():
    session['history'] = []
    session.modified = True
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)