import logging
import functools
import json
import datetime
from aiohttp import web
from bson import ObjectId

logger = logging.getLogger(__name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o,datetime.datetime):
            return o.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return json.JSONEncoder.default(self, o)

dumps = functools.partial(json.dumps, cls=JSONEncoder)

@web.middleware
async def format_api_middleware(request: web.Request, handler):
    try:
        handler_result = await handler(request)
        if type(handler_result) == dict:
            return web.json_response(handler_result, dumps=dumps)
        else:
            return handler_result
    except web.HTTPRedirection as e:
        raise
    except web.HTTPNotFound as e:
        logger.exception("")
        data = {"status": "error", "error": "Endpoint not found"}
        return web.json_response(data, status=e.status_code)
    except web.HTTPError as e:
        logger.exception("")
        data = {"status": "error", "error": e.reason}
        return web.json_response(data, status=e.status_code)
    except Exception as e:
        logger.exception("")
        data = {"status": "error", "error": str(e)}
        return web.json_response(data, status=500)
