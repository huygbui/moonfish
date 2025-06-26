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
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )

    podcasts: Mapped[list["Podcast"]] = relationship(
        "Podcast", back_populates="user", cascade="all, delete-orphan"
    )


class PodcastContent(Base):
    __tablename__ = "podcast_content"

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

    podcast_id: Mapped[int] = mapped_column(
        ForeignKey("podcast.id", ondelete="CASCADE"),
        index=True,
    )

    podcast: Mapped["Podcast"] = relationship("Podcast", back_populates="content")


class PodcastAudio(Base):
    __tablename__ = "podcast_audio"

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

    podcast_id: Mapped[int] = mapped_column(
        ForeignKey("podcast.id", ondelete="CASCADE"),
        index=True,
    )

    podcast: Mapped["Podcast"] = relationship("Podcast", back_populates="audio")


class Podcast(Base):
    __tablename__ = "podcast"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String)
    length: Mapped[Length]
    level: Mapped[Level]
    format: Mapped[Format]
    voice: Mapped[Voice]
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

    user: Mapped["User"] = relationship("User", back_populates="podcasts")

    content: Mapped[Optional["PodcastContent"]] = relationship(
        "PodcastContent",
        back_populates="podcast",
        cascade="all, delete-orphan",  # Delete content when podcast is deleted
    )
    audio: Mapped[Optional["PodcastAudio"]] = relationship(
        "PodcastAudio",
        back_populates="podcast",
        cascade="all, delete-orphan",  # Delete audio when podcast is deleted
    )


# User
class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    pass


class UserResult(UserBase):
    id: int
    created_at: datetime


# Podcast
class PodcastCreate(BaseModel):
    topic: str
    length: Length
    level: Level
    format: Format
    voice: Voice
    instruction: str | None = None


class PodcastResult(BaseModel):
    id: int

    topic: str
    length: Length
    level: Level
    format: Format
    voice: Voice
    instruction: str | None = None
    status: Status | None = None
    step: Step | None = None

    created_at: datetime
    updated_at: datetime

    title: str | None = None
    summary: str | None = None
    file_name: str | None = None
    duration: int | None = None


class OngoingPodcastResult(BaseModel):
    id: int

    topic: str
    length: Length
    level: Level
    format: Format
    voice: Voice
    instruction: str | None = None
    status: Status
    step: Step | None = None

    created_at: datetime
    updated_at: datetime


class PodcastContentResult(BaseModel):
    id: int

    title: str
    summary: str
    transcript: str

    created_at: datetime
    updated_at: datetime


class PodcastAudioResult(BaseModel):
    url: str
    expires_at: datetime


# Workflows
class PodcastTaskInput(PodcastCreate):
    id: int


class PodcastResearchResult(BaseModel):
    result: str
    usage: dict[str, Any]


class PodcastComposeResult(BaseModel):
    result: str
    usage: dict[str, Any]


class PodcastComposeResponse(BaseModel):
    title: str
    summary: str
    script: str


class PodcastVoiceResult(BaseModel):
    result: dict[str, Any]
    usage: dict[str, Any]


class PodcastTaskFailure(BaseModel):
    error: dict[str, str]
