# db.py
import os
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")  

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    # 👇 This disables prepared statements (fixes “prepared statement … does not exist” on transaction pooling)
    kwargs={"prepare_threshold": None},
    min_size=1,
    max_size=10,
)