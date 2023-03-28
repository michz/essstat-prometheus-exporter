FROM python:3.11-slim

WORKDIR /usr/src/app

COPY src/ /usr/src/app/
RUN python -m venv venv && . venv/bin/activate && pip install wheel && pip install -r requirements.txt

ENTRYPOINT ["/bin/sh", "/usr/src/app/entrypoint.sh"]
