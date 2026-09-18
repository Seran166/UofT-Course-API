from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Text
from typing import Annotated
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
    prerequisite_course_list: Mapped[str | None] = mapped_column(Text)
    corequisite_course_list: Mapped[str | None] = mapped_column(Text)


CourseCode = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=8,
        pattern=r"^[A-Za-z]{3}[0-9]{3}[HYhy][0-9]$",
        to_upper=True,
    ),
]