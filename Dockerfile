FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    colmap \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone repo first to cache it (optional, but good for stability)
# OR we can copy the local one if we want the docker generic
# Let's clone inside the build to ensure we have it
RUN git clone https://github.com/hustvl/4DGaussians.git 4DGaussians && \
    cd 4DGaussians && \
    git submodule update --init --recursive

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install 4DGaussian specific deps (submodules often need compile)
# We assume the user might need to run this manually or we try here
# This part is tricky as diff-gaussian-rasterization usually needs CUDA compile
WORKDIR /app/4DGaussians
RUN pip install -r requirements.txt || echo "No requirements found in repo, skipping"

# Copy local app code
WORKDIR /app
COPY . .

# Expose Gradio port
EXPOSE 7860

# Run
CMD ["python", "app.py"]
