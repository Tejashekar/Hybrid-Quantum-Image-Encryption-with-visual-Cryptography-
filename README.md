# Quantum Image Encryption + Visual Cryptography

## Overview
This project implements a quantum image encryption system combined with visual cryptography techniques. The goal is to securely encrypt images using quantum principles and then split the encrypted image into shares that can be reconstructed without revealing the original image.

## Features
- **Image Upload and Preprocessing**: Users can upload images, which are then preprocessed for encryption.
- **Quantum Encryption**: Utilizes quantum gates and NEQR encoding to encrypt images.
- **Visual Cryptography**: Splits the encrypted image into shares using a (2,2) visual cryptography scheme.
- **Reconstruction and Decryption**: Allows users to reconstruct the original image from shares and decrypt it.
- **Metrics Dashboard**: Provides visualizations of encryption quality metrics to assess the effectiveness of the encryption process.

## Project Structure
```
quantum-image-encryption-vc
├── app.py
├── pages
│   ├── 01_upload_preprocess.py
│   ├── 02_encrypt_split.py
│   ├── 03_reconstruct_decrypt.py
│   └── 04_metrics_dashboard.py
├── src
│   ├── config.py
│   ├── preprocessing.py
│   ├── neqr_encoder.py
│   ├── quantum_encryption.py
│   ├── visual_cryptography.py
│   ├── decryption.py
│   ├── metrics.py
│   ├── pipeline.py
│   └── utils.py
├── tests
│   ├── test_pipeline.py
│   ├── test_visual_cryptography.py
│   └── test_metrics.py
├── docs
│   └── implementation
│       ├── 01_project_setup.md
│       ├── 02_preprocessing_module.md
│       ├── 03_neqr_encoding.md
│       ├── 04_encryption_pipeline.md
│       ├── 05_visual_cryptography.md
│       ├── 06_decryption_pipeline.md
│       ├── 07_ui_integration.md
│       ├── 08_metrics_validation.md
│       └── 09_testing_release.md
├── input
│   └── .gitkeep
├── output
│   └── .gitkeep
├── requirements.txt
└── README.md
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd quantum-image-encryption-vc
   ```
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
1. Run the application:
   ```
   python app.py
   ```
2. Access the user interface through your web browser at `http://localhost:5000`.
3. Follow the prompts to upload an image, encrypt it, and view the results.

## Documentation
Detailed documentation for each module and process can be found in the `docs/implementation` directory. This includes setup instructions, module descriptions, and testing guidelines.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.