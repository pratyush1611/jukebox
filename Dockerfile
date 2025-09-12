FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends mpv ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install uv
WORKDIR /app
COPY pyproject.toml .
RUN uv pip install --system --no-cache .
COPY VERSION /app/
COPY app/ /app/
ENV MPV_IPC=/tmp/mpv.sock MPV_EXTRA=--ao=null PORT=5000
EXPOSE 5000
CMD ["python","jukebox.py"]
