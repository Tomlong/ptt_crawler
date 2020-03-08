import time
import logging
import requests
from bson import ObjectId
from threading import Thread
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo.database import Collection

logger = logging.getLogger(__name__)

PTT_URL_PREFIX = "https://www.ptt.cc"
HOT_BOARD_URL = "https://www.ptt.cc/bbs/hotboards.html"
OVER_18_BOARD = "/bbs/Gossiping/index.html"

class ListCrawler(object):
    def __init__(self, crawler_interval: int, list_collection: Collection, start_time: datetime, end_time: datetime):
        """
        Arguments:
            update_interval {int} -- [polling 間隔時間，單位秒]
            load_map_collection {pymongo.collection.Collection} --
            callback {function} --
        """
        self.list_collection = list_collection
        self.start_time = start_time
        self.end_time = end_time

        # get session with auth over 18 
        self.session = requests.session()
        payload = {
            "from": OVER_18_BOARD,
            "yes":  "yes"
        }
        res = self.session.post(f"{PTT_URL_PREFIX}/ask/over18", data=payload)

        self._crawler = Thread(target=self.start_crawl, args=(crawler_interval, ))
        self._crawler.daemon = True
        self._crawler.start()

    def get_time_from_url(self, url: str):
        return datetime.fromtimestamp(int(url.split('/')[-1].split('.')[1]))

    def get_hot_boards(self):
        res = self.session.get(HOT_BOARD_URL)
        soup = BeautifulSoup(res.text, 'html.parser')
        board_soups = soup.find_all('a', class_="board")

        urls = []
        for soup in board_soups:
            urls.append(f"{PTT_URL_PREFIX}{soup.get('href')}")
        return urls

    def get_article_url(self, article_soups: list, method: str):
        if method == "first":
            for article_soup in article_soups:
                try:
                    article_url = article_soup.a.get('href')
                    break
                except: 
                    continue
        if method == "last":
            for article_soup in article_soups[::-1]:
                try:
                    article_url = article_soup.a.get('href')
                    break
                except: 
                    continue
        return article_url
    
    def get_candidate_url(self, url: str):
        res = self.session.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        article_soups = soup.find_all('div', class_="title")
        first_article_url = self.get_article_url(article_soups, "first")
        first_article_time = self.get_time_from_url(first_article_url)

        diff_time = first_article_time - self.end_time
        diff_days = diff_time.days
        if diff_days == 0:
            return url

        page_soup = soup.find("div", class_="btn-group btn-group-paging")
        pre_page_url = page_soup.find_all("a")[1].get('href')
        index = int(pre_page_url.split('/')[-1].split('.')[0][5:]) + 1

        # find how many index for one day - index_num
        index_num = 0
        while True:
            index_num += 1
            res = self.session.get(f"{PTT_URL_PREFIX}{pre_page_url}")
            now_soup = BeautifulSoup(res.text, 'html.parser')
            # last one article was deleted, then continue
            try:
                article_url = now_soup.find_all('div', class_="title")[-1].a.get('href')
            except:
                page_soup = now_soup.find("div", class_="btn-group btn-group-paging")
                pre_page_url = page_soup.find_all("a")[1].get('href')
                continue

            article_time = self.get_time_from_url(article_url)
            each_diff_time = first_article_time - article_time
            
            if each_diff_time.days > 0:
                break
            page_soup = now_soup.find("div", class_="btn-group btn-group-paging")
            pre_page_url = page_soup.find_all("a")[1].get('href')

        # index_num times 0.8 for estimating index
        index_num = int(index_num * .8)
        start_index = index - (index_num * diff_days)
        board_name = url.split('/')[-2]
        return f"{PTT_URL_PREFIX}/bbs/{board_name}/index{str(start_index)}.html"

    def get_start_url(self, url: str):
        while True:
            res = self.session.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Get last article post time
            article_soups = soup.find_all('div', class_="title")
            # Find existed first_article and last_article of page
            first_article_url = self.get_article_url(article_soups, "first")
            last_article_url = self.get_article_url(article_soups, "last")
            # Get first and last article time
            first_article_time = self.get_time_from_url(first_article_url)
            last_article_time = self.get_time_from_url(last_article_url)

            # end_time between this page's first and last article
            if (self.end_time <= last_article_time) and (self.end_time >= first_article_time):
                return url
            # first_article_time > end_time, get pre-page as next url
            if (first_article_time > self.end_time):
                page_soup = soup.find("div", class_="btn-group btn-group-paging")
                pre_page_url = page_soup.find_all("a")[1].get('href')
                url = f"{PTT_URL_PREFIX}{pre_page_url}"
            else:
                page_soup = soup.find("div", class_="btn-group btn-group-paging")
                next_page_url = page_soup.find_all("a")[2].get('href')
                url = f"{PTT_URL_PREFIX}{next_page_url}"

    def crawl_list(self, url: str, board_name: str):
        article_list = list()
        while True:
            res = self.session.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            article_soups = soup.find_all('div', class_="title")
            # start from the newest article
            for article_soup in article_soups[::-1]:
                try:
                    href = article_soup.a.get('href')
                    article_url = f"{PTT_URL_PREFIX}{href}"
                except:
                    continue
                
                article_time = self.get_time_from_url(article_url)
                if (article_time <= self.end_time) and (article_time >= self.start_time):
                    # write in db
                    result = self.list_collection.find_one({"url": article_url})
                    if not result:
                        self.list_collection.insert_one(
                            {
                                "url": article_url,
                                "board_name": board_name,
                                "post_time": article_time,
                                "status": "pending",
                            }
                        )
                elif (article_time < self.start_time):
                    return

            page_soup = soup.find("div", class_="btn-group btn-group-paging")
            pre_page_url = page_soup.find_all("a")[1].get('href')
            url = f"{PTT_URL_PREFIX}{pre_page_url}"

    def start_crawl(self, crawler_interval: int):
        hot_urls = self.get_hot_boards()

        for url in hot_urls:
            board_name = url.split('/')[-2]
            logger.info(f"Crawl {board_name} from {self.start_time} to {self.end_time}")
            logger.info(f"Get candidate url of {board_name}")
            candidate_url = self.get_candidate_url(url)
            logger.info(f"Get start url")
            start_url = self.get_start_url(candidate_url)
            logger.info(f"Start crawling {board_name} list")
            self.crawl_list(start_url, board_name)
            logger.info(f"Crawling {board_name} finished")

            time.sleep(crawler_interval)
