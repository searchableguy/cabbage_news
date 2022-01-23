from asyncio import sleep
from datetime import timedelta
from aiohttp import ClientSession
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from bs4 import BeautifulSoup
from sanic.log import logger
from .database import News, engine
from .util import unwrap_comments_into_text, keywords_in_sentence, sentiment_analysis

blocked_keywords_in_title = [
    "google",
    "facebook",
    "meta",
    "twitter",
    "reddit",
    "instagram",
    "youtube",
    "linkedin",
    "pinterest",
    "amazon",
    "microsoft",
    "apple",
    "netflix",
    "spotify",
    "quora",
    "bitcoin",
    "military",
    "politics",
    "american",
    "United States",
]

# Not too negativity but neutural or close to it is fine.
sentiment_basepoint = -0.1

async def fetch_page_and_create_news_item(id: str) -> News | None:
    async with ClientSession("https://hn.algolia.com") as client:
        page_endpoint = "/api/v1/items/{id}".format(id=id)
        try:
            page = await client.get(page_endpoint)
            page_json = await page.json()
            title = page_json["title"]
            url = page_json["url"]
            text = page_json["text"]
            children = page_json["children"]
            if text:
                text = BeautifulSoup(text, features="html.parser").get_text()

            contains_blocked_keyword = keywords_in_sentence(
                blocked_keywords_in_title, title
            )

            # Filter out news items with keywords in the title
            if contains_blocked_keyword:
                logger.info(f"{title} filtered because it contains a blocked keyword.")
                return None

            news_item = News(title=title, url=url, text=text)

            if len(children):

                unwrapped_comments = unwrap_comments_into_text(children)

                soup = BeautifulSoup(
                    unwrapped_comments, features="html.parser"
                )

                comments_text = soup.get_text()

                urls_in_content = [ link["href"] for link in soup.find_all("a", href=True) ]

                user_sentiment = sentiment_analysis(comments_text)

                news_item.user_sentiment = user_sentiment
                news_item.urls_in_content = ",".join(urls_in_content)

            return news_item

        except Exception as error:
            logger.error(error)


async def fetch_and_insert_news_items(
    tags: str = "front_page", filter: str = "points>10"
):
    async with ClientSession("https://hn.algolia.com") as client:
        frontpage_endpoint = (
            f"/api/v1/search_by_date?tags={tags}&numericFilters={filter}"
        )

        try:
            frontpage = await client.get(frontpage_endpoint)
            frontpage_json = await frontpage.json()
            async with AsyncSession(engine) as session:

                news: List[News] = []
                items = frontpage_json["hits"]

                for item in items:
                    news_item = await fetch_page_and_create_news_item(item["objectID"])
                    if news_item:
                        news.append(news_item)

                session.add_all(news)

                await session.commit()
        except Exception as error:
            logger.error(error)


async def scheduled_ingest() -> None:
    while True:
        logger.info("Ingesting new news items.")
        await fetch_and_insert_news_items()
        logger.info("Finished ingesting new news items.")
        await sleep(timedelta(hours=6).total_seconds())
