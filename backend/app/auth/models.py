from database import Base
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username : Mapped[str] = mapped_column(unique=True, index=True)
    email : Mapped[str] = mapped_column(unique=True, index=True)
    password : Mapped[str] =  mapped_column()


