FROM python:3.12-slim

# Apply current OS security updates before installing the application.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DEFAULT_TIMEOUT=30 PIP_RETRIES=3
COPY pyproject.toml README.md ./
COPY App ./App
RUN pip install --no-cache-dir "setuptools>=68" wheel \
	&& pip install --no-cache-dir --no-build-isolation .
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
USER app
EXPOSE 8000
CMD ["uvicorn", "App.main:app", "--host", "0.0.0.0", "--port", "8000"]
