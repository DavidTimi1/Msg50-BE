ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose django port
EXPOSE 8000

# Run server
CMD ["python3", "-m", "uvicorn", "e2ee_chatapp.asgi:application", "--host=0.0.0.0", "--port=8000"]