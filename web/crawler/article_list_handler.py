import re
import logging
from aiohttp import web
from datetime import datetime
from web.schemas import CrawlerSchema
from pymongo.database import Database
from web.crawler.article_list_crawler import ListCrawler


logger = logging.getLogger(__name__)

class ArticleListHandler():
    def __init__(self, db: Database, crawler_interval: int):
        self.start_time = datetime(2020, 3, 10, 12, 00, 00)
        self.end_time = datetime(2020, 3, 11, 12, 00, 00)

        self.list_collection = db["list_data"]
        self.crawler_interval = crawler_interval
    
    async def on_post(self, request: web.Request):
        data = await request.json()
        CrawlerSchema.validate(data)
        try:    
            self.start_time = datetime.strptime(data["start_time"], "%Y-%m-%dT%H:%M:%SZ")
            self.end_time = datetime.strptime(data["end_time"], "%Y-%m-%dT%H:%M:%SZ")
        except:
            raise web.HTTPServiceUnavailable(reason="Time format is %Y-%m-%dT%H:%M:%SZ")

        self.crawler = ListCrawler(self.crawler_interval, self.list_collection, self.start_time, self.end_time)
        
        return {"status": "OK"}
