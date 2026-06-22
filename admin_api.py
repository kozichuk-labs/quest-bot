import json
from aiohttp import web
from aiogram import Bot
import database

async def get_users(request: web.Request):
    users_rows = await database.get_all_users()
    users = [dict(row) for row in users_rows]
    return web.json_response(users)

async def reset_user(request: web.Request):
    tg_id = request.match_info.get('tg_id')
    if not tg_id:
        return web.json_response({"error": "Missing tg_id"}, status=400)
    
    await database.reset_user_progress(int(tg_id))
    return web.json_response({"success": True})

async def send_message(request: web.Request):
    tg_id = request.match_info.get('tg_id')
    try:
        data = await request.json()
        text = data.get('text', '')
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    bot: Bot = request.app['bot']
    try:
        await bot.send_message(chat_id=int(tg_id), text=text)
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

def setup_admin_app(bot: Bot) -> web.Application:
    app = web.Application()
    app['bot'] = bot
    
    # API Routes
    app.router.add_get('/api/users', get_users)
    app.router.add_post('/api/users/{tg_id}/reset', reset_user)
    app.router.add_post('/api/users/{tg_id}/message', send_message)
    
    # Static files for the web app
    async def index(request):
        return web.FileResponse('./webapp/index.html')
    app.router.add_get('/', index)
    
    # Add route for static assets
    import os
    if not os.path.exists('./webapp'):
        os.makedirs('./webapp')
    app.router.add_static('/', './webapp/')
    
    return app
