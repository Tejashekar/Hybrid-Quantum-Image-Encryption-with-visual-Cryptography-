from src.preprocessing import load_image, preprocess
from src.quantum_encryption import encrypt
from src.visual_cryptography import generate_shares
from src.decryption import decrypt
from src.metrics import calculate_metrics

def run_pipeline(image_path):
    # Step 1: Load and preprocess the image
    image = load_image(image_path)
    preprocessed_image = preprocess(image)

    # Step 2: Encrypt the preprocessed image
    encrypted_image = encrypt(preprocessed_image)

    # Step 3: Generate visual cryptography shares
    share1, share2 = generate_shares(encrypted_image)

    # Step 4: Decrypt the image from shares
    reconstructed_image = decrypt(share1, share2)

    # Step 5: Calculate metrics
    metrics = calculate_metrics(preprocessed_image, encrypted_image, reconstructed_image)

    return {
        "original": preprocessed_image,
        "encrypted": encrypted_image,
        "share1": share1,
        "share2": share2,
        "reconstructed": reconstructed_image,
        "metrics": metrics
    }