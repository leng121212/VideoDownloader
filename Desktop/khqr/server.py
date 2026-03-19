from flask import Flask, request, jsonify
from flask_cors import CORS
from bakong_khqr import KHQR
import base64
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Initialize KHQR with Bakong Developer Token
# Using original Bakong Developer Token
BAKONG_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiYzc5MzBkZDNlNDE4NGQyMiJ9LCJpYXQiOjE3NzMyODEzMjcsImV4cCI6MTc4MTA1NzMyN30.LQsLZN0P-19UiFgpfMSKs45wN6VtmKEQyoTJiP3iliQ"
khqr = KHQR(BAKONG_TOKEN)

@app.route('/api/create-qr', methods=['POST'])
def create_qr():
    try:
        data = request.json
        amount = float(data.get('amount'))
        currency = data.get('currency', 'USD') # Default to USD
        
        # Validate currency
        if currency not in ['USD', 'KHR']:
            return jsonify({'error': 'Invalid currency. Must be USD or KHR.'}), 400

        # Create QR Data
        qr_data = khqr.create_qr(
            bank_account='chhunleng_tong@bkrt',
            merchant_name='TONG CHHUNLENG',
            merchant_city='Phnom Penh',
            amount=amount,
            currency=currency,
            store_label='Trabekprey',
            phone_number='85512345678',
            bill_number='TRX01234567',
            terminal_label='Cashier-01',
            static=False
        )
        
        # Generate MD5
        md5 = khqr.generate_md5(qr_data)
        
        # We bypass image generation on the backend to prevent Render Free Tier from freezing (Memory limits)
        # We will just return the pure qr_data and let the frontend draw the actual QR image.
        
        return jsonify({
            'qr_data': qr_data,
            'md5': md5,
            'qr_image': khqr.qr_image(qr_data, format="base64_uri")
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-payment', methods=['POST'])
def check_payment():
    try:
        data = request.json
        md5 = data.get('md5')
        
        if not md5:
            return jsonify({'error': 'MD5 is required'}), 400
            
        status = khqr.check_payment(md5)
        
        return jsonify({'status': status})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask server on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
