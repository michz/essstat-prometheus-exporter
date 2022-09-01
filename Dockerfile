FROM python:3.10.6-slim-bullseye
WORKDIR /app
COPY requirements.txt exporter.py /app/
RUN pip install -r requirements.txt
ENTRYPOINT [ "/app/exporter.py" ]
