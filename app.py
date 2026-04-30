"""
Advanced AI Chatbot - Flask Web Application
Main entry point for the chatbot service
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import logging
from chatbot.core import AdvancedChatbot
from chatbot.context_manager import ContextManager

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize chatbot and context manager
chatbot = AdvancedChatbot(model_path='models/chatbot_model.h5')
context_manager = ContextManager()

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Store active user sessions
user_sessions = {}


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    Accepts a message and returns AI response
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'message' not in data:
            return jsonify({
                'error': 'Message is required',
                'status': 'error'
            }), 400
        
        message = data.get('message', '').strip()
        user_id = data.get('user_id', 'anonymous')
        language = data.get('language', 'en')
        
        if not message:
            return jsonify({
                'error': 'Message cannot be empty',
                'status': 'error'
            }), 400
        
        # Get or create user context
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                'context': [],
                'created_at': datetime.now().isoformat()
            }
        
        session = user_sessions[user_id]
        
        # Add message to context
        session['context'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep context limited to last 10 messages
        if len(session['context']) > 10:
            session['context'] = session['context'][-10:]
        
        # Generate response
        response = chatbot.chat(
            message=message,
            context=session['context'],
            language=language
        )
        
        # Add response to context
        session['context'].append({
            'role': 'assistant',
            'content': response['text'],
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"User {user_id}: {message[:50]}...")
        
        return jsonify({
            'response': response['text'],
            'confidence': response.get('confidence', 0.0),
            'intent': response.get('intent', 'general'),
            'entities': response.get('entities', []),
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/train', methods=['POST'])
def train_chatbot():
    """
    Train the chatbot with new data
    """
    try:
        data = request.get_json()
        
        if not data or 'training_data' not in data:
            return jsonify({
                'error': 'Training data is required',
                'status': 'error'
            }), 400
        
        training_data = data.get('training_data', [])
        epochs = data.get('epochs', 50)
        
        # Train the model
        result = chatbot.train(training_data, epochs=epochs)
        
        logger.info("Chatbot training completed")
        
        return jsonify({
            'status': 'success',
            'message': 'Training completed',
            'accuracy': result['accuracy'],
            'loss': result['loss']
        }), 200
        
    except Exception as e:
        logger.error(f"Error in train endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/context/<user_id>', methods=['GET'])
def get_context(user_id):
    """
    Get conversation context for a user
    """
    try:
        if user_id not in user_sessions:
            return jsonify({
                'error': 'User session not found',
                'status': 'error'
            }), 404
        
        return jsonify({
            'user_id': user_id,
            'context': user_sessions[user_id]['context'],
            'session_created': user_sessions[user_id]['created_at'],
            'status': 'success'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_context endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/context/<user_id>', methods=['DELETE'])
def clear_context(user_id):
    """
    Clear conversation context for a user
    """
    try:
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        return jsonify({
            'message': f'Context cleared for user {user_id}',
            'status': 'success'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in clear_context endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'chatbot_loaded': chatbot is not None,
        'active_sessions': len(user_sessions),
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint with API documentation
    """
    docs = {
        'name': 'Advanced AI Chatbot API',
        'version': '1.0.0',
        'author': 'Shubham Kadam',
        'endpoints': {
            'POST /api/chat': 'Send a message and get AI response',
            'POST /api/train': 'Train the chatbot with new data',
            'GET /api/context/<user_id>': 'Get user conversation history',
            'DELETE /api/context/<user_id>': 'Clear user context',
            'GET /api/health': 'Check API health status'
        },
        'example_request': {
            'url': 'POST /api/chat',
            'body': {
                'message': 'Hello, how are you?',
                'user_id': 'user123',
                'language': 'en'
            }
        }
    }
    return jsonify(docs), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500


if __name__ == '__main__':
    logger.info("Starting Advanced AI Chatbot Server...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
