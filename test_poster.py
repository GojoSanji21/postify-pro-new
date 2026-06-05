import asyncio
import io
from PIL import Image
from plugins.thumbnail_maker import generate_poster_3

async def main():
    imdb_data = {
        "rating": "8.5",
        "duration": "24m",
        "ep1_title": "The Boy Who Became a God",
        "ep1_rating": "8.2",
        "ep1_duration": "24m",
        "ep2_title": "The Hero Returns",
        "ep2_rating": "8.8",
        "ep2_duration": "24m"
    }

    out_bio = await generate_poster_3(
        title="Solo Leveling Season 2",
        genres="Action, Adventure, Fantasy",
        synopsis="In a world where hunters, humans who possess magical abilities, must battle deadly monsters to protect the human race from certain annihilation, a notoriously weak hunter named Sung Jinwoo finds himself in a seemingly endless struggle for survival.",
        username="Anime Fury",
        imdb_data=imdb_data
    )

    with open("poster_output.jpg", "wb") as f:
        f.write(out_bio.read())

    print("Poster saved to poster_output.jpg")

if __name__ == "__main__":
    asyncio.run(main())
