import aiosqlite
import datetime

DB_NAME = "quest_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                username TEXT,
                name TEXT,
                age TEXT,
                current_state TEXT DEFAULT 'registration'
            )
        """)
        
        # Try adding pass_count to users if it doesn't exist
        try:
            await db.execute("ALTER TABLE users ADD COLUMN pass_count INTEGER DEFAULT 0")
        except aiosqlite.OperationalError:
            # Column might already exist
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS answers_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                quest_number INTEGER,
                user_answer TEXT,
                timestamp DATETIME
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS hints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                quest_number INTEGER,
                request_time DATETIME,
                sent BOOLEAN DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            return await cursor.fetchone()

async def add_or_update_user(tg_id: int, username: str, current_state: str = 'registration'):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (tg_id, username, current_state)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username=excluded.username,
                current_state=excluded.current_state
        """, (tg_id, username, current_state))
        await db.commit()

async def update_user_field(tg_id: int, field: str, value: str):
    allowed_fields = ['name', 'age', 'current_state']
    if field not in allowed_fields:
        raise ValueError("Invalid field to update")
        
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE tg_id = ?", (value, tg_id))
        await db.commit()

async def log_answer(tg_id: int, quest_number: int, user_answer: str):
    timestamp = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO answers_log (tg_id, quest_number, user_answer, timestamp)
            VALUES (?, ?, ?, ?)
        """, (tg_id, quest_number, user_answer, timestamp))
        await db.commit()

async def get_answers_log(tg_id: int, quest_number: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_answer, timestamp 
            FROM answers_log 
            WHERE tg_id = ? AND quest_number = ?
            ORDER BY timestamp ASC
        """, (tg_id, quest_number)) as cursor:
            return await cursor.fetchall()

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        # Total users
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
            
        # Breakdown by state
        async with db.execute("SELECT current_state, COUNT(*) FROM users GROUP BY current_state") as cursor:
            state_breakdown = await cursor.fetchall()
            
    return total_users, state_breakdown

async def increment_pass_count(tg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET pass_count = pass_count + 1 WHERE tg_id = ?", (tg_id,))
        await db.commit()

async def reset_user_progress(tg_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET current_state = 'WaitQuest1' WHERE tg_id = ?", (tg_id,))
        # Optional: clear answers log? Usually we keep it. We just reset state.
        await db.commit()

async def request_hint(tg_id: int, quest_number: int):
    timestamp = datetime.datetime.now().isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if already requested
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM hints WHERE tg_id = ? AND quest_number = ?", (tg_id, quest_number)) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return False # already requested

        await db.execute("""
            INSERT INTO hints (tg_id, quest_number, request_time, sent)
            VALUES (?, ?, ?, 0)
        """, (tg_id, quest_number, timestamp))
        await db.commit()
        return True

async def get_unsent_hints():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, tg_id, quest_number, request_time FROM hints WHERE sent = 0") as cursor:
            return await cursor.fetchall()

async def mark_hint_sent(hint_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE hints SET sent = 1 WHERE id = ?", (hint_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()
