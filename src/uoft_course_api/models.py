from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY

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
