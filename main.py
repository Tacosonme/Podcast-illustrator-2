import os
from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_cors import CORS
import tempfile
import uuid

app = Flask(__name__)
CORS(app)

# Configure for Railway
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Frontend HTML template
FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎙️ Podcast Illustrator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 600px;
            width: 100%;
            text-align: center;
        }
        h1 { color: #333; margin-bottom: 10px; font-size: 2.5em; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 1.1em; }
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 15px;
            padding: 40px;
            margin: 30px 0;
            background: #f9f9f9;
            transition: all 0.3s ease;
        }
        .upload-area:hover { border-color: #667eea; background: #f0f4ff; }
        .upload-area.dragover { border-color: #667eea; background: #e8f2ff; }
        input[type="file"] { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #ddd; 
            border-radius: 10px; 
            font-size: 16px;
            margin: 10px 0;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 18px;
            cursor: pointer;
            transition: transform 0.2s;
            margin: 10px;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: left;
        }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .feature {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: left;
        }
        .feature h3 { color: #667eea; margin-bottom: 10px; }
        .status { margin-top: 20px; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Podcast Illustrator</h1>
        <p class="subtitle">Transform your podcasts into illustrated videos with AI</p>
        
        <div class="features">
            <div class="feature">
                <h3>🎵 Audio Upload</h3>
                <p>Support for MP3, WAV, M4A, FLAC, OGG files up to 200MB</p>
            </div>
            <div class="feature">
                <h3>🤖 AI Processing</h3>
                <p>Automatic transcription and content analysis</p>
            </div>
            <div class="feature">
                <h3>🎨 Visual Generation</h3>
                <p>AI-generated images synchronized with audio</p>
            </div>
        </div>

        <div class="upload-area" id="uploadArea">
            <h3>📁 Upload Your Podcast</h3>
            <p>Drag and drop your audio file here, or click to browse</p>
            <input type="file" id="audioFile" accept="audio/*" />
            <button onclick="uploadFile()" id="uploadBtn">Upload & Process</button>
        </div>

        <div id="result"></div>
        
        <div class="status">
            <h3>🔍 API Status</h3>
            <button onclick="checkHealth()">Test Connection</button>
            <div id="healthResult"></div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;
        
        // Drag and drop functionality
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('audioFile');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
            }
        });
        
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        function showResult(elementId, message, type = 'info') {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="result ${type}">${message}</div>`;
        }

        async function uploadFile() {
            const fileInput = document.getElementById('audioFile');
            const uploadBtn = document.getElementById('uploadBtn');
            
            if (!fileInput.files[0]) {
                showResult('result', 'Please select an audio file first.', 'error');
                return;
            }

            const file = fileInput.files[0];
            const fileSizeMB = (file.size / 1024 / 1024).toFixed(2);
            
            if (file.size > 200 * 1024 * 1024) {
                showResult('result', `File too large (${fileSizeMB}MB). Maximum size is 200MB.`, 'error');
                return;
            }

            const formData = new FormData();
            formData.append('audio', file);
            
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Uploading...';
            
            try {
                showResult('result', `Uploading ${file.name} (${fileSizeMB}MB)...`, 'info');
                
                const response = await fetch(`${API_BASE}/api/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult('result', `
                        <strong>✅ Upload Successful!</strong><br>
                        <strong>Job ID:</strong> <code>${data.job_id}</code><br>
                        <strong>Filename:</strong> ${data.filename}<br>
                        <strong>File Size:</strong> ${(data.file_size / 1024 / 1024).toFixed(2)} MB<br>
                        <strong>Status:</strong> ${data.status}<br>
                        <em>Note: Full processing features will be added in the next update!</em>
                    `, 'success');
                } else {
                    showResult('result', `Upload failed: ${data.error || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                showResult('result', `Upload error: ${error.message}`, 'error');
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload & Process';
            }
        }

        async function checkHealth() {
            try {
                showResult('healthResult', 'Testing connection...', 'info');
                
                const response = await fetch(`${API_BASE}/api/health`);
                const data = await response.json();
                
                if (response.ok) {
                    showResult('healthResult', `
                        <strong>✅ Connection Successful!</strong><br>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `, 'success');
                } else {
                    showResult('healthResult', `❌ Connection failed (${response.status})`, 'error');
                }
            } catch (error) {
                showResult('healthResult', `❌ Connection error: ${error.message}`, 'error');
            }
        }

        // Auto health check on page load
        window.onload = () => {
            checkHealth();
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(FRONTEND_HTML)

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'platform': 'railway',
        'version': '1.0.0',
        'features': ['file_upload', 'health_check'],
        'message': 'Backend API is running successfully!'
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
    
    # Get file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    return jsonify({
        'job_id': job_id,
        'filename': file.filename,
        'file_size': file_size,
        'status': 'uploaded',
        'message': 'File uploaded successfully! Processing features coming soon.'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

