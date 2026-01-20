FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV/DeepFace
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

# Install GPU support specific (conditional)
# RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

COPY . .

# Environment defaults
ENV FLASK_APP=backend/app.py
ENV PYTHONUNBUFFERED=1

CMD ["python", "backend/app.py"]
