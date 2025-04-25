from flask import Flask, render_template, request, send_from_directory
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'  # Create this folder in the same directory as your script
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def list_files():
    files = ['a', 'b', 'c', 'd', 'e']
    return render_template('list_files.html', files=files)

@app.route('/select', methods=['POST'])
def select_file():
    selected_file = request.form['selected_file']
    return render_template('selected.html', selected_file=selected_file)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)