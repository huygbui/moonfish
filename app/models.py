from datetime import UTC, datetime
from typing import Any, Literal, Optional

import sqlalchemy
from pydantic import BaseModel, EmailStr
from pydantic.types import UUID4
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Types
Length = Literal["short", "long"]
Format = Literal["interview", "conversation", "story", "analysis"]
Voice = Literal["maya", "jake", "sofia", "alex"]
Status = Literal["pending", "active", "completed", "cancelled", "failed"]
Step = Literal["research", "compose", "voice"]

Tier = Literal["free", "premium"]


# Tables
class Base(DeclarativeBase):
    def to_dict(self) -> dict[str, Any]:
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}

    def update(self, data_dict, exclude=None):
        exclude = set(exclude) if exclude else set()
        valid_keys = {c.key for c in inspect(self).mapper.column_attrs}

        for key, value in data_dict.items():
            if key in valid_keys and key not in exclude:
                setattr(self, key, value)

    type_annotation_map = {
        Length: sqlalchemy.Enum("short", "long", name="length"),
        Format: sqlalchemy.Enum("interview", "conversation", "story", "analysis", name="format"),
        Voice: sqlalchemy.Enum("maya", "jake", "sofia", "alex", name="voice"),
        Status: sqlalchemy.Enum(
            "pending", "active", "completed", "cancelled", "failed", name="status"
        ),
        Step: sqlalchemy.Enum("research", "compose", "voice", name="step"),
    }


class SubscriptionTier(Base):
    __tablename__ = "subscription_tier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tier: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    max_podcasts: Mapped[int] = mapped_column(Integer, nullable=False)
    max_daily_episodes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_daily_extended_episodes: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="subscription_tier")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    subscription_tier_id: Mapped[int] = mapped_column(
        ForeignKey("subscription_tier.id"),
        default=1,
        server_default="1",
        index=True,
        nullable=False,
    )

    subscription_tier: Mapped["SubscriptionTier"] = relationship(
        "SubscriptionTier", back_populates="users"
    )

    podcasts: Mapped[list["Podcast"]] = relationship(
        "Podcast", back_populates="user", cascade="all, delete-orphan"
    )

    episodes: Mapped[list["Episode"]] = relationship(
        "Episode", back_populates="user", cascade="all, delete-orphan"
    )


class EpisodeContent(Base):
    __tablename__ = "episode_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    transcript: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )

    episode_id: Mapped[int] = mapped_column(
        ForeignKey("episode.id", ondelete="CASCADE"),
        index=True,
    )

    episode: Mapped["Episode"] = relationship("Episode", back_populates="content")


class Episode(Base):
    __tablename__ = "episode"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String)
    length: Mapped[Length]
    format: Mapped[Format]
    voice1: Mapped[Voice]
    voice2: Mapped[Optional[Voice]] = mapped_column(nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Status] = mapped_column(default="pending")
    step: Mapped[Optional[Step]] = mapped_column(nullable=True)

    hatchet_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    duration: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
    )

    podcast_id: Mapped[int] = mapped_column(
        ForeignKey("podcast.id", ondelete="CASCADE"),
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="episodes")
    podcast: Mapped["Podcast"] = relationship("Podcast", back_populates="episodes")

    content: Mapped[Optional["EpisodeContent"]] = relationship(
        "EpisodeContent",
        back_populates="episode",
        cascade="all, delete-orphan",  # Delete content when episode is deleted
    )


class Podcast(Base):
    __tablename__ = "podcast"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String)
    format: Mapped[Format]
    voice1: Mapped[Voice]
    voice2: Mapped[Optional[Voice]] = mapped_column(nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )

    thumbnail_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="podcasts")

    episodes: Mapped[list["Episode"]] = relationship(
        "Episode", back_populates="podcast", cascade="all, delete-orphan"
    )


# Subscription
class SubscriptionTierResult(BaseModel):
    id: int
    tier: Tier
    max_podcasts: int
    max_daily_episodes: int
    max_daily_extended_episodes: int


class SubscriptionTierUpdate(BaseModel):
    max_podcasts: int | None = None
    max_daily_episodes: int | None = None
    max_daily_extended_episodes: int | None = None


class UserUsageResult(BaseModel):
    podcasts: int
    daily_episodes: int
    daily_extended_episodes: int

    max_podcasts: int
    max_daily_episodes: int
    max_daily_extended_episodes: int


class UserTierUpdate(BaseModel):
    tier: Tier


# User
class UserBase(BaseModel):
    id: int
    device_id: UUID4 | None
    email: EmailStr | None
    name: str | None
    subscription_tier_id: int
    created_at: datetime


class UserResult(UserBase):
    pass


# Episode
class EpisodeCreate(BaseModel):
    topic: str
    length: Length
    instruction: str | None = None


class EpisodeResult(BaseModel):
    id: int
    podcast_id: int

    topic: str
    length: Length
    instruction: str | None = None

    format: Format
    voice1: Voice
    voice2: Voice | None = None

    status: Status | None = None
    step: Step | None = None

    created_at: datetime
    updated_at: datetime

    title: str | None = None
    summary: str | None = None
    audio_url: str | None = None
    duration: int | None = None


class EpisodeContentResult(BaseModel):
    id: int

    title: str
    summary: str
    transcript: str

    created_at: datetime
    updated_at: datetime


class EpisodeAudioResult(BaseModel):
    url: str


# Podcast
class PodcastCreate(BaseModel):
    title: str

    format: Format

    voice1: Voice
    voice2: Voice | None = None

    description: str | None = None


class PodcastUpdate(PodcastCreate):
    title: str | None = None

    format: Format | None = None

    voice1: Voice | None = None
    voice2: Voice | None = None

    description: str | None = None


class PodcastResult(PodcastCreate):
    id: int

    created_at: datetime
    updated_at: datetime

    image_url: str | None = None
    image_upload_url: str | None = None


class PodcastUpdateResult(PodcastResult):
    pass


class PodcastImageUploadURLResult(BaseModel):
    url: str


# JWT Models
class Token(BaseModel):
    access_token: str
    expires_at: int
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int


class TokenResult(Token):
    pass


class GuestSignInRequest(BaseModel):
    device_id: UUID4


class AuthResult(BaseModel):
    token: Token
    user: UserResult


# Workflows
class EpisodeTaskInput(BaseModel):
    id: int
    topic: str
    length: Length
    instruction: str | None = None
    format: Format
    voice1: Voice
    voice2: Voice | None = None
    podcast_id: int


# Research
class EpisodeResearchOutput(BaseModel):
    result: str
    usage: dict[str, Any]


# Compose
class EpisodeComposeResult(BaseModel):
    title: str
    summary: str
    transcript: str


class EpisodeComposeOutput(BaseModel):
    result: EpisodeComposeResult
    usage: dict[str, Any]


class EpisodeComposeResponse(BaseModel):
    title: str
    summary: str
    script: str


# Voice
class EpisodeVoiceResult(BaseModel):
    file_name: str
    duration: int


class EpisodeVoiceOutput(BaseModel):
    result: EpisodeVoiceResult
    usage: dict[str, Any]


# Failure
class EpisodeTaskFailure(BaseModel):
    error: dict[str, str]
