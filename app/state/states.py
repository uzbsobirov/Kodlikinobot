from aiogram.fsm.state import State, StatesGroup

class MovieSearchState(StatesGroup):
    waiting_for_code = State()

class AddMovieState(StatesGroup):
    waiting_for_type = State()         # kino yoki serial
    waiting_for_video = State()        # agar kino bo'lsa video
    waiting_for_code = State()         # unikal kod
    waiting_for_title = State()        # kino/serial nomi
    waiting_for_description = State()  # tavsif/janr

class AddEpisodeState(StatesGroup):
    waiting_for_movie_code = State()   # qaysi serialga
    waiting_for_season = State()       # fasl raqami (masalan 1)
    waiting_for_episode = State()      # qism raqami (masalan 1)
    waiting_for_video = State()        # video fayli
    waiting_for_episode_code = State() # to'g'ridan-to'g'ri qism kodi (ixtiyoriy)

class DeleteMovieState(StatesGroup):
    waiting_for_code = State()

class PaymentState(StatesGroup):
    waiting_for_receipt = State()      # chek skrinshoti (rasm)

class AdminCardState(StatesGroup):
    waiting_for_card_number = State()
    waiting_for_bank_name = State()
    waiting_for_card_holder = State()

class AdminChannelState(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_name = State()
    waiting_for_invite_link = State()
    # Instagram / boshqa (tekshirib bo'lmaydigan) havolalar uchun
    waiting_for_other_name = State()
    waiting_for_other_link = State()

class AdminPriceState(StatesGroup):
    waiting_for_price = State()

class AdminBroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_button = State()
    waiting_for_confirm = State()

class AdminManageState(StatesGroup):
    waiting_for_admin_id = State()

