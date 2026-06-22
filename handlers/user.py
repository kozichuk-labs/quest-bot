import os
import re
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from states import QuestStates
from config import QUESTS_DATA
from database import add_or_update_user, update_user_field, log_answer, request_hint, reset_user_progress, increment_pass_count, get_user

user_router = Router()

def get_dialog(key: str, default: str) -> str:
    return QUESTS_DATA.get("dialogs", {}).get(key, default)

def get_quest_dialog(quest_id: str, key: str, default: str) -> str:
    return QUESTS_DATA.get("quests", {}).get(str(quest_id), {}).get(key, default)

def get_quest_keyboard(quest_id: str) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    quest_data = QUESTS_DATA.get("quests", {}).get(str(quest_id))
    if not quest_data:
        return ReplyKeyboardRemove()
        
    delay = quest_data.get("hint_delay_seconds", 0)
    if delay > 0:
        btn_text = get_quest_dialog(quest_id, "hint_button_text", "💡 Взяти підказку")
        builder = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=btn_text)]
        ], resize_keyboard=True, is_persistent=True)
        return builder
    return ReplyKeyboardRemove()

async def send_quest_material(message: Message, current_quest_id: str, next_quest_id: str):
    quest_data = QUESTS_DATA.get("quests", {}).get(str(current_quest_id))
    if not quest_data:
        return

    photo_path = quest_data.get("next_quest_photo")
    description = quest_data.get("next_quest_description")
    next_message = quest_data.get("next_quest_message")
    
    keyboard = get_quest_keyboard(next_quest_id)

    if photo_path and os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        if description:
            await message.answer_photo(photo=photo, caption=description, reply_markup=keyboard)
        else:
            await message.answer_photo(photo=photo, reply_markup=keyboard)
    else:
        if description:
            await message.answer(description, reply_markup=keyboard)

    if next_message:
        await message.answer(next_message)

async def handle_hint_request(message: Message, quest_id: str):
    tg_id = message.from_user.id
    success = await request_hint(tg_id, int(quest_id))
    
    if success:
        msg = get_quest_dialog(quest_id, "hint_requested", "💡 Підказку замовлено! Вона з'явиться тут через заданий час.")
        await message.answer(msg)
    else:
        msg = get_quest_dialog(quest_id, "hint_already_requested", "Ти вже замовляв підказку для цього квесту.")
        await message.answer(msg)

@user_router.message(Command("my_id"))
async def cmd_my_id(message: Message):
    await message.answer(f"Твій Telegram ID: `{message.from_user.id}`\n\nДодай його в `.env` файл до `ADMIN_IDS`, щоб отримати доступ до адмінки.", parse_mode="Markdown")

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await add_or_update_user(message.from_user.id, message.from_user.username, 'WaitName')
    await state.set_state(QuestStates.WaitName)
    start_msg = get_dialog("start", "Привіт! Як тебе звати?")
    await message.answer(start_msg, reply_markup=ReplyKeyboardRemove())

@user_router.message(Command("reset"))
async def cmd_reset(message: Message):
    builder = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Так, почати спочатку")],
        [KeyboardButton(text="Ні, скасувати")]
    ], resize_keyboard=True)
    msg = get_dialog("reset_confirmation", "Ти впевнений, що хочеш скинути свій прогрес?")
    await message.answer(msg, reply_markup=builder)

@user_router.message(F.text == "Так, почати спочатку")
async def process_reset_confirm(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    await increment_pass_count(tg_id)
    await reset_user_progress(tg_id)
    await state.set_state(QuestStates.WaitQuest1)
    
    msg = get_dialog("reset_done", "Прогрес скинуто. Починаємо спочатку!")
    await message.answer(msg, reply_markup=ReplyKeyboardRemove())
    
    start_quest_1_msg = get_dialog("start_quest_1", "Чекаю відповідь на 1 квест в чаті.")
    keyboard = get_quest_keyboard("1")
    await message.answer(start_quest_1_msg, reply_markup=keyboard)

@user_router.message(F.text == "Ні, скасувати")
async def process_reset_cancel(message: Message, state: FSMContext):
    msg = get_dialog("reset_cancelled", "Скидання скасовано.")
    
    # Restore the proper keyboard based on current state
    user = await get_user(message.from_user.id)
    current_state = user['current_state'] if user else ''
    
    keyboard = ReplyKeyboardRemove()
    if 'Quest' in current_state:
        quest_num = current_state.replace('WaitQuest', '')
        if quest_num.isdigit():
            keyboard = get_quest_keyboard(quest_num)
            
    await message.answer(msg, reply_markup=keyboard)

@user_router.message(QuestStates.WaitName)
async def process_name(message: Message, state: FSMContext):
    name = message.text
    if re.search(r'\d', name):
        err_msg = get_dialog("invalid_name", "Ім'я не може містити цифри!")
        await message.answer(err_msg)
        return
        
    await update_user_field(message.from_user.id, 'name', name)
    await update_user_field(message.from_user.id, 'current_state', 'WaitAge')
    
    await state.set_state(QuestStates.WaitAge)
    ask_age_msg = get_dialog("ask_age", "Супер! А скільки тобі років?")
    await message.answer(ask_age_msg)

@user_router.message(QuestStates.WaitAge)
async def process_age(message: Message, state: FSMContext):
    age = message.text
    if not age.isdigit():
        err_msg = get_dialog("invalid_age", "Будь ласка, введи свій вік цифрами.")
        await message.answer(err_msg)
        return
        
    await update_user_field(message.from_user.id, 'age', age)
    await update_user_field(message.from_user.id, 'current_state', 'WaitQuest1')
    
    await state.set_state(QuestStates.WaitQuest1)
    start_quest_1_msg = get_dialog("start_quest_1", "Чекаю відповідь на 1 квест в чаті.")
    keyboard = get_quest_keyboard("1")
    await message.answer(start_quest_1_msg, reply_markup=keyboard)

async def check_quest_answer(message: Message, state: FSMContext, current_quest_id: str, next_quest_id: str, next_state_name: str, next_state_obj):
    user_answer = message.text
    tg_id = message.from_user.id
    
    if re.search(r'\d', user_answer):
        err_msg = get_quest_dialog(current_quest_id, "invalid_quest_answer", "Відповідь не може містити цифри.")
        await message.answer(err_msg)
        return
        
    await log_answer(tg_id, int(current_quest_id), user_answer)
    
    quest_data = QUESTS_DATA.get("quests", {}).get(str(current_quest_id), {})
    correct_answer = quest_data.get("answer", "")
    wrong_answer_msg = get_quest_dialog(current_quest_id, "wrong_answer", "Неправильна відповідь, спробуй ще.")
    
    if user_answer.strip().lower() == correct_answer.lower():
        await update_user_field(tg_id, 'current_state', next_state_name)
        await state.set_state(next_state_obj)
        
        correct_msg = get_quest_dialog(current_quest_id, "correct_answer_message", "Правильно! Ти відгадав.")
        btn_text = get_quest_dialog(current_quest_id, "next_quest_button_text", "Наступний квест ➡️")
        
        builder = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text=btn_text)]
        ], resize_keyboard=True)
        await message.answer(correct_msg, reply_markup=builder)
    else:
        await message.answer(wrong_answer_msg)

@user_router.message(QuestStates.WaitQuest1)
async def process_quest1(message: Message, state: FSMContext):
    hint_btn_text = get_quest_dialog("1", "hint_button_text", "💡 Взяти підказку")
    if message.text == hint_btn_text:
        return await handle_hint_request(message, "1")
    await check_quest_answer(message, state, "1", "2", "WaitTransition2", QuestStates.WaitTransition2)

@user_router.message(QuestStates.WaitTransition2)
async def process_transition2(message: Message, state: FSMContext):
    await update_user_field(message.from_user.id, 'current_state', 'WaitQuest2')
    await state.set_state(QuestStates.WaitQuest2)
    await send_quest_material(message, "1", "2")

@user_router.message(QuestStates.WaitQuest2)
async def process_quest2(message: Message, state: FSMContext):
    hint_btn_text = get_quest_dialog("2", "hint_button_text", "💡 Взяти підказку")
    if message.text == hint_btn_text:
        return await handle_hint_request(message, "2")
    await check_quest_answer(message, state, "2", "3", "WaitTransition3", QuestStates.WaitTransition3)

@user_router.message(QuestStates.WaitTransition3)
async def process_transition3(message: Message, state: FSMContext):
    await update_user_field(message.from_user.id, 'current_state', 'WaitQuest3')
    await state.set_state(QuestStates.WaitQuest3)
    await send_quest_material(message, "2", "3")

@user_router.message(QuestStates.WaitQuest3)
async def process_quest3(message: Message, state: FSMContext):
    hint_btn_text = get_quest_dialog("3", "hint_button_text", "💡 Взяти підказку")
    if message.text == hint_btn_text:
        return await handle_hint_request(message, "3")
    await check_quest_answer(message, state, "3", "4", "WaitTransition4", QuestStates.WaitTransition4)

@user_router.message(QuestStates.WaitTransition4)
async def process_transition4(message: Message, state: FSMContext):
    await update_user_field(message.from_user.id, 'current_state', 'WaitQuest4')
    await state.set_state(QuestStates.WaitQuest4)
    await send_quest_material(message, "3", "4")

@user_router.message(QuestStates.WaitQuest4)
async def process_quest4(message: Message, state: FSMContext):
    current_quest_id = "4"
    hint_btn_text = get_quest_dialog(current_quest_id, "hint_button_text", "💡 Взяти підказку")
    if message.text == hint_btn_text:
        return await handle_hint_request(message, current_quest_id)
        
    user_answer = message.text
    tg_id = message.from_user.id
    
    if re.search(r'\d', user_answer):
        err_msg = get_quest_dialog(current_quest_id, "invalid_quest_answer", "Відповідь не може містити цифри.")
        await message.answer(err_msg)
        return
        
    await log_answer(tg_id, 4, user_answer)
    
    quest_data = QUESTS_DATA.get("quests", {}).get(current_quest_id, {})
    correct_answer = quest_data.get("answer", "")
    final_message = quest_data.get("final_message", "Вітаємо з проходженням квесту!")
    wrong_answer_msg = get_quest_dialog(current_quest_id, "wrong_answer", "Неправильна відповідь, спробуй ще.")
    
    if user_answer.strip().lower() == correct_answer.lower():
        await update_user_field(tg_id, 'current_state', 'completed')
        await increment_pass_count(tg_id)
        await state.set_state(QuestStates.completed) if hasattr(QuestStates, 'completed') else await state.clear()
        await state.update_data(completed=True)
        
        await message.answer(final_message, reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(wrong_answer_msg)

@user_router.message(F.text)
async def process_any_text(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user and user['current_state'] == 'completed':
        msg = get_dialog("no_more_quests", "Більше квестів поки @yurapxl не придумав.")
        await message.answer(msg)
    else:
        pass
