import asyncio
from plugins.thumbnail_maker import generate_poster_3
from plugins.imdb_scraper import scrape_imdb_data

async def main():
    imdb_data = scrape_imdb_data('Jujutsu Kaisen')
    buf = await generate_poster_3(
        anime_img_url="https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx113415-bbBWj4pEFseh.jpg",
        title="Jujutsu Kaisen",
        genres="Action, Supernatural",
        synopsis="A boy swallows a cursed talisman - the finger of a demon - and becomes cursed himself. He enters a shaman's school to be able to locate the demon's other body parts and thus exorcise himself.",
        username="Jules",
        imdb_data=imdb_data
    )
    with open("test_poster3.png", "wb") as f:
        f.write(buf.getbuffer())

asyncio.run(main())
