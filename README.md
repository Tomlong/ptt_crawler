# ptt_crawler

## 爬蟲簡易說明
1. 給定指定的時間區間，爬蟲會爬取熱門看板的文章
2. 開始時間與結束時間，不可以超過現在時間
3. 結束時間不可早於開始時間

## Docker 安裝步驟
1. Build
```
docker-compose -f docker-compose.yml build
```
2. Execute service
```
docker-compose -f docker-compose.yml up -d
```
3. Stop
```
docker-compose down
```

## 部署多機注意事項
1. 將 docker-compose 內的 mongo service 拿掉
2. 將 list_crawler 和 article_crawler DB 位置指向共用的 mongodb
3. 即可將爬蟲部署到多台機器

## 爬蟲使用教學
1. docker啟動後，list_crawler 預設在 port 19010
2. 請用postman或其他方式 post，parameters 需要 start_time 及 end_time，格式如下:
```
POST /crawl

Header:
Content-Type: application/json
```
* Input json (!表示必要參數)
	* `start_time` (`string!`): 格式為 %Y-%m-%dT%H:%M:%SZ，(Ex: 2020-03-11T01:20:31Z)
    * `end_time` (`string!`): 格式為 "%Y-%m-%dT%H:%M:%SZ" (Ex: 2020-03-12T01:20:31Z)