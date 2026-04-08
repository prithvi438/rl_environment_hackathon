# --- Phase 1: Build the React Dashboard ---
FROM node:20-slim AS build-ui
WORKDIR /build

# Install dependencies
COPY simulator-ui/package*.json ./
RUN npm install

# Build the project
COPY simulator-ui/ ./
RUN npm run build

# --- Phase 2: Python Backend ---
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Clean and overwrite static folder with the fresh build from Phase 1
RUN rm -rf static/*
COPY --from=build-ui /build/dist ./static

# Set environment variables for HF Spaces
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose HF Spaces default port
EXPOSE 7860

# Create a non-root user (U1000 is default for HF Spaces)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Run the FastAPI server
CMD ["python", "server.py"]
