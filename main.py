import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers.user import user_router
from handlers.admin import admin_router
from scheduler import hint_scheduler
from aiohttp import web
from admin_api import setup_admin_app
from tunnel import start_tunnel, stop_tunnel

async def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    await init_db()
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set in .env file.")
        return

    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register routers
    # Note: admin_router is included first so that admin commands can be caught 
    # even if a user is currently in a state, though aiogram 3 routes based on filters.
    dp.include_router(admin_router)
    dp.include_router(user_router)
    
    # Start scheduler task
    asyncio.create_task(hint_scheduler(bot))
    
    # Start SSH Tunnel for WebApp
    await start_tunnel()
    
    # Setup and start aiohttp web app
    admin_app = setup_admin_app(bot)
    runner = web.AppRunner(admin_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 6767)
    await site.start()
    logging.info("Admin Web App running locally on http://127.0.0.1:6767")
    
    # Start polling
    logging.info("Starting bot...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await stop_tunnel()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
