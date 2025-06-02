import subprocess
from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO
import os
from werkzeug.utils import secure_filename
from video_processor import process_video, process_cancelled
import logging
import threading

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app)

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

current_processing_thread = None

@app.route('/')
def index():  
    return render_template('upload.html')

@app.route('/tracking')
def tracking():
    return render_template('tracking.html')

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_processing_thread
    try:
        if 'file' not in request.files or 'confidence' not in request.form:
            return "No file part or confidence threshold", 400
        file = request.files['file']
        confidence_threshold = float(request.form['confidence'])
        if file.filename == '':
            return "No selected file", 400
        if file:
            if current_processing_thread and current_processing_thread.is_alive():
                process_cancelled.set()

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            current_processing_thread = threading.Thread(target=process_video_with_progress, args=(filepath, confidence_threshold))
            current_processing_thread.start()
            return jsonify({"message": "Processing started"}), 202
    except Exception as e:
        logging.error("Error during file upload: %s", e)
        return "An error occurred during file upload.", 500

def process_video_with_progress(filepath, confidence_threshold):
    try:
        result = process_video(filepath, socketio, confidence_threshold)
        result['total_frames'] = result.get('total_frames')
        result['fps'] = result.get('fps')
        result['duration'] = result.get('duration')
        socketio.emit('result', result)
    except Exception as e:
        logging.error("Error during video processing: %s", e)
        socketio.emit('result', {"error": "An error occurred during video processing."})

if __name__ == "__main__":
    print("Starting server on http://localhost:8080")
    socketio.run(app, host="0.0.0.0", port=8080)
