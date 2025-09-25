# Use Python slim image
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project folder (inner fixlab_backend)
COPY fixlab_backend/ ./fixlab_backend/

# Copy manage.py
COPY fixlab_backend/manage.py ./fixlab_backend/

# Collect static files (optional)
RUN python ./fixlab_backend/manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run Gunicorn
CMD ["gunicorn", "fixlab_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
