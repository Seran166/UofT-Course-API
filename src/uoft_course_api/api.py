from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg.rows import dict_row
from src.uoft_course_api.database import engine, AsyncSessionLocal
from typing import Annotated
from src.uoft_course_api.models import Course, CourseCode, SessionCode, SectionCode

import src.uoft_course_api.models as models
from src.uoft_course_api.uoft_api import get_all_sessions, call_uoft_api, course_json

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(
            models.Base.metadata.create_all
        )

    yield

    await engine.dispose()

app = FastAPI(lifespan=lifespan) 

async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

db_dependency = Annotated[AsyncSession, Depends(get_db)]


async def get_course(course_code: CourseCode, db: db_dependency) -> Course:
    course = await db.get(Course, course_code.upper())

    if course is  None:
        raise HTTPException(status_code=404, detail="Course not found.")

    return course

@app.get("/{course_code}")
async def get_all_data(course_code: CourseCode, db: db_dependency):
    course = await get_course(course_code, db)

    if course is None or course.title is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    return get_all_sessions(course_code, course.title)

@app.get("/basic-course-infos/{course_code}")
async def basic_course_info(course_code: CourseCode, db: db_dependency):
    return get_course(course_code, db)


@app.get("/prerequisite-descriptions/{course_code}")
async def prerequsites_descriptions(course_code: CourseCode, db: db_dependency):
    desc_course = await get_course(course_code, db)
    return desc_course.prerequisites


@app.get("/prerequisite-codes/{course_code}")
async def prerequsites_codes_mentioned(course_code: CourseCode, db: db_dependency):
    prereq_course = await get_course(course_code, db)
    return prereq_course.prerequisite_course_list


@app.get("/recommended/{course_code}")
async def recommended(course_code: CourseCode, db: db_dependency):
    reccomended_course = await get_course(course_code, db)
    return reccomended_course.recommended

@app.get("/exclusions/{course_code}")
async def exclusions(course_code: CourseCode, db: db_dependency):
    exclusion_course = await get_course(course_code, db)
    return exclusion_course.exclusion

@app.get("/postrequisites/{course_code}")
async def postrequisites(course_code: CourseCode, db: db_dependency):
    return {"message": "Hello World"}

@app.get("/sections/{course_code}/{session_code}")
async def sections(course_code: CourseCode, session_code: SessionCode, db: db_dependency):
    course = await get_course(course_code, db)

    if course is None or course.title is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    
    course_response = call_uoft_api(course_code, course.title, session_code)
    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    
    data = course_json(course_response)

    return data['sections']

@app.get("/lectures/{course_code}/{session_code}")
async def lectures(course_code: str, session_code: SessionCode, db: db_dependency):
    course = await get_course(course_code, db)

    if course is None or course.title is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    course_response = call_uoft_api(course_code, course.title, session_code)
    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    data = course_json(course_response)
    if data is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    sections = data['sections']
    return [section for section in sections if section['teach_method'] == 'LEC']


@app.get("/tutorials/{course_code}/{session_code}")
async def tutorials(course_code: str, session_code: SessionCode, db: db_dependency):
    course = await get_course(course_code, db)

    if course is None or course.title is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    course_response = call_uoft_api(course_code, course.title, session_code)

    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    data = course_json(course_response)
    if data is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    sections = data['sections']
    return [section for section in sections if section['teach_method'] == 'TUT']

@app.get("/enrollment-infos/{course_code}/{session_code}/{section_code}")
async def enrollment(course_code: CourseCode, session_code: SessionCode, section_code: SectionCode, db: db_dependency):
    course = await get_course(course_code, db)

    if course is None or course.title is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    course_response = call_uoft_api(course_code, course.title, session_code)
    if course_response is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    
    data = course_json(course_response)
    if data is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    res = [section["current_enrolment"] for section in data["sections"]  if section["name"] == section_code ]
    return res[0]

