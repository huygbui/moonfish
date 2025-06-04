from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import AnyUrl, EmailStr
from sqlmodel import Field, Relationship, SQLModel


# User
class UserBase(SQLModel):
    email: EmailStr
    first_name: str
    last_name: str


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    podcasts: list["Podcast"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    pass


class UserResult(UserBase):
    id: int
    created_at: datetime


# Podcast
class PodcastBase(SQLModel):
    topic: str
    length: str
    level: str
    format: str
    voice: str
    instruction: str | None = None

    status: str = "pending"
    step: str | None = None

    audio_url: str | None = None
    duration: int | None = None


class PodcastContentBase(SQLModel):
    title: str = Field(default="Untitled", sa_column_kwargs={"server_default": "Untitled"})
    transcript: str


class PodcastAudioBase(SQLModel):
    url: str
    duration: int


class PodcastContent(PodcastContentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    podcast_id: int | None = Field(default=None, foreign_key="podcast.id", ondelete="CASCADE")
    podcast: "Podcast" = Relationship(back_populates="content")


class PodcastAudio(PodcastAudioBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    podcast_id: int | None = Field(default=None, foreign_key="podcast.id", ondelete="CASCADE")
    podcast: "Podcast" = Relationship(back_populates="content")


class Podcast(PodcastBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )

    user_id: int | None = Field(default=None, foreign_key="user.id")
    user: User = Relationship(back_populates="podcasts")

    content: PodcastContent | None = Relationship(back_populates="podcast", cascade_delete=True)


class PodcastCreate(SQLModel):
    topic: str
    length: Literal["short", "medium", "long"]
    level: Literal["beginner", "intermediate", "advanced"]
    format: Literal["narrative", "conversational"]
    voice: Literal["male", "female"]
    instruction: str | None = None


class PodcastResult(PodcastBase):
    id: int
    created_at: datetime
    updated_at: datetime


class PodcastUpdate(SQLModel):
    status: Literal["pending", "active", "completed", "cancelled"] | None = None
    step: Literal["research", "compose", "voice"] | None = None

    title: str | None = None
    audio_url: AnyUrl | None = None
    duration: int | None = None


class PodcastUpdateData(SQLModel):
    status: str | None = None
    step: str
    title: str
    audio_url: str
    duration: int


class PodcastContentCreate(PodcastContentBase):
    pass


class PodcastContentResult(PodcastContentBase):
    id: int
    created_at: datetime
    updated_at: datetime


# Workflows
class PodcastTaskInput(PodcastCreate):
    id: int


class PodcastResearchResult(SQLModel):
    result: str
    usage: dict[str, Any]


class PodcastComposeResult(SQLModel):
    result: str
    usage: dict[str, Any]


class PodcastComposeResponse(SQLModel):
    title: str
    script: str


class PodcastVoiceResult(SQLModel):
    result: str
    usage: dict[str, Any]


class PodcastTaskFailure(SQLModel):
    error: dict[str, str]
