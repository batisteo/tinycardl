#!/usr/bin/env python3

import csv
from asyncio import gather, run
from os import environ, makedirs
from sys import argv
from time import time
from typing import Iterable
from uuid import UUID

from aiocsv import AsyncWriter
from aiofiles import open as aopen
from aioify import aioify
from httpx import AsyncClient, Response
from jose.jwt import get_unverified_claims

mkdir = aioify(obj=makedirs, name="mkdir")

BASE_URL = "https://tinycards.duolingo.com/api/1/"
DIR_IMAGE = "images"
TYPE = {"TEXT": "text", "IMAGE": "imageUrl"}


async def main(compact_ids):
    start = time()
    client = AsyncClient(base_url=BASE_URL, timeout=20)

    token = environ.get("JWT_TOKEN")
    async with client as http:
        if token:
            user_id = get_unverified_claims(token)["sub"]
            r: Response = await http.get(
                f"users/{user_id}/favorites",
                cookies={"jwt_token": token},
                params={"relaxedStrength": True},
            )
            if not r.is_error:
                compact_ids = set(compact_ids) | {
                    fav.get("deck", fav.get("deckGroup"))["compactId"] for fav in r.json()["favorites"]
                }
        stuff = await gather(*{fetch(http, compact_id) for compact_id in compact_ids})
        print(stuff)

    print(round(time() - start, 2), "seconds")


async def fetch(http, compact_id):
    uuids = await get_uuids(http, compact_id)
    decks = await gather(*(grab_deck(http, uuid) for uuid in uuids))

    for deck in decks:
        cards = [
            [get_content(side["concepts"]) for side in card["sides"]]
            for card in deck["cards"]
        ]

        await fetch_images(cards, deck)

        await mkdir(deck["name"], exist_ok=True)
        async with aopen(
            f"{deck['name']}/{deck['slug']}.csv", "w", encoding="utf-8", newline=""
        ) as csvfile:
            record = AsyncWriter(csvfile).writerow
            show = lambda side: " | ".join((fact.popitem()[1]) for fact in side)
            for card in cards:
                await record([show(side) for side in card])

    return compact_id


def get_content(concepts):
    side_content = []
    for concept in concepts:
        fact, fact_type = concept["fact"], concept["fact"]["type"]
        side_content.append(
            {fact_type: fact[TYPE[fact_type]]} if fact_type in TYPE else {}
        )
    return side_content


async def fetch_images(cards, deck):
    urls = (x["IMAGE"] for card in cards for side in card for x in side if "IMAGE" in x)
    async with AsyncClient() as http:
        await gather(*[save(http, deck, image) for image in urls])


async def save(http, deck, url):
    DIR = f"{deck['name']}/{DIR_IMAGE}"
    await mkdir(DIR, exist_ok=True)
    filename = f"{DIR}/{url.split('/')[-1]}.jpeg"

    async with aopen(filename, "ab") as image:
        async with http.stream("GET", url) as r:
            async for chunk in r.aiter_bytes():
                await image.write(chunk)


async def grab_deck(http, uuid: UUID):
    params = {"attribution": True, "expand": True}
    r = await http.get(f"decks/{uuid}", params=params)
    print(".", flush=True, end="")
    return r.json()


async def get_uuids(http, compact_id) -> Iterable[UUID]:
    params = {"relaxedStrength": True, "expand": True}
    deck = await http.get(f"decks/uuid?compactId={compact_id}")
    if not deck.is_error:
        uuids = [deck.json()["uuid"]]
    else:
        group: Response = await http.get(f"deck-groups/uuid?compactId={compact_id}")
        if group.is_error:
            return []
        group_uuid = group.json()["uuid"]
        decks: Response = await http.get(f"deck-groups/{group_uuid}", params=params)
        print([deck["description"] for deck in decks.json()["decks"]])
        uuids = [deck["id"] for deck in decks.json()["decks"]]

    return [UUID(uuid) for uuid in uuids]


def entrypoint():
    _, *compact_ids = argv
    print(compact_ids)
    print("  Fetching.", end="", flush=True)
    run(main(compact_ids))

if __name__ == "__main__":
    entrypoint()
