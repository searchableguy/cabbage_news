from datetime import datetime
from pyclbr import Function
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields
from sanic.log import logger

db_file_name = "cabbage_news.sqlite"
db_url = f"sqlite+aiosqlite:///db/{db_file_name}"
engine = create_async_engine(db_url, echo=True)

Base = declarative_base()


class News(Base):
    __tablename__ = "news"
    id: Optional[int] = Column(Integer, primary_key=True)
    title: str = Column(String)
    url: str = Column(String)
    text: Optional[str] = Column(String, nullable=True)
    urls_in_content: Optional[str] = Column(String, nullable=True)
    icon_url: Optional[str] = Column(String, nullable=True)
    user_sentiment: Optional[float] = Column(Float, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow())
    
    __mapper_args__ = {"eager_defaults": True}

    def __str__(self):
        return self.__tablename__

def urls_in_content_field(news: News):

    if news.urls_in_content:
        return news.urls_in_content.split(",")
    return []

class NewsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = News
        load_instance = True

    urls_in_content = fields.Function(urls_in_content_field)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        news = await session.execute(select(News))
        result = news.scalars().all()
        if len(result):
            logger.info("Database already initialized")
        else:
            news_1 = News(title="Cabbage News 1", url="https://cabbage.news/1")
            news_2 = News(title="Cabbage News 2", url="https://cabbage.news/2")
            news_3 = News(title="Cabbage News 3", url="https://cabbage.news/3")
            session.add(news_1)
            session.add(news_2)
            session.add(news_3)
            await session.commit()
            await session.refresh(news_1)
            await session.refresh(news_2)
            await session.refresh(news_3)
