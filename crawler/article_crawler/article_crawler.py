import os
import re
import time
import signal
import logging
import pymongo
import requests
from bson import ObjectId
from threading import Thread
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo.database import Collection, Database

logger = logging.getLogger(__name__)

PTT_URL_PREFIX = "https://www.ptt.cc"
OVER_18_BOARD = "/bbs/Gossiping/index.html"


class ArticleCrawler():
    def __init__(self, db: Database, crawler_interval: int):
        self.list_data_collection = db["list_data"]
        self.article_data_collection = db["article_data"]

        self.session = requests.session()
        payload = {
            "from": OVER_18_BOARD,
            "yes":  "yes"
        }
        res = self.session.post(f"{PTT_URL_PREFIX}/ask/over18", data=payload)

        self.crawler_interval = crawler_interval
        self.crawler_each_interval = crawler_interval / 10
        self.loop = Thread(target=self.run_forever)

        self.flag = False

    def run_forever(self):
        while True:
            job = self.list_data_collection.find_one_and_update(
                {"status": "pending"},
                {"$set": {"status": "crawling"}}
            )

            if not job:
                logger.info("Waiting for new article urls...")
                time.sleep(self.crawler_interval)
                if self.flag is True:
                    break
                continue
            
            try:
                logger.info(f"Crawling article_id: {job['_id']}")
                self.start_crawl(job)
                self.list_data_collection.find_one_and_update(
                    {"_id": job["_id"]},
                    {"$set": {"status": "finish"}}
                )
                # stop for a while after crawl each article
                time.sleep(self.crawler_each_interval)

            except Exception as e:
                logger.exception(e)
            if self.flag is True:
                break

            time.sleep(self.crawler_interval)

    def start_crawl(self, job):
        article_url = job["url"]
        res = self.session.get(article_url)
        soup = BeautifulSoup(res.text, "html.parser")

        article_info = {}
        article_info["article_id"] = job["_id"]

        content_soup = soup.find("div", id="main-content")
        information_soup = content_soup.find_all("span", class_="article-meta-value")
        author_split_re = re.compile(r"\(|\)")
        author_split = author_split_re.split(information_soup[0].text)
        # get author Id, Name, board, title
        article_info["authorId"] = author_split[0].strip(' ')
        article_info["authorName"] = author_split[1].strip(' ')
        article_info["board"] = information_soup[1].text
        article_info["title"] = information_soup[2].text

        # get canonicalUrl
        article_info["canonicalUrl"] = article_url
        # get published timestamp from article_url
        article_info["time"] = datetime.fromtimestamp(int(article_url.split('/')[-1].split('.')[1]))

        # get all comments
        comments = []
        comment_soups = soup.findAll("div", class_="push")
        for comment_soup in comment_soups:
            push_tag = comment_soup.find("span", class_="push-tag").text.strip(' ')
            comment_id = comment_soup.find("span", class_="push-userid").text.strip(' ')
            # comment strip by : and space
            comment_content = comment_soup.find("span", class_="push-content").text.strip(' :')
            # comment_time strip by \n and space
            commet_time = comment_soup.find("span", class_="push-ipdatetime").text.strip(' \n')

            comments.append(
                {
                    "pushTag": push_tag,
                    "commentId": comment_id,
                    "commentContent": comment_content,
                    "commetTime": commet_time,
                }
            )
        article_info["comments"] = comments

        self.article_data_collection.update_one(
            {"canonicalUrl": article_url},
            {"$set": article_info}, 
            upsert=True
        )

    def start(self):
        self.loop.start()

    def stop(self):
        self.flag = True


if __name__ == '__main__':
    logger_level = os.environ.get('LOGGER_LEVEL', 'INFO')
    if logger_level == 'INFO':
        logging.basicConfig(level=logging.INFO)
    elif logger_level == 'DEBUG':
        logging.basicConfig(level=logging.DEBUG)

    MONGO_URI = os.environ.get('MONGO_URI', "mongodb://127.0.0.1:27017")
    DB_NAME = os.environ.get('DB_NAME', "ptt_data")
    db_client = pymongo.MongoClient(MONGO_URI)
    db = db_client[DB_NAME]

    crawler_interval = int(os.getenv('CRAWLER_INT', 5))
    crawler = ArticleCrawler(
        db=db,
        crawler_interval=crawler_interval
    )
    def signal_handler(signal, frame):
        logger.debug("Catch stop signal!")
        crawler.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    crawler.start()
    