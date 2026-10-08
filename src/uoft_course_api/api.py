"""HTTP endpoints for stored calendar information and live timetable offerings."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uoft_course_api.create_engine import engine, AsyncSessionLocal
from typing import Annotated, Any

import uoft_course_api.models as models
from uoft_course_api.models import Course
from uoft_course_api.uoft_client import get_all_sessions, call_uoft_api, course_json
from uoft_course_api.uoft_client import UoftAPIError, UoftAPITimeout
from uoft_course_api.schemas import SectionCode, SessionCode, CourseCode
from uoft_course_api.schemas import (
    CourseResponse, CourseOfferingResponse, SectionResponse, ErrorResponse,
    RequirementTextResponse, PrerequisiteCodesResponse, PostrequisiteCodesResponse,
    EnrollmentCountResponse,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create missing database tables at startup and dispose the engine at shutdown."""
    async with engine.begin() as connection:
        await connection.run_sync(
            models.Base.metadata.create_all
        )

    yield

    await engine.dispose()

app = FastAPI(
    title="U of T Course API",
    description=(
        "Access stored calendar information and live timetable offerings. "
        "Course codes use values such as CSC108H1. Timetable session_code values "
        "are F, S, or Y (fall, winter, or full academic year); they are distinct "
        "from academic-period identifiers. The upstream client currently searches "
        "20269, 20271, and 20269-20271. Timetable results are fetched on each "
        "request and are not cached. Stored calendar fields may be null when "
        "no value has been recorded."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "Courses", "description": "Stored calendar records and live course details."},
        {"name": "Prerequisites", "description": "Requirement text and extracted course mentions."},
        {"name": "Timetable", "description": "Live sections, instructors, meetings, and enrolment."},
    ],
    lifespan=lifespan,
)

COURSE_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "The course is not in the database."},
}
TIMETABLE_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "The stored course/title, requested offering, or section was not found."},
    502: {"model": ErrorResponse, "description": "The U of T API failed or returned unusable data."},
    504: {"model": ErrorResponse, "description": "The U of T API request timed out."},
}


@app.exception_handler(UoftAPIError)
async def upstream_error_handler(request, error: UoftAPIError):
    """Translate upstream failures to 502 responses and timeouts to 504 responses."""
    status_code = 504 if isinstance(error, UoftAPITimeout) else 502
    return JSONResponse(status_code=status_code, content={"detail": str(error)})

async def get_db():
    """Yield a database session and close it when request processing finishes."""
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

db_dependency = Annotated[AsyncSession, Depends(get_db)]


async def get_course(course_code: CourseCode, db: db_dependency) -> Course:
    """Look up an uppercase course code; raise HTTP 404 if it is not stored."""
    course = await db.get(Course, course_code.upper())

    if course is None:
        raise HTTPException(status_code=404, detail= f"Course {course_code} not found.")

    return course


async def get_course_title(course_code: CourseCode) -> str:
    """Fetch the title and release the database connection before timetable I/O."""
    async with AsyncSessionLocal() as db:
        course = await get_course(course_code, db)
        if course.title is None:
            raise HTTPException(status_code=404, detail="Course not found.")
        return course.title


@app.get(
    "/{course_code}", summary="Get live details across F/S/Y offerings",
    response_model=list[CourseOfferingResponse],
    tags=["Courses"], responses=TIMETABLE_ERRORS,
    response_description="A list of available course offerings, each including its sections.",
)
async def get_all_data(course_code: CourseCode):
    """Fetch detailed course data directly from the U of T timetable API.

    Requires a stored course with a title. Queries F, S, and Y offerings within
    the academic periods configured in the upstream client. Missing offerings
    are skipped; returns an empty list if none are available. An upstream failure
    fails the request rather than returning a partial list.
    """
    title = await get_course_title(course_code)

    return await run_in_threadpool(get_all_sessions, course_code, title)


@app.get(
    "/basic-course-infos/{course_code}", summary="Get stored calendar information",
    response_model=CourseResponse,
    tags=["Courses"], responses=COURSE_ERRORS,
    response_description="The stored course record, with nullable calendar fields.",
)
async def basic_course_info(course_code: CourseCode, db: db_dependency):
    """Return the database record without calling the U of T timetable API.

    Includes the title, description, breadth, hours, requirement text, and
    extracted prerequisite/corequisite course lists. Null means no value is
    stored; it does not necessarily mean a requirement does not exist.
    """
    return await get_course(course_code, db)


@app.get(
    "/prerequisite-descriptions/{course_code}", summary="Get prerequisite text",
    response_model=RequirementTextResponse,
    tags=["Prerequisites"], responses=COURSE_ERRORS,
    response_description="Stored prerequisite text, or null when absent.",
)
async def prerequsites_descriptions(course_code: CourseCode, db: db_dependency):
    """Return prerequisite text from the database, preserving written requirements."""
    desc_course = await get_course(course_code, db)
    return desc_course.prerequisites


@app.get(
    "/prerequisite-codes/{course_code}", summary="List course codes mentioned in prerequisites",
    response_model=PrerequisiteCodesResponse,
    tags=["Prerequisites"], responses=COURSE_ERRORS,
    response_description="A list of extracted course codes, or null when no list is stored.",
)
async def prerequsites_codes_mentioned(course_code: CourseCode, db: db_dependency):
    """Return stored, unique course mentions with no guaranteed ordering.

    The list does not preserve AND/OR relationships, grade thresholds, or credit
    requirements. It must not be interpreted as requiring every listed course.
    Returns null when no prerequisite course list is stored.
    """
    prereq_course = await get_course(course_code, db)

    if prereq_course.prerequisite_course_list is not None:
        return prereq_course.prerequisite_course_list


@app.get(
    "/recommended/{course_code}", summary="Get recommended preparation",
    response_model=RequirementTextResponse,
    tags=["Courses"], responses=COURSE_ERRORS,
    response_description="Stored recommended preparation text, or null when absent.",
)
async def recommended(course_code: CourseCode, db: db_dependency):
    """Return the stored preparation recommendation, separate from prerequisites."""
    reccomended_course = await get_course(course_code, db)
    return reccomended_course.recommended


@app.get(
    "/exclusions/{course_code}", summary="Get exclusion text",
    response_model=RequirementTextResponse,
    tags=["Courses"], responses=COURSE_ERRORS,
    response_description="Stored exclusion text, or null when absent.",
)
async def exclusions(course_code: CourseCode, db: db_dependency):
    """Return exclusion text from the calendar record without parsing its logic."""
    exclusion_course = await get_course(course_code, db)
    return exclusion_course.exclusion


@app.get(
    "/postrequisites/{course_code}", summary="Find courses mentioning this prerequisite",
    response_model=PostrequisiteCodesResponse,
    tags=["Prerequisites"], responses=COURSE_ERRORS,
    response_description="Matching course codes; an empty list if none are stored.",
)
async def postrequisites(course_code: CourseCode, db: db_dependency):
    """Search stored prerequisite course lists for the requested course code.

    Returns mentions, not proof that the requested course is strictly required
    or sufficient for eligibility. Results have no guaranteed ordering and are
    limited to courses imported into this database. The requested course must
    itself be stored.
    """
    # For error checking
    course = await get_course(course_code, db)

    statement = select(Course.course_code).where(
        Course.prerequisite_course_list.contains([course_code])
    )

    result = await db.scalars(statement)
    course_codes = result.all()

    return course_codes


@app.get(
    "/sections/{course_code}/{session_code}", summary="List live timetable sections",
    response_model=list[SectionResponse],
    tags=["Timetable"], responses=TIMETABLE_ERRORS,
    response_description="All sections in the offering; may be an empty list.",
)
async def sections(course_code: CourseCode, session_code: SessionCode):
    """Fetch all section types, including meetings, instructors, and enrolment.

    session_code selects F (fall), S (winter), or Y (full academic year), not an
    academic-period identifier. Data is fetched live from the configured periods.
    An existing offering with no sections returns []; a missing offering is 404.
    """
    title = await get_course_title(course_code)
    
    course_response = await run_in_threadpool(
        call_uoft_api, course_code, title, session_code
    )
    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    
    data = course_json(course_response)

    if data is None:
        raise HTTPException(status_code=404, detail="Course offering not found.")

    return data['sections']


@app.get(
    "/lectures/{course_code}/{session_code}", summary="List live lecture sections",
    response_model=list[SectionResponse],
    tags=["Timetable"], responses=TIMETABLE_ERRORS,
    response_description="Sections whose teach_method is LEC; may be an empty list.",
)
async def lectures(course_code: CourseCode, session_code: SessionCode):
    """Fetch an F/S/Y offering and return only lecture (LEC) sections.

    Returns [] if the offering exists but contains no lectures. Missing offerings
    return 404. Data comes directly from the configured U of T academic periods.
    """
    title = await get_course_title(course_code)

    course_response = await run_in_threadpool(
        call_uoft_api, course_code, title, session_code
    )
    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    data = course_json(course_response)
    if data is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    sections = data['sections']
    return [section for section in sections if section['teach_method'] == 'LEC']


@app.get(
    "/tutorials/{course_code}/{session_code}", summary="List live tutorial sections",
    response_model=list[SectionResponse],
    tags=["Timetable"], responses=TIMETABLE_ERRORS,
    response_description="Sections whose teach_method is TUT; may be an empty list.",
)
async def tutorials(course_code: CourseCode, session_code: SessionCode):
    """Fetch an F/S/Y offering and return only tutorial (TUT) sections.

    Returns [] if the offering exists but contains no tutorials. Missing offerings
    return 404. Data comes directly from the configured U of T academic periods.
    """
    title = await get_course_title(course_code)

    course_response = await run_in_threadpool(
        call_uoft_api, course_code, title, session_code
    )

    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    data = course_json(course_response)
    if data is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    sections = data['sections']
    return [section for section in sections if section['teach_method'] == 'TUT']


@app.get(
    "/enrollment-infos/{course_code}/{session_code}/{section_code}",
    summary="Get the current enrolment count for a section",
    response_model=EnrollmentCountResponse,
    tags=["Timetable"], responses=TIMETABLE_ERRORS,
    response_description="The section's current enrolment count as a JSON number.",
)
async def enrollment(course_code: CourseCode, session_code: SessionCode, section_code: SectionCode):
    """Return the upstream current enrolment count for a section such as LEC0101.

    session_code selects F/S/Y within the configured academic periods. This is
    the enrolled count, not remaining capacity or waitlist size. It reflects the
    upstream response at fetch time. A missing section returns 404.
    """
    title = await get_course_title(course_code)

    course_response = await run_in_threadpool(
        call_uoft_api, course_code, title, session_code
    )
    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")


    data = course_json(course_response)
    if data is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    res = [section["current_enrolment"] for section in data["sections"]  if section["name"] == section_code ]
    if not res:
        raise HTTPException(status_code=404, detail="Section not found.")
    return res[0]


if __name__ == '__main__':
    db = get_db()
