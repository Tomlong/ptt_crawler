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
ANNOUNCE = "公告"
RULE = "板規"

class ListCrawler(object):
    def __init__(self, crawler_interval: int, list_collection: Collection, start_time: datetime, end_time: datetime):
        """
        Arguments:
            start_time {datetime}: the start time of crawling range
            end_time {datetime}: the end time of crawling range
            crawler_interval {int}: stop interval (second) of crawling each board
            list_collection {pymongo.collection.Collection} -- collection
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
                    return article_url
                except: 
                    continue
        if method == "last":
            # ignore announce and rule
            for article_soup in article_soups[::-1]:
                title = article_soup.text.strip('\n')
                if (ANNOUNCE in title) or (RULE in title):
                    continue
                try:
                    article_url = article_soup.a.get('href')
                    return article_url
                except: 
                    continue
        return None

    def get_first_last_time(self, article_soups):
        first_article_url = self.get_article_url(article_soups, "first")
        first_article_time = self.get_time_from_url(first_article_url)
        last_article_url = self.get_article_url(article_soups, "last")
        last_article_time = self.get_time_from_url(last_article_url)

        return first_article_time, last_article_time
    
    def get_candidate_url(self, url: str):
        # Get first and last article posttime
        res = self.session.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        article_soups = soup.find_all('div', class_="title")
        first_article_url = self.get_article_url(article_soups, "first")

        # first_aritcle_url None means that first page do not contain article, then start from pre_page
        if first_article_url is None:
            page_soup = soup.find("div", class_="btn-group btn-group-paging")
            url = page_soup.find_all("a")[1].get('href')
            res = self.session.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            article_soups = soup.find_all('div', class_="title")
        first_article_time, last_article_time = self.get_first_last_time(article_soups)

        # if end_time is between first and last article posttime, then return url
        if (self.end_time <= last_article_time) and (self.end_time >= first_article_time):
            return url
        # end_time later than the latest article, then return url   
        if (self.end_time >= last_article_time):
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
            each_diff_time = last_article_time - article_time
            
            if each_diff_time.days > 0:
                break
            page_soup = now_soup.find("div", class_="btn-group btn-group-paging")
            pre_page_url = page_soup.find_all("a")[1].get('href')

        # index_num times 0.8 for estimating index
        index_num = int(index_num * .8)
        diff_time = last_article_time - self.end_time
        diff_days = diff_time.days
        start_index = index - (index_num * diff_days)
        board_name = url.split('/')[-2]
        return f"{PTT_URL_PREFIX}/bbs/{board_name}/index{str(start_index)}.html"

    def get_start_url(self, url: str):
        # if candidate_url is index.html, it means end_time is in first_page.
        if url.split('/')[-1] == "index.html":
            return url

        while True:
            res = self.session.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Get last article post time
            article_soups = soup.find_all('div', class_="title")
            # Get first and last article time
            first_article_time, last_article_time = self.get_first_last_time(article_soups)

            # end_time between this page's first and last article
            if (self.end_time <= last_article_time) and (self.end_time >= first_article_time):
                return url
            # first_article_time > end_time, get pre-page as next url
            if (first_article_time > self.end_time):
                page_soup = soup.find("div", class_="btn-group btn-group-paging")
                pre_page_url = page_soup.find_all("a")[1].get('href')
                url = f"{PTT_URL_PREFIX}{pre_page_url}"
            # get next-page as next url
            else:
                page_soup = soup.find("div", class_="btn-group btn-group-paging")
                next_page_url = page_soup.find_all("a")[2].get('href')
                url = f"{PTT_URL_PREFIX}{next_page_url}"

    def crawl_list(self, url: str, board_name: str):
        article_list = list()
        while True:
            res = self.session.get(url)
            # if url is index.html, remove sticky article
            if url.split('/')[-1] == "index.html":
                sticky_split = "<div class=\"r-list-sep\"></div>"
                page_without_sticky = res.text.split(sticky_split)[0]
                soup = BeautifulSoup(page_without_sticky, 'html.parser')
            else:
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
                                "published_time": article_time,
                                "status": "pending",
                            }
                        )
                elif (article_time < self.start_time):
                    return

            page_soup = soup.find("div", class_="btn-group btn-group-paging")
            pre_page_url = page_soup.find_all("a")[1].get('href')
            url = f"{PTT_URL_PREFIX}{pre_page_url}"

    def start_crawl(self, crawler_interval: int):
        """
        1. Get all board url of hot board
        2. Crawl the article urls of all hot board which posttime from start_time to end_time
            a. Get candidate url that probably approach start url
            b. Get exactly start url that end_time is between first article and last article posttime of the page
            c. Crawl list and go previous page util article's posttime over start_time
        """

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
