FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

RUN useradd -m -u 1000 repopilot
WORKDIR /app

COPY --chown=1000:1000 src/repopilot/__init__.py src/repopilot/security.py src/repopilot/inference_resilience.py /app/src/repopilot/
COPY --chown=1000:1000 hf_space/app.py /app/hf_space/
COPY --chown=1000:1000 hf_space/static/ /app/hf_space/static/

USER 1000

EXPOSE 7860
CMD ["python3", "/app/hf_space/app.py"]
