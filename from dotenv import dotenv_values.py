from dotenv import dotenv_values
from sqlalchemy import create_engine, text

u = dotenv_values(".env")["DATABASE_URL"]
u = u.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
e = create_engine(u)
c = e.connect()

print(c.execute(text("SELECT current_database(), current_user, current_schema(), inet_server_addr()::text")).fetchone())

print(c.execute(text("SELECT n.nspname, t.typname FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE t.typname = 'user_role'")).fetchall())