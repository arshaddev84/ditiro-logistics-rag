FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

ARG EMBEDDING_MODEL_ID=sentence-transformers/all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL_ID}').save('/models/all-MiniLM-L6-v2')"

COPY services ./services
COPY docs ./docs
COPY infra/postgres/seeds/seed_data.py ./infra/postgres/seeds/seed_data.py

ENV DOCS_PATH=/app/docs \
    EMBED_MODEL=/models/all-MiniLM-L6-v2

EXPOSE 8000

CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]