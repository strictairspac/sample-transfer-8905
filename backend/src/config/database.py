from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool
from .settings import DATABASE_URL
class Base(DeclarativeBase): pass
# NullPool: every request opens a short connection and closes it on return, so
# idle review sessions never hold (or leak) a database connection or cursor.
engine = create_engine(DATABASE_URL, poolclass=NullPool, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)
def db_session():
    with Session() as db: yield db
