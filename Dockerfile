# 1. Base image
FROM python:3.11-slim

# 2. Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 5. Copy the rest of the Django project files
COPY . /app/

# 6. Expose the Django default port
EXPOSE 8000

# 7. Default command to run the server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
