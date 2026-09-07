from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    premium_expire_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    joined_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.telegram_id} full_name={self.full_name}>"


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), default="movie", nullable=False)
    file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    episodes: Mapped[List["Episode"]] = relationship("Episode", back_populates="movie", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Movie id={self.id} code={self.code} title={self.title} type={self.media_type}>"


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    season: Mapped[int] = mapped_column(default=1, nullable=False)
    episode: Mapped[int] = mapped_column(default=1, nullable=False)
    episode_code: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    movie: Mapped["Movie"] = relationship("Movie", back_populates="episodes")

    def __repr__(self) -> str:
        return f"<Episode id={self.id} movie_id={self.movie_id} S{self.season}E{self.episode}>"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    screenshot_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="kutilmoqda", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Payment id={self.id} user_id={self.user_id} amount={self.amount} status={self.status}>"


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_number: Mapped[str] = mapped_column(String(64), nullable=False)
    card_holder: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Card id={self.id} number={self.card_number} bank={self.bank_name}>"


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Instagram va boshqa (tekshirib bo'lmaydigan) havolalarda haqiqiy Telegram
    # chat ID bo'lmaydi, shuning uchun bu maydon endi ixtiyoriy (Optional).
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_link: Mapped[str] = mapped_column(String(255), nullable=False)
    # "telegram" — get_chat_member orqali haqiqiy a'zolik tekshiriladi (majburiy)
    # "other"    — Instagram va shu kabi havolalar, tekshirib bo'lmaydi, faqat ko'rsatiladi
    channel_type: Mapped[str] = mapped_column(String(32), default="telegram", nullable=False)

    def __repr__(self) -> str:
        return f"<Channel id={self.id} channel_id={self.channel_id} name={self.name} type={self.channel_type}>"


class ChannelMembership(Base):
    """
    Katta (ko'p obunachili) kanallarda Telegram get_chat_member() orqali
    ixtiyoriy foydalanuvchining a'zoligini so'rab bo'lmaydi (Bot API
    "member list is inaccessible" xatoligini qaytaradi). Shuning uchun
    a'zolik holatini chat_member yangilanishlaridan kuzatib, shu yerda
    saqlab boramiz — bu kanal hajmidan qat'i nazar ishlaydi.
    """
    __tablename__ = "channel_memberships"
    __table_args__ = (UniqueConstraint("channel_id", "user_id", name="uq_channel_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ChannelMembership channel_id={self.channel_id} user_id={self.user_id} status={self.status}>"


class Setting(Base):
    __tablename__ = "settings"
    # Jadvalda faqat bitta (id=1) qator bo'lishi kafolatlanadi (race condition oldini olish uchun)
    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    pro_price_month: Mapped[int] = mapped_column(BigInteger, default=15000, nullable=False)

    def __repr__(self) -> str:
        return f"<Setting id={self.id} pro_price_month={self.pro_price_month}>"


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), default="admin", nullable=False)  # "owner" yoki "admin"
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Admin id={self.id} tg_id={self.telegram_id} role={self.role}>"

