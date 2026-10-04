from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Text, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from typing import Annotated, Any
from datetime import datetime
from pydantic import StringConstraints

Base = declarative_base()

class Course(Base):
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    breadth: Mapped[str | None] = mapped_column(Text)
    course_hours: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    exclusion: Mapped[str | None] = mapped_column(Text)
    prerequisites: Mapped[str | None] = mapped_column(Text)
    corequisites: Mapped[str | None] = mapped_column(Text)
    recommended: Mapped[str | None] = mapped_column(Text)
    prerequisite_course_list: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    corequisite_course_list: Mapped[list | None] = mapped_column(ARRAY(Text))

class DetailedCourse(Base):
    __tablename__ = "course_cache"
    course_code: Mapped[str] = mapped_column(Text, primary_key=True)
    session_code: Mapped[str] = mapped_column(primary_key=True)
    course_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

CourseCode = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=8,
        pattern=r"^[A-Za-z]{3}[0-9]{3}[HYhy][0-9]$",
        to_upper=True
    ),
]

SessionCode = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=1,
        pattern=r"^[FSYfsy]$",
        to_upper=True
    ),
]

SectionCode = Annotated[
    str,
    StringConstraints(
        min_length=7,
        max_length=7,
        pattern=r"^[A-Za-z]{3}\d{4}$",
        to_upper=True
    ),
]