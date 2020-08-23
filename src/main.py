#!/usr/bin/env python3

import csv
from asyncio import gather, run
from sys import argv
from os import makedirs
from uuid import UUID
from time import time

from aiofiles import open as aopen
from httpx import AsyncClient


DIR_IMAGE = "images"
TYPE = {"TEXT": "text", "IMAGE": "imageUrl"}


async def main(compact_ids):
    start = time()
    client = AsyncClient(base_url="https://tinycards.duolingo.com/api/1/")

    async with client as http:
        stuff = await gather(*{fetch(http, compact_id) for compact_id in compact_ids})
        print(stuff)

    print(round(time() - start, 2), "seconds")


async def fetch(http, compact_id):
    uuid = await to_uuid(http, compact_id=compact_id)
    deck = await grab_deck(http, uuid)

    cards = [
        [get_content(side["concepts"]) for side in card["sides"]]
        for card in deck["cards"]
    ]

    await fetch_images(cards, compact_id)

    return compact_id


def get_content(concepts):
    side_content = []
    for concept in concepts:
        fact, fact_type = concept["fact"], concept["fact"]["type"]
        side_content.append(
            {fact_type: fact[TYPE[fact_type]]} if fact_type in TYPE else {}
        )
    return side_content


async def fetch_images(cards, compact_id):
    urls = (x["IMAGE"] for card in cards for side in card for x in side if "IMAGE" in x)
    async with AsyncClient() as http:
        await gather(*[save(http, compact_id, image) for image in urls])


async def save(http, compact_id, url):
    DIR = f"{compact_id}/{DIR_IMAGE}"
    makedirs(DIR, exist_ok=True)
    filename = f"{DIR}/{url.split('/')[-1]}.jpeg"

    async with aopen(filename, "ab") as image:
        async with http.stream("GET", url) as r:
            async for chunk in r.aiter_bytes():
                await image.write(chunk)


async def grab_deck(http, uuid: UUID):
    params = {"attribution": True, "expand": True}
    r = await http.get(f"decks/{uuid}", params=params)
    print(".", flush=True)
    return r.json()


async def to_uuid(http, compact_id) -> UUID:
    r = await http.get(f"decks/uuid?compactId={compact_id}")
    print(".", end="", flush=True)
    return UUID(r.json()["uuid"])


if __name__ == "__main__":
    _, *compact_ids = argv
    print("  Fetching.", end="", flush=True)
    run(main(compact_ids))
