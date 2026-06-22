import asyncio
import datetime
import logging
from aiogram import Bot

from database import get_unsent_hints, mark_hint_sent
from config import QUESTS_DATA

async def hint_scheduler(bot: Bot):
    while True:
        try:
            unsent_hints = await get_unsent_hints()
            for hint in unsent_hints:
                hint_id = hint['id']
                tg_id = hint['tg_id']
                quest_number = hint['quest_number']
                request_time_str = hint['request_time']
                
                request_time = datetime.datetime.fromisoformat(request_time_str)
                
                quest_data = QUESTS_DATA.get("quests", {}).get(str(quest_number), {})
                delay_seconds = quest_data.get("hint_delay_seconds", 0)
                hint_text = quest_data.get("hint_text", "Підказка відсутня.")
                
                target_time = request_time + datetime.timedelta(seconds=delay_seconds)
                
                if datetime.datetime.now() >= target_time:
                    # Send the hint
                    try:
                        fmt = quest_data.get("hint_message_format", "💡 **ПІДКАЗКА для Квесту {quest_number}**:\n\n{hint_text}")
                        final_text = fmt.format(quest_number=quest_number, hint_text=hint_text)
                        await bot.send_message(chat_id=tg_id, text=final_text)
                        await mark_hint_sent(hint_id)
                        logging.info(f"Sent hint for quest {quest_number} to user {tg_id}")
                    except Exception as e:
                        logging.error(f"Failed to send hint to {tg_id}: {e}")
            
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        
        # Check every 60 seconds
        await asyncio.sleep(60)
