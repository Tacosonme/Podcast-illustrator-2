import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import tempfile
import uuid

app = Flask(__name__)
CORS(app)

# Configure for Railway
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

@app.route('/')
def home():
    return jsonify({
        'status': 'healthy',
        'service': 'podcast-illustrator',
        'message': 'Railway deployment successful!'
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'platform': 'railway',
        'version': '1.0.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    return jsonify({
        'job_id': job_id,
        'filename': file.filename,
        'file_size': len(file.read()),
        'status': 'uploaded',
        'message': 'File uploaded successfully - processing will be implemented'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

