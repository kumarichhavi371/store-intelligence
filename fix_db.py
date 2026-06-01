content = (
    "from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean\n"
    "from sqlalchemy.orm import declarative_base, sessionmaker\n"
    "import os\n"
    "\n"
    "DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./store_intelligence.db')\n"
    "\n"
    "engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})\n"
    "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n"
    "Base = declarative_base()\n"
    "\n"
    "\n"
    "class EventRecord(Base):\n"
    "    __tablename__ = 'events'\n"
    "    event_id    = Column(String, primary_key=True, index=True)\n"
    "    store_id    = Column(String, index=True)\n"
    "    camera_id   = Column(String)\n"
    "    visitor_id  = Column(String, index=True)\n"
    "    event_type  = Column(String, index=True)\n"
    "    timestamp   = Column(String, index=True)\n"
    "    zone_id     = Column(String, nullable=True)\n"
    "    dwell_ms    = Column(Integer, default=0)\n"
    "    is_staff    = Column(Boolean, default=False)\n"
    "    confidence  = Column(Float)\n"
    "    queue_depth = Column(Integer, nullable=True)\n"
    "    sku_zone    = Column(String, nullable=True)\n"
    "    session_seq = Column(Integer, default=0)\n"
    "\n"
    "\n"
    "def create_tables():\n"
    "    Base.metadata.create_all(bind=engine)\n"
    "\n"
    "\n"
    "def get_db():\n"
    "    db = SessionLocal()\n"
    "    try:\n"
    "        yield db\n"
    "    finally:\n"
    "        db.close()\n"
)

with open("app/database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done! Verifying...")
with open("app/database.py", "r") as f:
    print(f.read())