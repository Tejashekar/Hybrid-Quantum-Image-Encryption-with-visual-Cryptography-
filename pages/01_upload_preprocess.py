from flask import Flask, render_template, request, redirect, url_for
from src.preprocessing import load_image, preprocess, image_to_matrix
import os

app = Flask(__name__)

# Directory to save uploaded images
UPLOAD_FOLDER = 'input/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        # Preprocess the image
        image = load_image(file_path)
        processed_image = preprocess(image, size=(128, 128))
        image_matrix = image_to_matrix(processed_image)
        
        # Redirect to the next step (e.g., encryption)
        return redirect(url_for('next_step', image_matrix=image_matrix.tolist()))
    
@app.route('/next_step')
def next_step():
    # Placeholder for the next step in the pipeline
    return render_template('next_step.html')

if __name__ == '__main__':
    app.run(debug=True)