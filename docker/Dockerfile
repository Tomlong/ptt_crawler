FROM python:3.7

COPY requirements.txt /

RUN pip3 install -U pip && \
    pip3 install --no-cache-dir -r /requirements.txt && rm /requirements.txt

COPY . /app

WORKDIR /app

EXPOSE 80

CMD ["/app/entrypoint.sh"]