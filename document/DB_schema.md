## DB Schema
article_id 為每筆文章資料的 unique key

### list_data
儲存文章 url 及相關訊息,
unique key: article_id
```json
{
    "_id": article_id,
    "url" : 文章url(string),
    "board_name" : 看板名稱(string),
    "published_time" : 貼文時間(ISODate),
    "status" : 爬取狀況(string)，分為pending、crawling、finish、fail,
}
```

### article_data
儲存文章詳細相關訊息
foreign key: article_id -> list_data
```json
{
    "_id" : article_info_id,
    "canonicalUrl" : 文章完整連結(string),
    "article_id" : article_id,
    "authorId" : 作者ID(string),
    "authorName" : 作者名稱(string),
    "board" : 看板名稱(string),
    "comments" : [
        {
            "pushTag" : 回文標籤(string),
            "commentId" : 回文者ID(string),
            "commentContent" : 回文內容(string),
            "commetTime" : 回文時間(string),
        }
    ],
    "content" : 完整內文(string),
    "post_time" : 貼文時間(ISODate),
    "title" : 標題(string),
}
```