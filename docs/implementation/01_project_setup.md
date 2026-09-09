# Project Setup for Quantum Image Encryption + Visual Cryptography

## Overview
This document outlines the steps required to set up the project environment for the Quantum Image Encryption + Visual Cryptography application. It includes instructions for installing dependencies, configuring the environment, and running the application.

## Prerequisites
Before setting up the project, ensure that you have the following installed on your system:
- Python 3.7 or higher
- pip (Python package installer)

## Step 1: Clone the Repository
Start by cloning the project repository from GitHub (or your version control system):
```bash
git clone <repository-url>
cd quantum-image-encryption-vc
```

## Step 2: Create a Virtual Environment
It is recommended to create a virtual environment to manage project dependencies:
```bash
python -m venv venv
```

## Step 3: Activate the Virtual Environment
Activate the virtual environment using the following command:
- On Windows:
```bash
venv\Scripts\activate
```
- On macOS/Linux:
```bash
source venv/bin/activate
```

## Step 4: Install Dependencies
Install the required dependencies listed in the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

## Step 5: Verify Installation
To ensure that all dependencies are installed correctly, you can run the following command:
```bash
pip list
```
This should display a list of installed packages, including `qiskit`, `opencv-python`, `numpy`, `matplotlib`, and `Pillow`.

## Step 6: Run the Application
You can now run the application using the following command:
```bash
python app.py
```
This will start the web server, and you can access the user interface in your web browser at `http://localhost:5000`.

## Step 7: Explore the User Interface
Once the application is running, you can navigate through the user interface to upload images, encrypt them, generate shares, and view metrics.

## Conclusion
You have successfully set up the Quantum Image Encryption + Visual Cryptography project. Follow the subsequent documentation for detailed information on each module and functionality.