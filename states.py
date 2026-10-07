"""FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class ProtocolForm(StatesGroup):
    # Asosiy qadamlar (nomi steps.STEPS dagi kalit bilan bir xil)
    approver_position = State()
    approver_name = State()
    university = State()
    faculty = State()
    event_name = State()
    event_type = State()
    number = State()
    date = State()
    city = State()
    participants = State()
    venue = State()
    count = State()
    time = State()
    agenda = State()
    heard = State()
    photos = State()
    decisions = State()
    secretary = State()
    signers = State()

    # Yordamchi holatlar
    event_type_custom = State()
    block_manual = State()      # Kun tartibi / Eshitildi / Qarorlarni qo'lda yozish
    block_review = State()      # AI yozgan matnni ko'rib chiqish
    heard_hint = State()        # AI uchun izoh
    signer_position = State()
    signer_name = State()

    summary = State()
    format_select = State()


class SettingsForm(StatesGroup):
    value = State()
