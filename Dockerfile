FROM python:3-slim

WORKDIR /app

# Install openssh-client in case the tunnel is ever needed inside the container
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-client && \
    rm -rf /var/lib/apt/lists/*

# Optimize layer caching: copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the web app port
EXPOSE 6767

CMD ["python", "main.py"]
