FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY smartheatpump ./smartheatpump
RUN pip install --no-cache-dir .
# config.json en history.db komen in /data (koppel dit als volume)
WORKDIR /data
ENV SHP_CONFIG=/data/config.json SHP_HISTORY_DB=/data/history.db
EXPOSE 8000
CMD ["smartheatpump", "serve", "--port", "8000"]
