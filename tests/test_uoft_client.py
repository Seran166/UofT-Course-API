import pytest
from unittest.mock import Mock, patch
import requests
from tests.support import uoft_client as client, response, section, meeting, no_results_response

def test_format_time():
    for value, expected in [(0, '00:00'), (60000, '00:01'), (3599999, '00:59'), (86399999, '23:59')]:
        assert client.format_time(value) == expected

def test_meeting_conversion():
    assert client.time_location_json(meeting()) == {'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00', 'location_code': 'BA', 'session_code': '20269', 'repetition': 'WEEKLY'}

def test_weekdays_and_unknown():
    for day, name in [(1, 'Monday'), (2, 'Tuesday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (9, 'Unknown')]:
        data = meeting()
        data['start']['day'] = day
        assert client.time_location_json(data)['day'] == name

def test_enrollment_controls():
    data = {'enrolmentControls': [{}, {'post': {}}, {'post': {'name': '*'}}, {'post': {'name': ''}}, {'post': {'name': 'Arts'}}, {'post': {'name': 'Arts'}}]}
    assert client.find_enrollment_controls(data) == ['All students in Arts']

def test_section_conversion():
    result = client.course_section_json(section())
    assert result == {'name': 'LEC0101', 'type': 'Lecture', 'teach_method': 'LEC', 'section_number': '0101', 'meeting_times': [client.time_location_json(meeting())], 'instructors': ['Ada Lovelace'], 'current_enrolment': 20, 'max_enrolment': 30, 'current_waitlist': 2, 'delivery_modes': [{'session': '20269', 'mode': 'INPER'}], 'is_cancelled': False, 'is_tba': False, 'enrolment_indicator': []}

def test_optional_meetings_and_flags():
    for meetings in [None, []]:
        data = section()
        data.update(meetingTimes=meetings, cancelInd='Y', tbaInd='Y', enrolmentInd='R', enrolmentControls=[{'post': {'name': 'Arts'}}])
        result = client.course_section_json(data)
        assert result['meeting_times'] == []
        assert result['is_cancelled']
        assert result['is_tba']
        assert result['enrolment_indicator'] == ['All students in Arts']
    del data['meetingTimes']
    assert client.course_section_json(data)['meeting_times'] == []

def test_course_conversion():
    assert client.course_json(response()) == {'name': 'Programming', 'specific_id': 'test-id', 'section': 'F', 'code': 'CSC108H1', 'description': 'Learn programming', 'prerequisites': 'None', 'corequisites': None, 'exclusions': 'CSC120H1', 'recommended': None, 'breadth_s': ['The Physical and Mathematical Universes (5)'], 'department': 'Computer Science', 'department_code': 'CSC', 'credit': 0.5, 'sections': [client.course_section_json(section())]}

def test_request_payload_and_timeout():
    with patch.object(client.requests, 'post', return_value=response()) as post:
        result = client.call_uoft_api('CSC108H1', 'Programming', 'F')
    assert result is post.return_value
    assert post.call_args.args == ('https://api.easi.utoronto.ca/ttb/getPageableCourses',)
    assert post.call_args.kwargs['timeout'] == 30
    assert post.call_args.kwargs['json']['courseCodeAndTitleProps'] == {'courseCode': 'CSC108H1', 'courseTitle': 'Programming', 'courseSectionCode': 'F', 'searchCourseDescription': False}

def test_transport_error_propagates():
    with patch.object(client.requests, 'post', side_effect=requests.Timeout), pytest.raises(client.UoftAPITimeout):
        client.call_uoft_api('CSC108H1', 'Programming', 'F')

def test_sessions_skip_empty_offerings():
    empty = response()
    empty.json.return_value['payload']['pageableCourse']['courses'] = []
    with patch.object(client, 'call_uoft_api', side_effect=[response(), empty, response()]) as call:
        result = client.get_all_sessions('CSC108H1', 'Programming')
    assert len(result) == 2
    assert [c.args[2] for c in call.call_args_list] == ['F', 'S', 'Y']

def test_all_sessions_failed():
    with patch.object(client, 'call_uoft_api', return_value=Mock(status_code=503)), pytest.raises(client.UoftAPIError):
        client.get_all_sessions('CSC108H1', 'Programming')

def test_empty_successful_session_is_skipped():
    empty = response()
    empty.json.return_value['payload']['pageableCourse']['courses'] = []
    with patch.object(client, 'call_uoft_api', return_value=empty):
        assert client.get_all_sessions('CSC108H1', 'Programming') == []


def test_no_results_http_404_is_empty_offering():
    raw = no_results_response()
    with patch.object(client.requests, 'post', return_value=raw):
        assert client.course_json(client.call_uoft_api('CSC111H1', 'Foundations', 'F')) is None


@pytest.mark.parametrize('payload', [
    None, {}, {'payload': None, 'status': []},
    {'payload': None, 'status': [{'code': 9999}]},
    {'payload': None, 'status': [{'code': 4404}, {'code': 9999}]},
])
def test_unrecognized_404_still_raises(payload):
    raw = no_results_response()
    raw.json.return_value = payload
    with pytest.raises(client.UoftAPIError):
        client.course_json(raw)


def test_non_json_404_still_raises():
    raw = no_results_response()
    raw.json.side_effect = ValueError('Not JSON')
    with pytest.raises(client.UoftAPIError):
        client.course_json(raw)


@pytest.mark.parametrize('payload', [None, {}, {'payload': None}, {'payload': {'pageableCourse': {'courses': None}}}, {'payload': {'pageableCourse': {'courses': [{}]}}}])
def test_malformed_payload(payload):
    raw = response()
    raw.json.return_value = payload
    with pytest.raises(client.UoftAPIError, match='invalid course data'):
        client.course_json(raw)


@pytest.mark.parametrize('status', [301, 404, 429, 500])
def test_upstream_http_status(status):
    raw = response()
    raw.status_code = status
    with patch.object(client.requests, 'post', return_value=raw), pytest.raises(client.UoftAPIError):
        client.call_uoft_api('CSC108H1', 'Programming', 'F')


@pytest.mark.parametrize('field,value', [
    ('currentEnrolment', 'invalid'),
    ('maxEnrolment', -1),
    ('deliveryModes', ['In Person']),
])
def test_invalid_upstream_fields_become_client_errors(field, value):
    raw = response()
    raw.json.return_value['payload']['pageableCourse']['courses'][0]['sections'][0][field] = value
    with pytest.raises(client.UoftAPIError, match='invalid course data'):
        client.course_json(raw)
