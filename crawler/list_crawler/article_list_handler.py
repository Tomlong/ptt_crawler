from aiohttp import web
from datetime import datetime
from schemas import CrawlerSchema
from pymongo.database import Database
from article_list_crawler import ListCrawler


class ArticleListHandler():
    def __init__(self, db: Database, crawler_interval: int):
        self.start_time = datetime(2020, 3, 10, 12, 00, 00)
        self.end_time = datetime(2020, 3, 11, 12, 00, 00)

        self.list_collection = db["list_data"]
        self.crawler_interval = crawler_interval
    def check_time(self):
        if self.start_time >= self.end_time:
            raise web.HTTPServiceUnavailable(reason="start_time is later than end_time.")
        
        if (self.start_time > datetime.now()) or (self.end_time > datetime.now()):
            raise web.HTTPServiceUnavailable(reason="start_time or end_time is later than now.")
    async def on_post(self, request: web.Request):
        data = await request.json()
        CrawlerSchema.validate(data)

        try:    
            self.start_time = datetime.strptime(data["start_time"], "%Y-%m-%dT%H:%M:%SZ")
            self.end_time = datetime.strptime(data["end_time"], "%Y-%m-%dT%H:%M:%SZ")
        except:
            raise web.HTTPServiceUnavailable(reason="Time format is %Y-%m-%dT%H:%M:%SZ")
        
        self.check_time()

        self.crawler = ListCrawler(self.crawler_interval, self.list_collection, self.start_time, self.end_time)
        
        return {"status": "OK"}
