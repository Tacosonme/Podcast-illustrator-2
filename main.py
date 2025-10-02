import os
import subprocess
import json
import tempfile
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configure for Railway
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_job_status(job_dir, status, progress, message=""):
    """Update job status"""
    status_data = {
        'status': status,
        'progress': progress,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    status_file = os.path.join(job_dir, 'status.json')
    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=2)

def segment_audio(job_dir, audio_file, segment_duration=600):
    """Split audio into segments using FFmpeg"""
    segments_dir = os.path.join(job_dir, 'segments')
    os.makedirs(segments_dir, exist_ok=True)
    
    try:
        update_job_status(job_dir, 'processing', 10, 'Segmenting audio file...')
        
        # Use the working FFmpeg command
        cmd = [
            'ffmpeg', '-i', audio_file,
            '-f', 'segment',
            '-segment_time', str(segment_duration),
            '-c:a', 'libmp3lame',
            '-b:a', '128k',
            '-ar', '44100',
            '-ac', '2',
            os.path.join(segments_dir, 'segment_%03d.mp3')
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Get list of created segments
        segment_files = []
        for filename in sorted(os.listdir(segments_dir)):
            if filename.startswith('segment_') and filename.endswith('.mp3'):
                segment_files.append(os.path.join(segments_dir, filename))
        
        update_job_status(job_dir, 'processing', 30, f'Created {len(segment_files)} audio segments')
        return segment_files
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Audio segmentation failed: {e.stderr}"
        update_job_status(job_dir, 'failed', 0, error_msg)
        raise Exception(error_msg)

# Frontend HTML template
FRONTEND_HTML = '''
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
        input[type="file"] { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #ddd; 
            border-radius: 10px; 
            font-size: 16px;
            margin: 10px 0;
        }
        input[type="text"] { 
            width: 300px; 
            padding: 10px; 
            border: 2px solid #ddd; 
            border-radius: 8px; 
            font-size: 14px;
            margin: 0 10px;
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
        .progress { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .progress-bar { height: 100%; background: #667eea; transition: width 0.3s; }
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
        .status-section { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Podcast Illustrator</h1>
        <p class="subtitle">Transform your podcasts into illustrated videos with AI</p>
        
        <div class="features">
            <div class="feature">
                <h3>🎵 Audio Processing</h3>
                <p>FFmpeg-powered audio segmentation and conversion</p>
            </div>
            <div class="feature">
                <h3>🤖 AI Transcription</h3>
                <p>OpenAI Whisper for accurate speech-to-text (coming soon)</p>
            </div>
            <div class="feature">
                <h3>🎨 Visual Generation</h3>
                <p>AI-generated images synchronized with audio (coming soon)</p>
            </div>
        </div>

        <div class="upload-area">
            <h3>📁 Upload Your Podcast</h3>
            <p>Drag and drop your audio file here, or click to browse</p>
            <input type="file" id="audioFile" accept="audio/*" />
            <button onclick="uploadFile()" id="uploadBtn">Upload & Process</button>
        </div>

        <div id="result"></div>
        
        <div class="status-section">
            <h3>🔍 Processing Status</h3>
            <input type="text" id="jobId" placeholder="Enter Job ID" />
            <button onclick="checkStatus()">Check Status</button>
            <div id="statusResult"></div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;

        function showResult(elementId, message, type = 'info') {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="result ${type}">${message}</div>`;
        }

        function showProgress(elementId, progress) {
            const element = document.getElementById(elementId);
            element.innerHTML = `
                <div class="result info">
                    <div>Processing... ${progress}%</div>
                    <div class="progress">
                        <div class="progress-bar" style="width: ${progress}%"></div>
                    </div>
                </div>
            `;
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
                        <strong>Status:</strong> ${data.status}
                    `, 'success');
                    
                    document.getElementById('jobId').value = data.job_id;
                    setTimeout(() => startProcessing(data.job_id), 1000);
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

        async function startProcessing(jobId) {
            try {
                const response = await fetch(`${API_BASE}/api/process/${jobId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showResult('result', `
                        <strong>🚀 Processing Started!</strong><br>
                        Job ID: <code>${jobId}</code><br>
                        Status: ${data.status}
                    `, 'success');
                    
                    monitorProgress(jobId);
                } else {
                    showResult('result', `Processing failed: ${data.error || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                showResult('result', `Processing error: ${error.message}`, 'error');
            }
        }

        async function checkStatus() {
            const jobId = document.getElementById('jobId').value.trim();
            
            if (!jobId) {
                showResult('statusResult', 'Please enter a Job ID.', 'error');
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE}/api/status/${jobId}`);
                const data = await response.json();
                
                if (response.ok) {
                    const progress = data.progress || 0;
                    if (data.status === 'processing') {
                        showProgress('statusResult', progress);
                    } else {
                        showResult('statusResult', `
                            <strong>Status:</strong> ${data.status}<br>
                            <strong>Progress:</strong> ${progress}%<br>
                            <strong>Message:</strong> ${data.message}<br>
                            <strong>Timestamp:</strong> ${data.timestamp}
                        `, data.status === 'completed' ? 'success' : data.status === 'failed' ? 'error' : 'info');
                    }
                } else {
                    showResult('statusResult', `Status check failed: ${data.error || 'Job not found'}`, 'error');
                }
            } catch (error) {
                showResult('statusResult', `Status error: ${error.message}`, 'error');
            }
        }

        async function monitorProgress(jobId) {
            const checkProgress = async () => {
                try {
                    const response = await fetch(`${API_BASE}/api/status/${jobId}`);
                    const data = await response.json();
                    
                    if (response.ok) {
                        const progress = data.progress || 0;
                        showProgress('statusResult', progress);
                        
                        if (data.status === 'completed') {
                            showResult('statusResult', `
                                <strong>✅ Processing Complete!</strong><br>
                                Job ID: <code>${jobId}</code><br>
                                Message: ${data.message}
                            `, 'success');
                        } else if (data.status === 'failed') {
                            showResult('statusResult', `❌ Processing failed: ${data.message}`, 'error');
                        } else if (data.status === 'processing') {
                            setTimeout(checkProgress, 3000);
                        }
                    }
                } catch (error) {
                    console.error('Progress monitoring error:', error);
                }
            };
            
            checkProgress();
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(FRONTEND_HTML)

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'platform': 'railway',
        'version': '1.1.0',
        'features': ['file_upload', 'audio_processing', 'ffmpeg'],
        'message': 'Audio processing with FFmpeg enabled!'
    })

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Supported: mp3, wav, m4a, flac, ogg'}), 400
    
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(job_dir, filename)
    file.save(file_path)
    
    file_size = os.path.getsize(file_path)
    
    update_job_status(job_dir, 'uploaded', 0, 'File uploaded successfully')
    
    return jsonify({
        'job_id': job_id,
        'filename': filename,
        'file_size': file_size,
        'status': 'uploaded',
        'message': 'File uploaded successfully! Ready for processing.'
    })

@app.route('/api/process/<job_id>', methods=['POST'])
def process_audio(job_id):
    job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    
    if not os.path.exists(job_dir):
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        audio_file = None
        for filename in os.listdir(job_dir):
            if filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg')):
                audio_file = os.path.join(job_dir, filename)
                break
        
        if not audio_file:
            return jsonify({'error': 'No audio file found'}), 400
        
        try:
            segments = segment_audio(job_dir, audio_file, segment_duration=600)
            update_job_status(job_dir, 'completed', 100, f'Audio processing complete! Created {len(segments)} segments.')
        except Exception as e:
            update_job_status(job_dir, 'failed', 0, str(e))
            return jsonify({'error': str(e)}), 500
        
        return jsonify({
            'job_id': job_id,
            'status': 'processing',
            'message': 'Audio processing started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<job_id>')
def get_status(job_id):
    job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    status_file = os.path.join(job_dir, 'status.json')
    
    if not os.path.exists(status_file):
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        return jsonify(status_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
