# Copyright (c) 2026 CGArtLab. CC BY-NC-SA 4.0.
# news-report Docker image
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ ./src/
COPY config/ ./config/
COPY .env.example ./

RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 newsreport
USER newsreport

# Data and output directories
RUN mkdir -p /app/data /app/output && chown -R newsreport:newsreport /app/data /app/output

# Entry point
ENTRYPOINT ["news-report"]
CMD ["--help"]

# Usage:
#   docker build -t news-report .
#   docker run --env-file .env -v $(pwd)/data:/app/data -v $(pwd)/output:/app/output news-report --full
#
# With SearXNG:
#   docker run --env-file .env --network host \
#     -v $(pwd)/data:/app/data -v $(pwd)/output:/app/output \
#     news-report --full
