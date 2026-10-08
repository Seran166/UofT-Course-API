import pytest
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from tests.support import models
from uoft_course_api import schemas

def test_valid_codes_normalize():
    for model, value, expected in [(schemas.CourseCode, 'csc108h1', 'CSC108H1'), (schemas.SessionCode, 's', 'S'), (schemas.SectionCode, 'lec0101', 'LEC0101')]:
        assert TypeAdapter(model).validate_python(value) == expected

def test_invalid_codes():
    for model, values in [(schemas.CourseCode, ['', 'XCSC108H1', 'CSC108H1X', 'CSC108Q1']), (schemas.SessionCode, ['20269', 'Z', '']), (schemas.SectionCode, ['LEC01', '0101', 'LEC01011'])]:
        for value in values:
            with pytest.raises(ValidationError):
                TypeAdapter(model).validate_python(value)

def test_primary_keys():
    assert list(models.Course.__table__.primary_key.columns.keys()) == ['course_code']

def test_postgres_schema_compiles():
    sql = str(CreateTable(models.Course.__table__).compile(dialect=postgresql.dialect()))
    assert 'TEXT[]' in sql
