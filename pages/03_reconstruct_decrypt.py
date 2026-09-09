from flask import Flask, render_template, request, redirect, url_for
from src.decryption import decrypt
from src.visual_cryptography import reconstruct_from_shares
import numpy as np
import cv2
import os

app = Flask(__name__)

@app.route('/reconstruct_decrypt', methods=['GET', 'POST'])
def reconstruct_decrypt():
    if request.method == 'POST':
        share1_file = request.files['share1']
        share2_file = request.files['share2']
        
        if share1_file and share2_file:
            share1 = np.frombuffer(share1_file.read(), np.uint8)
            share1 = cv2.imdecode(share1, cv2.IMREAD_GRAYSCALE)
            share2 = np.frombuffer(share2_file.read(), np.uint8)
            share2 = cv2.imdecode(share2, cv2.IMREAD_GRAYSCALE)

            # Reconstruct the encrypted image from shares
            encrypted_image = reconstruct_from_shares(share1, share2)

            # Decrypt the image
            decrypted_image = decrypt(encrypted_image)

            # Save the results
            output_dir = 'output'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            cv2.imwrite(os.path.join(output_dir, 'reconstructed.png'), encrypted_image)
            cv2.imwrite(os.path.join(output_dir, 'decrypted.png'), decrypted_image)

            return redirect(url_for('reconstruct_decrypt', success=True))

    return render_template('reconstruct_decrypt.html')

if __name__ == '__main__':
    app.run(debug=True)