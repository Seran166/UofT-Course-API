"""Request constraints and public JSON response contracts for the course API."""

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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


class ErrorResponse(BaseModel):
    """Error body used for missing resources and upstream failures (not HTTP 422)."""

    detail: str = Field(description="Human-readable explanation of the failure.")


class CourseResponse(BaseModel):
    """Stored calendar record; null means no value is recorded in the database."""

    model_config = ConfigDict(from_attributes=True)

    course_code: CourseCode = Field(description="Calendar course code.", examples=["CSC108H1"])
    title: str | None = Field(description="Calendar course title.")
    breadth: str | None = Field(description="Calendar breadth requirement text.")
    course_hours: str | None = Field(description="Calendar contact hours, such as 24L/12T.")
    description: str | None = Field(description="Calendar course description.")
    exclusion: str | None = Field(description="Original exclusion requirement text.")
    prerequisites: str | None = Field(description="Original prerequisite requirement text.")
    corequisites: str | None = Field(description="Original corequisite requirement text.")
    recommended: str | None = Field(description="Recommended preparation text.")
    prerequisite_course_list: list[CourseCode] | None = Field(
        description="Unique prerequisite mentions; AND/OR logic and grade requirements are not preserved."
    )
    corequisite_course_list: list[CourseCode] | None = Field(
        description="Unique corequisite mentions; logical relationships are not preserved."
    )


class MeetingTimeResponse(BaseModel):
    """One meeting's day, times, building, and academic period."""

    day: str = Field(description="Weekday name, or Unknown for an unmapped day.", examples=["Monday"])
    start_time: str = Field(description="Start time in 24-hour HH:MM format.", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(description="End time in 24-hour HH:MM format.", pattern=r"^\d{2}:\d{2}$")
    location_code: str | None = Field(description="Building code, which may be empty or null.", examples=["BA"])
    session_code: str = Field(description="Academic-period identifier, distinct from F/S/Y.", examples=["20269"])
    repetition: str | None = Field(description="Upstream recurrence value.", examples=["WEEKLY"])


class DeliveryModeResponse(BaseModel):
    """An upstream delivery mode associated with an academic period."""

    # The client passes these objects through; preserve extra upstream metadata.
    model_config = ConfigDict(extra="allow")

    session: str = Field(description="Academic-period identifier.", examples=["20271"])
    mode: str = Field(description="Upstream delivery-mode code.", examples=["INPER"])


class SectionResponse(BaseModel):
    """One live lecture, tutorial, or other teaching section."""

    name: SectionCode = Field(description="Full section identifier.", examples=["LEC0101"])
    type: str = Field(description="Human-readable section type.", examples=["Lecture"])
    teach_method: str = Field(description="Teaching-method code.", examples=["LEC", "TUT"])
    section_number: str = Field(description="Section number with leading zeros preserved.", examples=["0101"])
    meeting_times: list[MeetingTimeResponse] = Field(description="Scheduled meetings; empty when none are supplied.")
    instructors: list[str] = Field(description="Instructor names; empty when none are supplied.")
    current_enrolment: int = Field(description="Number of enrolled students.", ge=0)
    max_enrolment: int = Field(description="Section enrolment capacity.", ge=0)
    current_waitlist: int = Field(description="Number of waitlisted students.", ge=0)
    delivery_modes: list[DeliveryModeResponse] = Field(description="Delivery modes by academic period.")
    is_cancelled: bool = Field(description="Whether the section is cancelled.")
    is_tba: bool = Field(description="Whether the upstream TBA flag is set.")
    enrolment_indicator: list[str] = Field(description="Extracted program restrictions, not a complete eligibility check.")


class CourseOfferingResponse(BaseModel):
    """Live course details for one F/S/Y offering, including all section types."""

    name: str = Field(description="Upstream course name.")
    specific_id: str = Field(description="U of T API's internal offering identifier.")
    section: SessionCode = Field(description="F (fall), S (winter), or Y (full academic year).")
    code: CourseCode = Field(description="Calendar course code.")
    description: str | None = Field(description="Upstream course description.")
    prerequisites: str | None = Field(description="Upstream prerequisite text.")
    corequisites: str | None = Field(description="Upstream corequisite text.")
    exclusions: str | None = Field(description="Upstream exclusion text.")
    recommended: str | None = Field(description="Upstream recommended preparation.")
    breadth_s: list[str] | None = Field(description="Upstream breadth requirement descriptions.")
    department: str | None = Field(description="Department name.")
    department_code: str | None = Field(description="Department identifier.")
    credit: float = Field(description="Maximum credit weight reported by the upstream API.")
    sections: list[SectionResponse] = Field(description="All teaching sections in this offering.")


RequirementTextResponse = Annotated[str | None, Field(description="Stored requirement text, or null when absent.")]
PrerequisiteCodesResponse = Annotated[
    list[CourseCode] | None,
    Field(description="Extracted prerequisite mentions, or null; not a logical requirement expression."),
]
PostrequisiteCodesResponse = Annotated[list[CourseCode], Field(description="Stored courses mentioning this prerequisite; may be empty.")]
EnrollmentCountResponse = Annotated[int, Field(description="Current enrolled student count, not remaining capacity.", ge=0)]
