content = '''services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./store_intelligence.db
    restart: unless-stopped

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports:
      - "3000:3000"
    depends_on:
      - api
    restart: unless-stopped
'''

with open("docker-compose.yml", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")