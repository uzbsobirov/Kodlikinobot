from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN", default="")
ENV_ADMINS = [int(admin_id.strip()) for admin_id in env.list("ADMINS", default=[]) if admin_id.strip().isdigit()]
ADMINS = list(ENV_ADMINS)

def sync_admins(db_admin_ids: list[int]):
    all_ids = set(ENV_ADMINS) | set(db_admin_ids)
    ADMINS.clear()
    ADMINS.extend(all_ids)

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

IP = env.str("ip", default="127.0.0.1")

# PostgreSQL database connection URL
# Masalan: postgresql+asyncpg://user:password@localhost:5432/kodlikinodb
DB_URL = env.str("DB_URL", default="postgresql+asyncpg://postgres:postgres@localhost:5432/kodlikinodb")

# Yopiq baza kanali ID si (Kinolar yuklanadigan kanal)
BASE_CHANNEL_ID = env.str("BASE_CHANNEL_ID", default="")
if BASE_CHANNEL_ID.startswith("-100") or (BASE_CHANNEL_ID.startswith("-") and BASE_CHANNEL_ID[1:].isdigit()):
    BASE_CHANNEL_ID = int(BASE_CHANNEL_ID)
elif BASE_CHANNEL_ID.isdigit():
    BASE_CHANNEL_ID = int(f"-100{BASE_CHANNEL_ID}")