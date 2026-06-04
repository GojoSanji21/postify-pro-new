import asyncio
from plugins.thumbnail_maker import generate_poster

async def main():
    buf = await generate_poster(
        anime_img_url="https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx113415-bbBWj4pEFseh.jpg",
        title="Jujutsu Kaisen",
        genres="Action, Supernatural",
        synopsis="A boy swallows a cursed talisman - the finger of a demon - and becomes cursed himself.",
        username="Jules"
    )
    with open("test_poster1.png", "wb") as f:
        f.write(buf.getbuffer())

asyncio.run(main())
