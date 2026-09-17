FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt backend/requirements.lock.txt ./backend/
RUN python -m pip install -r backend/requirements.txt \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin cutscope

COPY backend/*.py ./backend/
COPY backend/routes ./backend/routes
COPY backend/services ./backend/services
COPY backend/fixtures ./backend/fixtures

USER 10001:10001
EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2).read()"

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
