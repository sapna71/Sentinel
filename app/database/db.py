# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database.models import Base
# from app.database.session import engine

# async def init_db():
#     async with engine.begin() as conn:
#         # In a real app, use Alembic. For hackathon, we'll create all tables.
#         await conn.run_sync(Base.metadata.create_all)

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Base
from app.database.session import engine

async def init_db():
    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)