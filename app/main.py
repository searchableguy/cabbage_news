from datetime import datetime
from contextvars import ContextVar
from sanic import Sanic, response
from sanic.log import logger
from .background import scheduled_ingest
from .database import News, init_db, engine, NewsSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import sessionmaker

app = Sanic("cabbage_news")

_base_model_session_ctx = ContextVar("session")


@app.middleware("request")
async def inject_session(request):
    request.ctx.session = sessionmaker(engine, AsyncSession, expire_on_commit=False)()
    request.ctx.session_ctx_token = _base_model_session_ctx.set(request.ctx.session)


@app.middleware("response")
async def close_session(request, response):
    if hasattr(request.ctx, "session_ctx_token"):
        _base_model_session_ctx.reset(request.ctx.session_ctx_token)
        await request.ctx.session.close()


@app.get("/")
async def index(request):
    return response.json({"message": "Hello World"})


@app.get("/feed")
async def feed(request):
    session = request.ctx.session
    async with session.begin():
        news = await session.execute(select(News).order_by(desc(News.id)).limit(20))
        items = NewsSchema().dump(news.scalars().all(), many=True)
        feed = {
            "version": "https://jsonfeed.org/version/1",
            "title": "Cabbage.news Feed",
            "description": "Curated feed from hackernews",
            "items": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "url": item["url"],
                    "content_text": "\n".join(item["urls_in_content"]),
                    "date_published": item["created_at"],
                    "summary": item["text"],
                }
                for item in items
            ],
        }
        return response.json(feed)


@app.get("/api/news")
async def api_news(request):
    session = request.ctx.session
    async with session.begin():
        news = await session.execute(select(News).order_by(desc(News.id)).limit(20))
        items = NewsSchema().dump(news.scalars().all(), many=True)
        return response.json({"items": items})


@app.get("/health")
async def health(request):
    return response.json({"timestamp": datetime.utcnow().isoformat(), "message": "OK"})


@app.before_server_start
async def init(app: Sanic, loop):
    app.add_task(init_db())
    app.add_task(scheduled_ingest())


@app.before_server_stop
async def cleanup(app: Sanic, loop):
    logger.info("Stopping server")
    app.purge_tasks()
