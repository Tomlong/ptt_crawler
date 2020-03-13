FROM python:3.7

COPY /crawler/list_crawler/requirements.txt /

RUN pip3 install -U pip && \
    pip3 install --no-cache-dir -r /requirements.txt && rm /requirements.txt

COPY /crawler/list_crawler /app/list_crawler

WORKDIR /app/list_crawler

EXPOSE 80

CMD ["/app/list_crawler/entrypoint.sh"]

HEALTHCHECK --interval=5s --timeout=3s \
    CMD /app/list_crawler/healthcheck.sh