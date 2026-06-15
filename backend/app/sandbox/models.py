from database import Base
from sqlalchemy import ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from datetime import datetime
from sqlalchemy import func

class CeleryStatuses(enum.Enum):
    PENDING = "pending"
    STARTED = "started"
    FAILED = "failed"
    SUCCESS = "success"
    RUNNING = "running"


class Job(Base):
    __tablename__ = "jobs"
    uuid: Mapped[str] = mapped_column(primary_key=True)
    task_id : Mapped[str | None] = mapped_column(nullable=True)
    status :  Mapped[CeleryStatuses] = mapped_column(SAEnum(CeleryStatuses))
    user_id : Mapped[int] = mapped_column(ForeignKey('users.id'))
    stdout :  Mapped[str | None] = mapped_column(nullable=True)
    stderr :  Mapped[str | None] = mapped_column(nullable=True)
    created_at : Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at : Mapped[datetime | None] = mapped_column(nullable=True)
