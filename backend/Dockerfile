FROM python:3.9.16-slim

WORKDIR /app

COPY ./requirements.txt /app

RUN python3 -m pip install -r requirements.txt \
    && rm -rf /root/.cache/pip/

COPY ./melodicnet /app/melodicnet
COPY ./app.py /app
COPY ./wsgi.py /app

ARG MODEL_CONFIG_PATH
COPY ${MODEL_CONFIG_PATH} /app/model_config

CMD ["gunicorn", "-w 1", "-b :8080", "wsgi:app"]