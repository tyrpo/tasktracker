from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Teams(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_name: Mapped[str]
    admin_id: Mapped[int]
    join_key: Mapped[str]
    team_id: Mapped[int]


class Users(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    user_name: Mapped[str]
    current_team: Mapped[str | None]


class Tasks(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    deadline: Mapped[str]
    user_id: Mapped[int]
    team_name: Mapped[int]


class UserTeam(Base):
    __tablename__ = "users_teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    team_name: Mapped[str]
