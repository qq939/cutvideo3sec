import os
import requests
from flask import Flask, request, jsonify
from moviepy import VideoFileClip
import math

app = Flask(__name__)

# Config
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
TARGET_URL = "http://videocut.dimond.top/overall"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return '''
    <!doctype html>
    <title>Upload Video</title>
    <h1>Upload Video to Cut and Send</h1>
    <form action="/upload_and_cut" method=post enctype=multipart/form-data>
      <input type=file name=video>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/upload_and_cut', methods=['POST'])
def upload_and_cut():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save uploaded file
    filename = file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    results = []
    
    try:
        # Load video
        clip = VideoFileClip(file_path)
        duration = clip.duration
        
        # Cut into 3s segments
        segment_duration = 3
        num_segments = math.ceil(duration / segment_duration)
        
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration)
            
            # Create subclip
            subclip = clip.subclip(start_time, end_time)
            
            # Generate segment filename
            segment_filename = f"segment_{i}_{filename}"
            segment_path = os.path.join(UPLOAD_FOLDER, segment_filename)
            
            # Write segment to file
            # Use ultrafast preset for speed, libx264 for compatibility
            subclip.write_videofile(
                segment_path, 
                codec='libx264', 
                audio_codec='aac', 
                temp_audiofile=os.path.join(UPLOAD_FOLDER, f"temp-audio-{i}.m4a"), 
                remove_temp=True,
                preset='ultrafast',
                logger=None # Silence output
            )
            
            # Post to target URL
            try:
                with open(segment_path, 'rb') as f:
                    files = {'video': (segment_filename, f, 'video/mp4')}
                    response = requests.post(TARGET_URL, files=files)
                    results.append({
                        'segment': i,
                        'status_code': response.status_code,
                        'response': response.json() if response.content else None
                    })
            except Exception as req_e:
                results.append({
                    'segment': i,
                    'error': str(req_e)
                })
            
            # Clean up segment file
            if os.path.exists(segment_path):
                os.remove(segment_path)
                
        clip.close()
        
        # Clean up original file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return jsonify({'status': 'processed', 'results': results})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
