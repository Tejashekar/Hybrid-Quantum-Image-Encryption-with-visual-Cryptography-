from flask import Flask, render_template, request, redirect, url_for
from src.quantum_encryption import encrypt
from src.visual_cryptography import generate_shares
from src.utils import load_image, save_image

app = Flask(__name__)

@app.route('/encrypt_split', methods=['GET', 'POST'])
def encrypt_split():
    if request.method == 'POST':
        # Get the uploaded image
        file = request.files['image']
        if file:
            # Load and preprocess the image
            image = load_image(file)
            encrypted_image = encrypt(image)
            share1, share2 = generate_shares(encrypted_image)

            # Save the shares to output directory
            save_image(share1, 'output/share1.png')
            save_image(share2, 'output/share2.png')

            return redirect(url_for('view_shares'))

    return render_template('encrypt_split.html')

@app.route('/view_shares')
def view_shares():
    return render_template('view_shares.html')

if __name__ == '__main__':
    app.run(debug=True)