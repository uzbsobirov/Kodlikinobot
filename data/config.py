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

# PostgreSQL database connection URL
# Masalan: postgresql+asyncpg://user:password@localhost:5432/kodlikinodb
DB_URL = env.str("DB_URL", default="postgresql+asyncpg://postgres:postgres@localhost:5432/kodlikinodb")

# FSM holatlarini saqlash uchun Redis manzili (ixtiyoriy).
# Bo'sh qoldirilsa, MemoryStorage ishlatiladi — bot qayta ishga tushganda
# foydalanuvchilarning joriy jarayoni (masalan, to'lov chekini kutish) yo'qoladi.
# Masalan: redis://localhost:6379/0
REDIS_URL = env.str("REDIS_URL", default="")