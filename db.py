# db.py
#import os
from psycopg_pool import ConnectionPool

#DATABASE_URL = os.environ["DATABASE_URL"]  # Supabase pooled URL (port 6543)
DATABASE_URL = "postgresql://postgres.ckazdosbbrioczxpszlw:06EdnNL6Pi6PnG6U@aws-1-us-east-1.pooler.supabase.com:6543/postgres"

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    # 👇 This disables prepared statements (fixes “prepared statement … does not exist” on transaction pooling)
    kwargs={"prepare_threshold": None},
    min_size=1,
    max_size=10,
)