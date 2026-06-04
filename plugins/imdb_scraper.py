import aiohttp
import asyncio

async def async_scrape_imdb_data(title):
    imdb_data = {
        'rating': 'N/A',
        'duration': '24m',
        'ep1_title': 'Episode 1',
        'ep1_thumb': None,
        'ep1_rating': 'N/A',
        'ep1_duration': '24m',
        'ep2_title': 'Episode 2',
        'ep2_thumb': None,
        'ep2_rating': 'N/A',
        'ep2_duration': '24m'
    }

    try:
        async with aiohttp.ClientSession() as session:
            # We'll use TMDb for episode images as it's more reliable than scraping IMDB directly
            # Jikan API for Anime is also very reliable. Let's use Jikan as primary for anime.
            search_url = f"https://api.jikan.moe/v4/anime?q={title}&limit=1"
            async with session.get(search_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data'):
                        anime = data['data'][0]
                        mal_id = anime['mal_id']
                        imdb_data['rating'] = str(anime.get('score', 'N/A'))
                        imdb_data['duration'] = anime.get('duration', '24m').replace(' per ep', '').replace(' min', 'm')

                        # Fetch Episodes
                        ep_url = f"https://api.jikan.moe/v4/anime/{mal_id}/videos/episodes"
                        async with session.get(ep_url) as ep_resp:
                            if ep_resp.status == 200:
                                ep_data = await ep_resp.json()
                                eps = ep_data.get('data', [])
                                eps.reverse() # Jikan sometimes returns newest first, or oldest first. Let's find ep 1.

                                ep1 = next((e for e in eps if e.get('mal_id') == 1), None)
                                ep2 = next((e for e in eps if e.get('mal_id') == 2), None)

                                if ep1:
                                    imdb_data['ep1_title'] = ep1.get('title', 'Episode 1')
                                    if ep1.get('images', {}).get('jpg', {}).get('image_url'):
                                        imdb_data['ep1_thumb'] = ep1['images']['jpg']['image_url']
                                if ep2:
                                    imdb_data['ep2_title'] = ep2.get('title', 'Episode 2')
                                    if ep2.get('images', {}).get('jpg', {}).get('image_url'):
                                        imdb_data['ep2_thumb'] = ep2['images']['jpg']['image_url']

    except Exception as e:
        print(f"Scraper Error: {e}")

    return imdb_data

def scrape_imdb_data(title):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(async_scrape_imdb_data(title))
    except Exception as e:
        return asyncio.run(async_scrape_imdb_data(title))
