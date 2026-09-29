import os
import json
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Load categories
with open('categories.json', 'r', encoding='utf-8') as f:
    CATEGORIES = json.load(f)

# User sessions storage (in-memory, use database in production)
user_sessions = {}

def load_categories():
    """Load product categories from JSON"""
    with open('categories.json', 'r', encoding='utf-8') as f:
        return json.load(f)['categories']

def categorize_order(text):
    """Categorize incoming order based on keywords"""
    text_lower = text.lower()
    
    for category in CATEGORIES['categories']:
        for keyword in category['keywords']:
            if keyword in text_lower:
                return category
    
    return CATEGORIES['categories'][-1]  # Return "Other" category

def get_welcome_message():
    """Return welcome message for new customers"""
    return """السلام عليكم! 👋 

خوش آمدید ہمارے Order Processing Bot میں!

میں آپ کے آرڈر کو سنبھالنے میں مدد کروں گا۔

براہ کرم اپنا آرڈر بتائیں اور میں اسے categorize کروں گا۔

مثال: "مجھے 2 کپ چائے چاہیے" یا "ایک نیا فون"

کیسے مدد کر سکتا ہوں؟"""

def get_category_response(category):
    """Generate response based on category"""
    category_responses = {
        "Food & Beverages": "🍜 آپ کا آرڈر **کھانے پینے** کے زمرے میں شامل ہے۔\nآپ کی تفصیلات:\n- شے: کھانا/مشروبات\n- ڈیلیوری وقت: 30 منٹ",
        "Electronics": "📱 آپ کا آرڈر **الیکٹرانکس** کے زمرے میں شامل ہے۔\nآپ کی تفصیلات:\n- شے: الیکٹرانک چیزیں\n- ڈیلیوری وقت: 2-3 دن",
        "Clothing": "👕 آپ کا آرڈر **کپڑوں** کے زمرے میں شامل ہے۔\nآپ کی تفصیلات:\n- شے: کپڑے\n- ڈیلیوری وقت: 1-2 دن",
        "Books & Stationery": "📚 آپ کا آرڈر **کتابیں اور سٹیشنری** کے زمرے میں شامل ہے۔\nآپ کی تفصیلات:\n- شے: کتابیں/سٹیشنری\n- ڈیلیوری وقت: 1 دن",
        "Home & Garden": "🏠 آپ کا آرڈر **گھر اور باغ** کے زمرے میں شامل ہے۔\nآپ کی تفصیلات:\n- شے: فرنیچر/ڈیکوریشن\n- ڈیلیوری وقت: 3-5 دن",
        "Other": "❓ آپ کے آرڈر کو درست طریقے سے categorize نہیں کیا جا سکا۔\nبراہ کرم اپنے آرڈر کی مزید تفصیل دیں۔"
    }
    
    return category_responses.get(category['name'], "معلومات کے لیے شکریہ! ہم آپ کے آرڈر کو process کریں گے۔")

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message using Twilio"""
    try:
        message_obj = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=to_number
        )
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    # Initialize user session if new
    if sender not in user_sessions:
        user_sessions[sender] = {
            'welcomed': False,
            'orders': []
        }
    
    # Welcome new users
    if not user_sessions[sender]['welcomed']:
        response_text = get_welcome_message()
        user_sessions[sender]['welcomed'] = True
    else:
        # Categorize the order
        category = categorize_order(incoming_msg)
        response_text = get_category_response(category)
        
        # Store order
        user_sessions[sender]['orders'].append({
            'message': incoming_msg,
            'category': category['name']
        })
    
    # Create Twilio response
    resp = MessagingResponse()
    resp.message(response_text)
    
    return str(resp)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {'status': 'Bot is running!'}, 200

@app.route('/stats', methods=['GET'])
def stats():
    """Get bot statistics"""
    total_users = len(user_sessions)
    total_orders = sum(len(session['orders']) for session in user_sessions.values())
    
    return {
        'total_users': total_users,
        'total_orders': total_orders,
        'sessions': user_sessions
    }, 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
