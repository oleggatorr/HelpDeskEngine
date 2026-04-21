from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Импортируем Document для корректного разрешения relationship
# (Chat ссылается на Document из reports)
from app.reports.models import Document  # noqa: F401


# Таблица участников чата (многие-ко-многим)
chat_participants = Table(
    "chat_participants",
    Base.metadata,
    Column("chat_id", Integer, ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

# Таблица прочтений сообщений (многие-ко-многим)
message_reads = Table(
    "message_reads",
    Base.metadata,
    Column("message_id", Integer, ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("read_at", DateTime(timezone=True), server_default=func.now())
)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)  # Название чата
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    is_archived = Column(Integer, default=False, nullable=False)  # Архивирован ли чат
    is_closed = Column(Integer, default=False, nullable=False)    # Закрыт ли чат
    is_anonymized = Column(Integer, default=False, nullable=False)  # Анонимизирован ли чат
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Связи
    document = relationship("Document", backref="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    participants = relationship("User", secondary=chat_participants, backref="chats")

    def __repr__(self):
        return f"<Chat {self.id} - doc:{self.document_id}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # Системное сообщение (без отправителя)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    reads = relationship("User", secondary=message_reads, backref="read_messages")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Message {self.id} - chat:{self.chat_id}>"


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_type = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Связи
    message = relationship("Message", back_populates="attachments")

    def __repr__(self):
        return f"<MessageAttachment {self.id}>"
