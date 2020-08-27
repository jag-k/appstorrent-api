import asyncio
from json import dumps
from os.path import join
from typing import Tuple, Union, Callable, Coroutine

import aiohttp
from bs4 import BeautifulSoup, Tag

CATEGORY = ''
BASE_URL = "https://www.appstorrent.ru"

DEFAULT_SORT = ""

_loop = asyncio.get_event_loop()


def run(coroutine: Coroutine):
    res = _loop.run_until_complete(coroutine)
    return res


class API:
    NAVIGATIONS = None
    NAVIGATIONS_DICT = None
    FILTER = {}

    @staticmethod
    def get_bs(text: bytes) -> BeautifulSoup:
        return BeautifulSoup(text.decode('utf-8'), "lxml")

    @staticmethod
    async def get_response(url: str, **kwargs) -> bytes:
        async with aiohttp.ClientSession(**kwargs) as session:
            async with session.get(url, verify_ssl=False, **kwargs) as resp:
                return await resp.read()

    @staticmethod
    async def get_bs_data(url: str, **kwargs) -> BeautifulSoup:
        return API.get_bs(await API.get_response(url, **kwargs))

    @staticmethod
    async def get_navigation(bs: BeautifulSoup = None) -> Tuple[list, dict]:
        if type(bs) is not BeautifulSoup:
            bs = await API.get_bs_data(BASE_URL)

        navigations = []
        navigations_dict = {}
        for a in bs.find("div", {"class": "list-group2"}).findAll('a'):
            a: Tag
            name, count = list(a.stripped_strings)
            href = a.get("href", '/').lstrip('/')
            if href in API.FILTER:
                navigations.append({
                    "name": name,
                    "href": href,
                    "count": int(count)
                })
                navigations_dict[href] = int(count)
        return navigations, navigations_dict

    @staticmethod
    async def get_data(
            _type: str = None,
            category: str = None,
            sorting: Union[str, int] = None,
            print_percents: bool = False
    ) -> dict:
        if _type not in API.FILTER:
            return {}

        bs = await API.get_bs_data(join(BASE_URL, _type))

        categories = {
            s.get("value").strip('/').rsplit('/', 1)[-1]: s.text

            for s in bs.find(
                "select",
                {"id": "dle_sort", "onchange": "top.location=this.value"}
            ).findAll(
                "option",
                {"hidden": False}
            )
        }

        if category not in categories:
            category = ''

        sort = {
            o.get("value"): {
                "key": o.get("data-value"),
                "value": o.get("value"),
                "name": o.text,
            }
            for o in bs.find("select", {"id": "dle_sort"}).findAll("option")
        }
        if not (sorting in sort or str(sorting) in sort):
            sorting = DEFAULT_SORT

        data: list = await API.FILTER[_type](category=category, percents=print_percents, href=_type, sorting=sorting)

        return {
            "categories": categories,
            "category": category,
            "find_type": _type,
            "sorting": sorting,
            "sort": sort,
            "data": {
                "count": len(data),
                "items": data
            }
        }

    @staticmethod
    def constructor(name: str, attrs: dict, selector_func: Callable, _href: str = '') -> Callable:
        async def dec(category=CATEGORY, href=_href, percents=False, **kwargs):
            res = []
            url = join(BASE_URL, href, category, "page/%s")
            page_number = 1

            bs = await API.get_bs_data(url % page_number, cookies={
                "remember_select": kwargs.get("sorting", DEFAULT_SORT)
            })

            try:
                total_count = API.NAVIGATIONS_DICT[href]

            except TypeError:
                API.NAVIGATIONS, API.NAVIGATIONS_DICT = await API.get_navigation(bs)
                total_count = API.NAVIGATIONS_DICT[href]

            while True:
                have_elements = False
                for tag in bs.findAll(name, attrs):  # type: Tag
                    have_elements = True
                    res.append(selector_func(tag))
                    if percents:
                        print("\r%s%% (%s / %s)" % (
                            int((float(len(res)) / float(total_count)) * 100),
                            len(res),
                            total_count
                        ),
                              end='')

                if not have_elements:
                    if percents:
                        print('\r', end="")
                    return res

                page_number += 1
                bs = await API.get_bs_data(url % page_number, cookies={
                    "remember_select": kwargs.get("sorting", DEFAULT_SORT)
                })

        return dec

    @staticmethod
    def generate_filter():
        API.FILTER = {
            "programs": API.constructor(
                'a',
                {"class": "pr-itema"},
                lambda a: {
                    "href": a.get("href", ""),
                    "id": a.get("href", "").rsplit('/', 1)[-1].rsplit('.', 1)[0],
                    "img": join(BASE_URL, a.find("img", {"class": "program-icon"}).get("src").strip('/')),
                    "title": a.find("div", {"class": "pr-title"}).text,
                    "description": a.find("div", {"class": "pr-desc"}).text,
                    "version": a.find("div", {"class": "pr-desc2"}).text,
                },
                "programs"
            ),
            "games": API.constructor(
                "li",
                {"class": "games-item"},
                lambda li: {
                    "href": li.find('a').get("href", ""),
                    "id": li.find('a').get("href", "").rsplit('/', 1)[-1].rsplit('.', 1)[0],
                    "img": join(BASE_URL, li.find("img", {"class": "games-icon"}).get("src").strip('/')),
                    "title": li.find("div", {"class": "games-title"}).text,
                    "description": ' '.join(filter(bool, li.find("div", {"class": "games-desc"}).text.split())),
                    "category": ''.join(
                        filter(bool, li.find("div", {"class": "games-desc"}).text.split())
                    ).split('/')[1:]
                },
                "games"
            )
        }

        API.NAVIGATIONS, API.NAVIGATIONS_DICT = run(API.get_navigation())


API.generate_filter()


async def main():
    print(dumps(
        await API.get_data("games"),
        ensure_ascii=False,
        indent=2
    ))

if __name__ == '__main__':
    r = run(main())
    print(r)
