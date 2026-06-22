from aiogram.fsm.state import State, StatesGroup

class QuestStates(StatesGroup):
    WaitName = State()
    WaitAge = State()
    WaitQuest1 = State()
    WaitQuest2 = State()
    WaitTransition2 = State()
    WaitQuest3 = State()
    WaitTransition3 = State()
    WaitQuest4 = State()
    WaitTransition4 = State()
    completed = State()

class AdminStates(StatesGroup):
    WaitUserId = State()
    WaitMessageText = State()
