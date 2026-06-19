FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first — Docker caches this layer separately
# so rebuilds are fast when only source code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source after deps — changes here don't invalidate the pip layer
COPY src/ ./src/
COPY api/ ./api/

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
