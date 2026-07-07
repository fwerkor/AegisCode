FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AEGIS_HOME=/data
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY config ./config
RUN pip install --no-cache-dir -e .[dev]
RUN useradd -m -u 10001 aegis && mkdir -p /data && chown -R aegis:aegis /data /app
USER aegis
EXPOSE 8080
CMD ["python", "-m", "aegis_harness.web", "--host", "0.0.0.0", "--port", "8080"]
