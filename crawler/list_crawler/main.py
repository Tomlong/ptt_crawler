import os
import aiohttp
import logging
import pymongo
import argparse
from aiohttp import web
from middlewares import format_api_middleware
from article_list_handler import ArticleListHandler
from health_check_handler import HealthCheckHandler

logger = logging.getLogger(__name__)
MB = 1024**2
middlewares = [
    format_api_middleware,
]


async def create_session(app):
    session = aiohttp.ClientSession()
    app["session"] = session


async def close_session(app):
    await app["session"].close()


def create_app():
    MONGO_URI = os.environ.get('MONGO_URI', "mongodb://127.0.0.1:27017")
    DB_NAME = os.environ.get('DB_NAME', "ptt_data")
    db_client = pymongo.MongoClient(MONGO_URI)
    db = db_client[DB_NAME]

    app = web.Application(middlewares=middlewares, client_max_size=10 * MB)
    crawler_interval = int(os.getenv('CRAWLER_INT', 5))
    article_list_crawler = ArticleListHandler(
        db=db, 
        crawler_interval=crawler_interval,
    )
    health_check_handler = HealthCheckHandler()
    app.router.add_route("POST", "/crawl", article_list_crawler.on_post)
    app.router.add_route("GET", "/health_check", health_check_handler.on_get)

    app.on_startup.append(create_session)
    app.on_cleanup.append(close_session)

    return app

if __name__ == "__main__":
    logger_level = os.environ.get('LOGGER_LEVEL', 'INFO')
    if logger_level == 'INFO':
        logging.basicConfig(level=logging.INFO)
    elif logger_level == 'DEBUG':
        logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default="8000")
    args = parser.parse_args()

    app = create_app()
    web.run_app(app, host=args.host, port=args.port)