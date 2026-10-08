"""Response contracts, serialization, and generated API documentation."""
import json
from pathlib import Path

import pytest
from fastapi.exceptions import ResponseValidationError
from pydantic import TypeAdapter, ValidationError
from requests import Response

from tests.support import api, response, uoft_client
from uoft_course_api import schemas


def test_course_response_from_database_attributes(course):
    result = schemas.CourseResponse.model_validate(course).model_dump()
    assert result['course_code'] == 'CSC108H1'
    assert result['title'] == 'Programming'
    assert result['description'] is None
    assert result['corequisite_course_list'] is None
    assert '_sa_instance_state' not in result


def test_nested_offering_round_trip():
    payload = uoft_client.course_json(response())
    parsed = schemas.CourseOfferingResponse.model_validate(payload)
    assert parsed.model_dump() == payload
    assert parsed.sections[0].meeting_times[0].start_time == '09:00'
    assert parsed.sections[0].delivery_modes[0].mode == 'INPER'


def test_saved_upstream_response_validates():
    path = Path(__file__).resolve().parents[1] / 'expected_responses/expected_response.json'
    raw = Response()
    raw.status_code = 200
    raw._content = path.read_bytes()
    payload = uoft_client.course_json(raw)
    assert schemas.CourseOfferingResponse.model_validate(payload).model_dump() == payload


def test_preserve_extra_delivery_metadata():
    payload = {'session': '20269', 'mode': 'INPER', 'label': 'In Person'}
    assert schemas.DeliveryModeResponse.model_validate(payload).model_dump() == payload


@pytest.mark.parametrize('field,value', [('current_enrolment', -1), ('instructors', 'Ada'), ('meeting_times', [{}]), ('delivery_modes', ['In Person'])])
def test_reject_invalid_section_shape(field, value):
    res = uoft_client.course_json(response())
    assert res is not None
    payload = res['sections'][0]
    payload[field] = value
    with pytest.raises(ValidationError):
        schemas.SectionResponse.model_validate(payload)


@pytest.mark.parametrize('schema,value', [
    (schemas.RequirementTextResponse, None),
    (schemas.RequirementTextResponse, 'MAT135H1 or equivalent'),
    (schemas.PrerequisiteCodesResponse, None),
    (schemas.PrerequisiteCodesResponse, []),
    (schemas.PrerequisiteCodesResponse, ['MAT135H1']),
    (schemas.PostrequisiteCodesResponse, []),
    (schemas.EnrollmentCountResponse, 0),
])
def test_scalar_and_list_shapes_preserved(schema, value):
    adapter = TypeAdapter(schema)
    assert json.loads(adapter.dump_json(adapter.validate_python(value))) == value


@pytest.mark.asyncio
async def test_basic_course_serializes_orm_record(http, course):
    result = await http.get('/basic-course-infos/CSC108H1')
    assert result.status_code == 200
    assert result.json() == schemas.CourseResponse.model_validate(course).model_dump()


@pytest.mark.asyncio
async def test_response_validation_rejects_incomplete_offering(http, monkeypatch):
    monkeypatch.setattr(api, 'get_all_sessions', lambda *_: [{'section': 'F'}])
    with pytest.raises(ResponseValidationError):
        await http.get('/CSC108H1')


@pytest.mark.asyncio
async def test_empty_offerings_list_stays_empty(http, monkeypatch):
    monkeypatch.setattr(api, 'get_all_sessions', lambda *_: [])
    result = await http.get('/CSC108H1')
    assert result.status_code == 200
    assert result.json() == []


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['prerequisite-descriptions', 'recommended', 'exclusions'])
async def test_null_text_response(http, course, path):
    course.prerequisites = course.recommended = course.exclusion = None
    result = await http.get(f'/{path}/CSC108H1')
    assert result.status_code == 200
    assert result.json() is None


def test_openapi_documents_every_response():
    document = api.app.openapi()
    for path in document['paths'].values():
        operation = path['get']
        assert operation['responses']['200']['content']['application/json']['schema']
        assert operation['responses']['404']['content']['application/json']['schema']['$ref'].endswith('/ErrorResponse')
        # Input-validation errors retain FastAPI's separate error contract.
        assert operation['responses']['422']['content']['application/json']['schema']['$ref'].endswith('/HTTPValidationError')
    components = document['components']['schemas']
    for name in ['CourseResponse', 'CourseOfferingResponse', 'SectionResponse', 'MeetingTimeResponse', 'DeliveryModeResponse', 'ErrorResponse']:
        assert name in components
    assert components['CourseOfferingResponse']['properties']['sections']['items']['$ref'].endswith('/SectionResponse')
    for code in ['502', '504']:
        assert document['paths']['/{course_code}']['get']['responses'][code]['content']['application/json']['schema']['$ref'].endswith('/ErrorResponse')
