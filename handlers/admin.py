import os
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from config import ADMIN_IDS, QUESTS_DATA
from states import QuestStates, AdminStates
from database import get_stats, get_answers_log, get_user, update_user_field, reset_user_progress, increment_pass_count
from tunnel import get_webapp_url

admin_router = Router()

def is_admin(tg_id: int) -> bool:
    return tg_id in ADMIN_IDS

def get_admin_keyboard():
    webapp_url = get_webapp_url()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Відкрити Web Адмінку", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👤 Керування юзером", callback_data="admin_manage_user")]
    ])

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    await state.clear()
    await message.answer("🔧 **Панель Адміністратора**", reply_markup=get_admin_keyboard())

@admin_router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    total_users, state_breakdown = await get_stats()
    
    response = f"📊 **Статистика бота:**\n\nВсього користувачів: {total_users}\n\n**Розподіл за етапами:**\n"
    for state_name, count in state_breakdown:
        response += f"- {state_name}: {count} користувачів\n"
        
    await callback.message.edit_text(response, reply_markup=get_admin_keyboard())
    await callback.answer()

@admin_router.callback_query(F.data == "admin_manage_user")
async def cb_admin_manage_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
        
    await state.set_state(AdminStates.WaitUserId)
    await callback.message.answer("Введіть Telegram ID користувача:")
    await callback.answer()

@admin_router.message(AdminStates.WaitUserId)
async def process_admin_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    try:
        target_tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID має бути числом. Спробуйте ще раз або введіть /admin для виходу.")
        return
        
    user = await get_user(target_tg_id)
    if not user:
        await message.answer("Користувача не знайдено в базі даних.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
        
    info = (
        f"👤 **Користувач {target_tg_id}**\n"
        f"Username: @{user['username']}\n"
        f"Ім'я: {user['name']}\n"
        f"Вік: {user['age']}\n"
        f"Поточний етап: {user['current_state']}\n"
        f"Кількість проходжень: {user.get('pass_count', 0)}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Скинути прогрес", callback_data=f"admin_reset_{target_tg_id}")],
        [InlineKeyboardButton(text="📝 Лог відповідей", callback_data=f"admin_logs_{target_tg_id}")],
        [InlineKeyboardButton(text="✉️ Надіслати повідомлення", callback_data=f"admin_msg_{target_tg_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await message.answer(info, reply_markup=keyboard)
    await state.clear()

@admin_router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔧 **Панель Адміністратора**", reply_markup=get_admin_keyboard())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_reset_"))
async def cb_admin_reset_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
        
    target_tg_id = int(callback.data.split("_")[2])
    
    # We must clear the target user's FSM state as well
    target_key = StorageKey(bot_id=callback.bot.id, chat_id=target_tg_id, user_id=target_tg_id)
    target_state = FSMContext(storage=state.storage, key=target_key)
    
    await target_state.set_state(QuestStates.WaitQuest1)
    await reset_user_progress(target_tg_id)
    
    await callback.message.answer(f"✅ Прогрес користувача {target_tg_id} скинуто до Квесту 1.", reply_markup=get_admin_keyboard())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_logs_"))
async def cb_admin_logs_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    target_tg_id = int(callback.data.split("_")[2])
    
    response = f"📝 **Логи відповідей для {target_tg_id}:**\n\n"
    
    for q_num in range(1, 5):
        logs = await get_answers_log(target_tg_id, q_num)
        if logs:
            response += f"**Квест {q_num}:**\n"
            for log in logs[-5:]: # show last 5 attempts
                response += f"- {log['user_answer']} ({log['timestamp']})\n"
            response += "\n"
            
    if response == f"📝 **Логи відповідей для {target_tg_id}:**\n\n":
        response = "Немає збережених відповідей для цього користувача."
        
    await callback.message.answer(response, reply_markup=get_admin_keyboard())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_msg_"))
async def cb_admin_msg_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
        
    target_tg_id = int(callback.data.split("_")[2])
    await state.set_state(AdminStates.WaitMessageText)
    await state.update_data(target_tg_id=target_tg_id)
    
    await callback.message.answer(f"Введіть текст повідомлення для користувача {target_tg_id}:")
    await callback.answer()

@admin_router.message(AdminStates.WaitMessageText)
async def process_admin_msg_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    data = await state.get_data()
    target_tg_id = data.get("target_tg_id")
    text_to_send = message.text
    
    try:
        await message.bot.send_message(chat_id=target_tg_id, text=text_to_send)
        await message.answer(f"✅ Повідомлення успішно надіслано користувачу {target_tg_id}.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Помилка при надсиланні: {e}", reply_markup=get_admin_keyboard())
        
    await state.clear()
