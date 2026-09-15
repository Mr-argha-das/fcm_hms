FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
# Swap opencv-python (needs libGL, absent in slim image) for the headless build,
# and add pytz which requirements.txt is missing.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y opencv-python \
    && pip install --no-cache-dir pytz opencv-python-headless==4.13.0.92

COPY . .

EXPOSE 8000
# ${PORT:-8000} lets hosting platforms (Render/Railway/Fly) inject their port
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
