from schema import Schema, And

CrawlerSchema = Schema({
    "start_time": And(str, len),
    "end_time": And(str, len)
})