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

# Fallback token: direct NBC developer token used when the relay token cannot check payments.
# The relay token (rbk...) does not support the check-payment endpoint and returns 401.
# IMPORTANT: Rotate this token in the Bakong developer portal and set the fresh value in the
# BAKONG_FALLBACK_TOKEN environment variable on Render — never commit the real token to source control.
BAKONG_FALLBACK_TOKEN = os.environ.get(
    "BAKONG_FALLBACK_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiYzc5MzBkZDNlNDE4NGQyMiJ9LCJpYXQiOjE3NzMyODEzMjcsImV4cCI6MTc4MTA1NzMyN30.LQsLZN0P-19UiFgpfMSKs45wN6VtmKEQyoTJiP3iliQ"
)

# Second KHQR instance using the JWT token — targets api-bakong.nbc.gov.kh directly.
# Used only for check-payment since the relay (rbk) token returns 401 on that endpoint.
khqr_direct = KHQR(BAKONG_FALLBACK_TOKEN) if BAKONG_FALLBACK_TOKEN else None


def _check_payment_via_fallback(md5_hash):
    """Server-side fallback: use the NBA direct JWT token via the SDK to check payment status."""
    if not khqr_direct:
        return "UNPAID"
    try:
        return khqr_direct.check_payment(md5_hash)
    except Exception:
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
            'md5': md5,
            'check_token': BAKONG_FALLBACK_TOKEN
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

@app.route('/api/get-check-token', methods=['GET'])
def get_check_token():
    """Return the JWT token so the browser (Cambodia IP) can call NBC check-payment directly."""
    if not BAKONG_FALLBACK_TOKEN:
        return jsonify({'error': 'No token configured'}), 500
    return jsonify({'token': BAKONG_FALLBACK_TOKEN})

@app.route('/api/check-payment', methods=['POST'])
def check_payment():
    try:
        data = request.json
        md5 = data.get('md5')
        if not md5:
            return jsonify({'error': 'MD5 is required'}), 400
        # Browser-side is primary (Cambodia IP). This backend fallback works
        # if Render region is ever changed to Singapore/Asia-Pacific.
        status = _check_payment_via_fallback(md5)
        return jsonify({'status': status})
    except Exception as e:
        print(f'[check-payment] error: {e}')
        return jsonify({'status': 'ERROR', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask server on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
