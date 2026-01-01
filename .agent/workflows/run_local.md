---
description: Run the 4DGS Studio application locally
---
# Running 4DGS Studio Locally

This workflow details how to run the application on a Windows machine with an NVIDIA GPU.

## Prerequisites
1.  **NVIDIA GPU**: Ensure you have drivers installed.
2.  **CUDA Toolkit 11.8**: Must be installed and in PATH.
3.  **Visual Studio Build Tools**: Required for compiling some Python extensions (C++).
4.  **COLMAP**: Must be in your system PATH (type `colmap -h` in terminal to verify).
5.  **FFmpeg**: Must be in your system PATH.

## Installation Steps

1.  **Setup Repository**:
    The setup script clones the external 4DGaussians repository.
    ```powershell
    python scripts/setup.py
    ```

2.  **Create Virtual Environment (Recommended)**:
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install PyTorch (CUDA 11.8)**:
    Standard pip install often grabs CPU version. Use this specific command:
    ```powershell
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```

4.  **Install Project Requirements**:
    ```powershell
    pip install -r requirements.txt
    ```

5.  **Install Submodule Requirements**:
    The 4DGaussians repo has its own requirements, some of which might overlap or require compilation.
    ```powershell
    pip install -r 4DGaussians/requirements.txt
    ```
    *Note: If `diff-gaussian-rasterization` fails to install, ensure your CUDA_HOME environment variable is set correctly.*
    
## Running the App

1.  **Start the Server**:
    ```powershell
    python app.py
    ```

2.  **Access UI**:
    Open your browser to `http://127.0.0.1:7860`.

## Troubleshooting

-   **COLMAP not found**: Add the folder containing `colmap.exe` to your Windows Environment Variables `Path`.
-   **CUDA errors**: Verify `nvcc --version` matches your PyTorch CUDA version.
-   **Extension build errors**: Run `pip install setuptools wheel` and ensure Visual Studio C++ build tools are installed.
