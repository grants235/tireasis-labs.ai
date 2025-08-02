FROM --platform=linux/amd64 openmined/tenseal:latest

# Set working directory  
WORKDIR /app

# Copy requirements and install additional Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app || echo "User may already exist"
RUN chown -R app:app /app || echo "Ownership already set"
USER app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run the application
CMD ["python", "app.py"]