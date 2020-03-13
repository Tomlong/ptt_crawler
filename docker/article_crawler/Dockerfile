FROM python:3.7

COPY /crawler/article_crawler/requirements.txt /

RUN pip3 install -U pip && \
    pip3 install --no-cache-dir -r /requirements.txt && rm /requirements.txt

COPY /crawler/article_crawler /app/article_crawler

WORKDIR /app/article_crawler

CMD ["/app/article_crawler/entrypoint.sh"]

HEALTHCHECK --interval=5s --timeout=3s \
    CMD /app/article_crawler/healthcheck.sh