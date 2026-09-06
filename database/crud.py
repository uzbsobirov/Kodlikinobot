from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, update, delete, func, distinct
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from database.base import async_session
from database.models import User, Movie, Episode, Payment, Card, Channel, Setting, Admin
from data.config import sync_admins, ENV_ADMINS

# `settings` jadvalida yagona (id=1) qator kafolatlangan bo'lishi kerak
SETTINGS_ROW_ID = 1

# ==================== USERS ====================

async def get_or_create_user(telegram_id: int, full_name: str, username: Optional[str] = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Ma'lumotlar o'zgargan bo'lsa yangilash
            if user.full_name != full_name or user.username != username:
                user.full_name = full_name
                user.username = username
                await session.commit()
                await session.refresh(user)
        return user

async def get_user(telegram_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def set_premium(telegram_id: int, days: int = 30) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            now = datetime.utcnow()
            if user.is_premium and user.premium_expire_date and user.premium_expire_date > now:
                # Agar obunasi hali tugamagan bo'lsa, muddati ustiga qo'shiladi
                user.premium_expire_date = user.premium_expire_date + timedelta(days=days)
            else:
                user.is_premium = True
                user.premium_expire_date = now + timedelta(days=days)
            await session.commit()
            await session.refresh(user)
            return user
        return None

async def expire_old_premiums() -> List[int]:
    """Muddati o'tgan foydalanuvchilarning PRO statusini bekor qilish"""
    async with async_session() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(User).where(User.is_premium == True, User.premium_expire_date < now)
        )
        expired_users = result.scalars().all()
        expired_ids = []
        for u in expired_users:
            u.is_premium = False
            expired_ids.append(u.telegram_id)
        if expired_ids:
            await session.commit()
        return expired_ids

async def get_users_count() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar_one() or 0

async def get_premium_users_count() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)).where(User.is_premium == True))
        return result.scalar_one() or 0

async def get_all_user_ids() -> List[int]:
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        return [row[0] for row in result.all()]


# ==================== MOVIES & EPISODES ====================

async def add_movie(code: str, title: str, media_type: str = "movie", file_id: Optional[str] = None, description: Optional[str] = None) -> Movie:
    async with async_session() as session:
        clean_code = str(code).strip().lower()
        movie = Movie(
            code=clean_code,
            title=title,
            media_type=media_type,
            file_id=file_id,
            description=description
        )
        session.add(movie)
        await session.commit()
        await session.refresh(movie)
        return movie

async def get_movie_by_code(code: str) -> Optional[Movie]:
    async with async_session() as session:
        clean_code = str(code).strip().lower()
        result = await session.execute(
            select(Movie).options(selectinload(Movie.episodes)).where(Movie.code == clean_code)
        )
        return result.scalar_one_or_none()

async def get_movie_by_id(movie_id: int) -> Optional[Movie]:
    async with async_session() as session:
        result = await session.execute(
            select(Movie).options(selectinload(Movie.episodes)).where(Movie.id == movie_id)
        )
        return result.scalar_one_or_none()

async def delete_movie(code: str) -> bool:
    async with async_session() as session:
        clean_code = str(code).strip().lower()
        result = await session.execute(delete(Movie).where(Movie.code == clean_code))
        await session.commit()
        return result.rowcount > 0

async def get_movies_count() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count(Movie.id)))
        return result.scalar_one() or 0

async def add_episode(movie_id: int, season: int, episode: int, file_id: str, episode_code: Optional[str] = None) -> Episode:
    async with async_session() as session:
        ep_code = episode_code.strip().lower() if episode_code else None
        ep = Episode(
            movie_id=movie_id,
            season=season,
            episode=episode,
            file_id=file_id,
            episode_code=ep_code
        )
        session.add(ep)
        await session.commit()
        await session.refresh(ep)
        return ep

async def get_episode_by_code(episode_code: str) -> Optional[Episode]:
    async with async_session() as session:
        clean_code = str(episode_code).strip().lower()
        result = await session.execute(
            select(Episode).options(selectinload(Episode.movie)).where(Episode.episode_code == clean_code)
        )
        return result.scalar_one_or_none()

async def get_seasons_for_movie(movie_id: int) -> List[int]:
    async with async_session() as session:
        result = await session.execute(
            select(distinct(Episode.season)).where(Episode.movie_id == movie_id).order_by(Episode.season)
        )
        return [row[0] for row in result.all()]

async def get_episodes_by_season(movie_id: int, season: int) -> List[Episode]:
    async with async_session() as session:
        result = await session.execute(
            select(Episode).where(Episode.movie_id == movie_id, Episode.season == season).order_by(Episode.episode)
        )
        return list(result.scalars().all())

async def get_episode(movie_id: int, season: int, episode: int) -> Optional[Episode]:
    async with async_session() as session:
        result = await session.execute(
            select(Episode).where(
                Episode.movie_id == movie_id,
                Episode.season == season,
                Episode.episode == episode
            )
        )
        return result.scalar_one_or_none()


# ==================== PAYMENTS ====================

async def create_payment(user_id: int, amount: int, screenshot_file_id: str) -> Payment:
    async with async_session() as session:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            screenshot_file_id=screenshot_file_id,
            status="kutilmoqda"
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment

async def get_payment(payment_id: int) -> Optional[Payment]:
    async with async_session() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

async def update_payment_status(payment_id: int, new_status: str, expected_status: str = "kutilmoqda") -> bool:
    """
    To'lov holatini atomik ravishda yangilaydi: faqat holat `expected_status`
    bo'lgandagina yangilanadi (bitta SQL UPDATE...WHERE ichida).

    Bu ikki admin bir vaqtda "Tasdiqlash"/"Bekor qilish" tugmasini bossa yuzaga
    keladigan race condition'ning oldini oladi — avval "select, keyin tekshirib,
    keyin yangilash" (check-then-act) yondashuvi atomik emas edi va ikkala admin
    ham eski holatni ko'rib, ikkalasi ham PRO status bera olardi.

    Qaytaradi: True — agar shu chaqiruv holatni haqiqatan ham o'zgartira olgan
    bo'lsa; False — agar to'lov allaqachon boshqa holatga o'tkazilgan bo'lsa.
    """
    async with async_session() as session:
        result = await session.execute(
            update(Payment)
            .where(Payment.id == payment_id, Payment.status == expected_status)
            .values(status=new_status)
        )
        await session.commit()
        return result.rowcount > 0

async def get_total_revenue() -> int:
    """Tasdiqlangan to'lovlardan tushgan umumiy summa (so'mda)"""
    async with async_session() as session:
        result = await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "tasdiqlandi")
        )
        total = result.scalar_one_or_none()
        return int(total) if total else 0

async def get_approved_payments_count() -> int:
    """Tasdiqlangan to'lovlar (PRO xaridlar) soni"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Payment.id)).where(Payment.status == "tasdiqlandi")
        )
        return result.scalar_one() or 0

async def get_approved_payments_history(limit: int = 10) -> list:
    """Tasdiqlangan to'lovlar tarixi (kim qancha to'lagan)"""
    async with async_session() as session:
        result = await session.execute(
            select(Payment, User.full_name, User.username)
            .join(User, User.telegram_id == Payment.user_id, isouter=True)
            .where(Payment.status == "tasdiqlandi")
            .order_by(Payment.id.desc())
            .limit(limit)
        )
        return result.all()


# ==================== CARDS ====================

async def add_card(card_number: str, bank_name: str, card_holder: Optional[str] = None) -> Card:
    async with async_session() as session:
        card = Card(
            card_number=card_number.strip(),
            bank_name=bank_name.strip(),
            card_holder=card_holder.strip() if card_holder else None,
            is_active=True
        )
        session.add(card)
        await session.commit()
        await session.refresh(card)
        return card

async def get_active_cards() -> List[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).where(Card.is_active == True))
        return list(result.scalars().all())

async def get_all_cards() -> List[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).order_by(Card.id.desc()))
        return list(result.scalars().all())

async def toggle_card_status(card_id: int) -> Optional[Card]:
    async with async_session() as session:
        result = await session.execute(select(Card).where(Card.id == card_id))
        card = result.scalar_one_or_none()
        if card:
            card.is_active = not card.is_active
            await session.commit()
            await session.refresh(card)
            return card
        return None

async def delete_card(card_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(delete(Card).where(Card.id == card_id))
        await session.commit()
        return result.rowcount > 0


# ==================== CHANNELS ====================

async def add_channel(channel_id: int, name: str, invite_link: str) -> Channel:
    async with async_session() as session:
        # mavjud bo'lsa yangilash
        result = await session.execute(select(Channel).where(Channel.channel_id == channel_id))
        channel = result.scalar_one_or_none()
        if channel:
            channel.name = name
            channel.invite_link = invite_link
        else:
            channel = Channel(
                channel_id=channel_id,
                name=name,
                invite_link=invite_link
            )
            session.add(channel)
        await session.commit()
        await session.refresh(channel)
        return channel

async def get_all_channels() -> List[Channel]:
    async with async_session() as session:
        result = await session.execute(select(Channel).order_by(Channel.id.asc()))
        return list(result.scalars().all())

async def delete_channel(channel_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(delete(Channel).where(Channel.channel_id == channel_id))
        await session.commit()
        return result.rowcount > 0


# ==================== SETTINGS ====================

async def get_pro_price() -> int:
    async with async_session() as session:
        setting = await session.get(Setting, SETTINGS_ROW_ID)
        if setting:
            return setting.pro_price_month

        # id=1 bilan qat'iy bog'lab qo'yamiz — shu tufayli ikkita so'rov bir
        # vaqtda "topilmadi" holatiga tushib qolsa ham, faqat bittasi qator
        # yarata oladi (PRIMARY KEY constraint ikkinchisini bloklaydi), va
        # `select(Setting)` + `scalar_one_or_none()` hech qachon
        # MultipleResultsFound bilan yiqilmaydi.
        setting = Setting(id=SETTINGS_ROW_ID, pro_price_month=15000)
        session.add(setting)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            setting = await session.get(Setting, SETTINGS_ROW_ID)
        return setting.pro_price_month

async def set_pro_price(new_price: int) -> int:
    async with async_session() as session:
        setting = await session.get(Setting, SETTINGS_ROW_ID)
        if setting:
            setting.pro_price_month = new_price
            await session.commit()
            return new_price

        setting = Setting(id=SETTINGS_ROW_ID, pro_price_month=new_price)
        session.add(setting)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            setting = await session.get(Setting, SETTINGS_ROW_ID)
            setting.pro_price_month = new_price
            await session.commit()
        return new_price


# ==================== ADMINS ====================

async def get_all_admins() -> List[Admin]:
    """Barcha adminlar ro'yxatini olish"""
    async with async_session() as session:
        result = await session.execute(select(Admin).order_by(Admin.id.asc()))
        return list(result.scalars().all())

async def get_all_admin_ids() -> List[int]:
    """Barcha adminlar Telegram ID ro'yxatini olish"""
    async with async_session() as session:
        result = await session.execute(select(Admin.telegram_id))
        return list(result.scalars().all())

async def get_admin_by_tg_id(telegram_id: int) -> Optional[Admin]:
    """Telegram ID bo'yicha adminni topish"""
    async with async_session() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def add_admin(
    telegram_id: int,
    full_name: Optional[str] = None,
    username: Optional[str] = None,
    role: str = "admin",
    added_by: Optional[int] = None
) -> Admin:
    """Yangi admin qo'shish va keshni yangilash"""
    async with async_session() as session:
        result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = Admin(
                telegram_id=telegram_id,
                full_name=full_name,
                username=username,
                role=role,
                added_by=added_by
            )
            session.add(admin)
        else:
            if full_name:
                admin.full_name = full_name
            if username:
                admin.username = username
            admin.role = role
        await session.commit()
        await session.refresh(admin)

    await reload_admins_cache()
    return admin

async def delete_admin(telegram_id: int) -> bool:
    """Adminni o'chirish va keshni yangilash (.env dagi asosiy admin o'chirilmaydi)"""
    if telegram_id in ENV_ADMINS:
        return False

    async with async_session() as session:
        result = await session.execute(delete(Admin).where(Admin.telegram_id == telegram_id))
        await session.commit()
        deleted = result.rowcount > 0

    if deleted:
        await reload_admins_cache()
    return deleted

async def reload_admins_cache() -> List[int]:
    """Baza orqali adminlar keshini yangilash"""
    admin_ids = await get_all_admin_ids()
    sync_admins(admin_ids)
    return admin_ids

async def init_admins_from_env_and_db() -> List[int]:
    """.env dagi adminlarni bazaga kiritish va keshni sinxronlash"""
    async with async_session() as session:
        for env_id in ENV_ADMINS:
            result = await session.execute(select(Admin).where(Admin.telegram_id == env_id))
            existing = result.scalar_one_or_none()
            if not existing:
                # User jadvalidan ismini izlash
                u_res = await session.execute(select(User).where(User.telegram_id == env_id))
                u = u_res.scalar_one_or_none()
                new_admin = Admin(
                    telegram_id=env_id,
                    full_name=u.full_name if u else f"Asosiy Admin ({env_id})",
                    username=u.username if u else None,
                    role="owner"
                )
                session.add(new_admin)
        await session.commit()

    return await reload_admins_cache()

