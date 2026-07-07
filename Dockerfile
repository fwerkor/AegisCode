FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AEGISCODE_HOME=/data
WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY config ./config
RUN pip install --no-cache-dir -e .[dev]
RUN useradd -m -u 10001 aegiscode && mkdir -p /data && chown -R aegiscode:aegiscode /data /workspace
USER aegiscode
EXPOSE 8080
ENTRYPOINT ["aegiscode"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
