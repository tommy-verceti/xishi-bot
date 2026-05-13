"""V2 Engine entry point.

Starts: DB init, sticker seeding, scheduler, web panel, WS relay.
"""

import asyncio
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from db.database import get_db, init_db

STICKERS_DIR = os.path.join(os.path.dirname(__file__), "stickers", "files")


def setup_logging() -> None:
    os.makedirs(CONFIG.log_dir, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, CONFIG.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(CONFIG.log_dir, "v2-engine.log"), encoding="utf-8"
            ),
        ],
    )


async def main() -> None:
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("V2 Engine starting...")

    # Init DB
    db = await get_db()
    await init_db(db)
    logger.info("Database initialized at %s", CONFIG.db_path)

    # Phase 3: Seed stickers
    from stickers.library import seed_stickers
    await seed_stickers(db, STICKERS_DIR)
    await db.close()

    # Phase 4: Start scheduler (APScheduler runs in its own thread)
    from scheduler.scheduler import start_scheduler
    start_scheduler()

    # Phase 6: Start web panel in background thread
    from web.app import start_web

    def run_web() -> None:
        start_web()

    web_thread = threading.Thread(target=run_web, daemon=True, name="web-panel")
    web_thread.start()
    logger.info("Web panel starting on http://%s:%s", CONFIG.web_host, CONFIG.web_port)

    # Phase 0-3: Start WS relay (blocks forever)
    from router import main as run_router

    logger.info("WS relay on %s:%s", CONFIG.listen_host, CONFIG.listen_port)
    await run_router()


if __name__ == "__main__":
    asyncio.run(main())
