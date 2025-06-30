from datetime import UTC, datetime
from typing import Any, Literal, Optional

import sqlalchemy
from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Types
Length = Literal["short", "medium", "long"]
Level = Literal["beginner", "intermediate", "advanced"]
Format = Literal["narrative", "conversational"]
Voice = Literal["male", "female"]
Status = Literal["pending", "active", "completed", "cancelled", "failed"]
Step = Literal["research", "compose", "voice"]


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
        Length: sqlalchemy.Enum("short", "medium", "long", name="length"),
        Level: sqlalchemy.Enum("beginner", "intermediate", "advanced", name="level"),
        Format: sqlalchemy.Enum("narrative", "conversational", name="format"),
        Voice: sqlalchemy.Enum("male", "female", name="voice"),
        Status: sqlalchemy.Enum(
            "pending", "active", "completed", "cancelled", "failed", name="status"
        ),
        Step: sqlalchemy.Enum("research", "compose", "voice", name="step"),
    }


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apple_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
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


class EpisodeAudio(Base):
    __tablename__ = "episode_audio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String)
    duration: Mapped[int] = mapped_column(Integer)
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

    episode: Mapped["Episode"] = relationship("Episode", back_populates="audio")


class Episode(Base):
    __tablename__ = "episode"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String)
    length: Mapped[Length]
    level: Mapped[Level]
    format: Mapped[Format]
    voice1: Mapped[Voice]
    name1: Mapped[str] = mapped_column(String, nullable=True)
    voice2: Mapped[Optional[Voice]] = mapped_column(nullable=True)
    name2: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Status] = mapped_column(default="pending")
    step: Mapped[Optional[Step]] = mapped_column(nullable=True)

    hatchet_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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
    audio: Mapped[Optional["EpisodeAudio"]] = relationship(
        "EpisodeAudio",
        back_populates="episode",
        cascade="all, delete-orphan",  # Delete audio when episode is deleted
    )


class Podcast(Base):
    __tablename__ = "podcast"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String)
    format: Mapped[Format]
    voice1: Mapped[Voice]
    name1: Mapped[str] = mapped_column(String, nullable=True)
    voice2: Mapped[Optional[Voice]] = mapped_column(nullable=True)
    name2: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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

    user: Mapped["User"] = relationship("User", back_populates="podcasts")

    episodes: Mapped[list["Episode"]] = relationship(
        "Episode", back_populates="podcast", cascade="all, delete-orphan"
    )


# User
class UserBase(BaseModel):
    id: int
    apple_id: str | None
    email: EmailStr | None
    name: str | None
    created_at: datetime


class UserResult(UserBase):
    pass


# Episode
class EpisodeCreate(BaseModel):
    topic: str
    length: Length
    level: Level
    instruction: str | None = None


class EpisodeResult(BaseModel):
    id: int
    podcast_id: int

    topic: str
    length: Length
    level: Level
    instruction: str | None = None

    format: Format
    voice1: Voice
    name1: str
    voice2: Voice | None = None
    name2: str | None = None

    status: Status | None = None
    step: Step | None = None

    created_at: datetime
    updated_at: datetime

    title: str | None = None
    summary: str | None = None
    file_name: str | None = None
    duration: int | None = None


class OngoingEpisodeResult(BaseModel):
    id: int
    podcast_id: int

    topic: str
    length: Length
    level: Level
    instruction: str | None = None

    format: Format
    voice1: Voice
    name1: str
    voice2: Voice | None = None
    name2: str | None = None

    status: Status
    step: Step | None = None

    created_at: datetime
    updated_at: datetime


class EpisodeContentResult(BaseModel):
    id: int

    title: str
    summary: str
    transcript: str

    created_at: datetime
    updated_at: datetime


class EpisodeAudioResult(BaseModel):
    url: str
    expires_at: datetime


# Podcast
class PodcastCreate(BaseModel):
    title: str

    format: Format

    voice1: Voice
    name1: str
    voice2: Voice | None = None
    name2: str | None = None

    description: str | None = None


class PodcastResult(PodcastCreate):
    id: int

    created_at: datetime
    updated_at: datetime

    image_url: str | None = None


class PodcastImageUploadURLResult(BaseModel):
    url: str


# JWT Models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    apple_id: str


class TokenResult(Token):
    pass


class AppleSignInRequest(BaseModel):
    apple_id: str
    email: str | None = None
    full_name: str | None = None


class AuthResult(BaseModel):
    token: Token
    user: UserResult


# Workflows
class EpisodeTaskInput(EpisodeCreate):
    id: int
    format: Format
    voice1: Voice
    name1: str
    voice2: Voice | None = None
    name2: str | None = None

    podcast_id: int


class EpisodeResearchResult(BaseModel):
    result: str
    usage: dict[str, Any]


class EpisodeComposeResult(BaseModel):
    result: str
    usage: dict[str, Any]


class EpisodeComposeResponse(BaseModel):
    title: str
    summary: str
    script: str


class EpisodeVoiceResult(BaseModel):
    result: dict[str, Any]
    usage: dict[str, Any]


class EpisodeTaskFailure(BaseModel):
    error: dict[str, str]
