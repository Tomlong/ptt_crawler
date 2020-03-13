from aiohttp import web


class HealthCheckHandler():
    def __init__(self):
        pass

    def on_get(self, req):
        return {"status": "OK"}
