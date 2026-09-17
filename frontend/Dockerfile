FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY frontend/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY frontend ./frontend

EXPOSE 3000

CMD ["streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0", "--server.port=3000", "--server.headless=true", "--browser.gatherUsageStats=false"]
