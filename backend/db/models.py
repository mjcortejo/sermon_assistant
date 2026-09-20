"""SQLAlchemy ORM models for sermons, notes, and chat."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Sermon(Base):
    __tablename__ = "sermons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    transcript_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    notes: Mapped["GeneratedNotes | None"] = relationship(
        back_populates="sermon",
        uselist=False,
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="sermon",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class GeneratedNotes(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sermon_id: Mapped[int] = mapped_column(ForeignKey("sermons.id"), unique=True)
    main_theme: Mapped[str] = mapped_column(Text, default="")
    scriptures_json: Mapped[str] = mapped_column(Text, default="[]")
    takeaways_json: Mapped[str] = mapped_column(Text, default="[]")
    summary: Mapped[str] = mapped_column(Text, default="")
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
    user_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    sermon: Mapped[Sermon] = relationship(back_populates="notes")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sermon_id: Mapped[int] = mapped_column(ForeignKey("sermons.id"))
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sermon: Mapped[Sermon] = relationship(back_populates="messages")
