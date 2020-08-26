from json import dumps

import aiohttp as aiohttp
from sanic import Sanic
from sanic.request import Request
from sanic.response import redirect, json, text
from appstorrent_api import API, BASE_URL

app = Sanic(__name__)
POST = frozenset({"POST"})
GET_POST = frozenset({"GET", "POST"})
app.api: API


@app.listener('before_server_start')
def init(application, loop):
    application.api = API.create(aiohttp.ClientSession(loop=loop))
    application.api.generate_filter()


@app.listener('after_server_stop')
def finish(application, loop):
    loop.run_until_complete(application.api.session.close())
    loop.close()


@app.route("/games")
async def games(request: Request):
    return json(await request.app.api.get_data("games"))


@app.route("/programs")
async def programs(request: Request):
    return json(await request.app.api.get_data("programs"))


@app.route("/")
async def func(request: Request):
    return text(dumps({
        "parsed": True,
        "url": request.url,
        "raw_url": str(request.raw_url),
        "query_string": request.query_string,
        "args": request.args,
        "query_args": request.query_args,
    }, indent=2, ensure_ascii=False), content_type="application/json")


@app.route("/as")
async def apps_torrent_redirect(request: Request):
    return redirect(BASE_URL)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, auto_reload=True)
