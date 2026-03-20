from flask import Flask, request, jsonify
from flask_cors import CORS
from bakong_khqr import KHQR
import os
import http.client
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Primary token (relay): stored as environment variable on hosting platform
BAKONG_TOKEN = os.environ.get(
    "BAKONG_TOKEN",
    "rbkJSlqXv-ZAIDcmwSufaAufUQIjqzjPKllXJczuRTxxBE"
)
khqr = KHQR(BAKONG_TOKEN)

def _check_payment(md5_hash):
    """
    Check payment via the relay (api.bakongrelay.com) using the rbk token.
    The relay accepts rbk tokens and proxies from a Cambodia IP — this is
    the same path used by create_qr() and is known to work.
    """
    try:
        result = khqr.check_payment(md5_hash)
        print(f"[check-payment] relay result: {result}")
        return result  # "PAID" or "UNPAID"
    except Exception as e:
        print(f"[check-payment] relay error: {e}")
        return "UNPAID"

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok'})

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
        
        return jsonify({
            'qr_data': qr_data,
            'md5': md5
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/qr-image', methods=['POST'])
def qr_image_endpoint():
    try:
        data = request.json
        qr_data = data.get('qr_data')
        if not qr_data:
            return jsonify({'error': 'qr_data is required'}), 400
        qr_image_uri = khqr.qr_image(qr_data, format='base64_uri')
        return jsonify({'qr_image': qr_image_uri})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-payment', methods=['POST'])
def check_payment():
    try:
        data = request.json
        md5 = data.get('md5')
        if not md5:
            return jsonify({'error': 'MD5 is required'}), 400
        status = _check_payment(md5)
        return jsonify({'status': status})
    except Exception as e:
        print(f'[check-payment] error: {e}')
        return jsonify({'status': 'ERROR', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask server on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
