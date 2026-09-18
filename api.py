from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg.rows import dict_row
from database import engine, AsyncSessionLocal
from typing import Annotated
from models import Course, CourseCode

import models
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

@app.get("/{course_code}")
async def get_all_data(course_code: CourseCode):
    pass

@app.get("/basic-course-infos/{course_code}")
async def basic_course_info(course_code: CourseCode, db: db_dependency):
    course = await db.get(Course, course_code.upper())

    if course is  None:
        raise HTTPException(status_code=404, detail="Course not found.")

    return course


@app.get("/prerequisite-descriptions/{course_code}")
async def prerequsites_descriptions(course_code: str):
    return {"message": "Hello World"}

@app.get("/prerequisite-codes/{course_code}")
async def prerequsites_codes_mentioned(course_code: str):
    return {"message": "Hello World"}

@app.get("/recommended/{course_code}")
async def recommended(course_code: str):
    return {"message": "Hello World"}

@app.get("/exclusions/{course_code}")
async def exclusions(course_code: str):
    return {"message": "Hello World"}

@app.get("/postrequisites/{course_code}")
async def postrequisites(course_code: str):
    return {"message": "Hello World"}

@app.get("/sections/{course_code}")
async def sections():
    return {"message": "Hello World"}

@app.get("/lectures/{course_code}")
async def lectures(course_code: str):
    return {"message": "Hello World"}

@app.get("/tutorials/{course_code}")
async def tutorials(course_code: str):
    return {"message": "Hello World"}

@app.get("/enrollment-infos/{course_code}/{section_code}")
async def enrollment(course_code: str, section_code: str):
    return {"message": "Hello World"}
