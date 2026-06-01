content = '''FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    libgl1 \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

with open("Dockerfile", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")