content = """fastapi
uvicorn[standard]
sqlalchemy
pydantic
python-multipart
ultralytics
opencv-python-headless
numpy
supervision
httpx
pytest
pytest-asyncio
pytest-cov
rich
requests
python-dotenv
aiofiles
"""

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")