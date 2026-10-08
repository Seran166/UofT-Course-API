"""
These classes aren't needed, but help me organize the json responses given, will eventually transpose them back into a json response anyways
"""

from typing import Any, Optional

import requests
from requests import Response
import pprint
from dataclasses import dataclass
from pydantic import ValidationError
from uoft_course_api.schemas import CourseCode, CourseOfferingResponse


class UoftAPIError(Exception):
    """An upstream failure, distinct from a course with no matching offering."""


class UoftAPITimeout(UoftAPIError):
    """The upstream request timed out."""


def is_no_results(data: object) -> bool:
    """Recognize an empty offering without ignoring malformed or mixed errors."""
    if not isinstance(data, dict):
        return False

    if data.get("payload") is not None:
        return False

    statuses = data.get("status")
    if not isinstance(statuses, list) or not statuses:
        return False

    for status in statuses:
        if not isinstance(status, dict):
            return False
        if status.get("code") != 4404:
            return False

    return True


def validate_response(response: Response) -> None:
    if response.status_code == 404:
        try:
            data = response.json()
        except ValueError:
            data = None
        if is_no_results(data):
            return
    if not 200 <= response.status_code < 300:
        raise UoftAPIError("U of T API returned an unsuccessful response.")


def course_json(course_response: Response) -> dict | None:
    validate_response(course_response)
    if course_response.status_code == 404:
        return None
    try:
        courses = course_response.json()['payload']['pageableCourse']['courses']
        if not isinstance(courses, list):
            raise TypeError("courses must be a list")
        if not courses:
            return None
        converted = _course_json(courses[0])
        return CourseOfferingResponse.model_validate(converted).model_dump()
    except (ValidationError, ValueError, KeyError, TypeError, IndexError) as error:
        raise UoftAPIError("U of T API returned invalid course data.") from error


def _course_json(course_data: dict) -> dict:
    course_info = course_data['cmCourseInfo']

    return {
        'name': course_data['name'],
        'specific_id': course_data['id'],
        'section': course_data['sectionCode'],
        'code': course_data['code'],

        'description': course_info['description'],
        'prerequisites': course_info['prerequisitesText'],
        'corequisites': course_info['corequisitesText'],
        'exclusions': course_info['exclusionsText'],
        'recommended': course_info['recommendedPreparation'],

        'breadth_s': course_info['breadthRequirements'],

        'department': course_data['department']['name'],
        'department_code': course_data['department']['code'],
        'credit': course_data['maxCredit'],
        
        'sections': [course_section_json(section) for section in course_data['sections']]
    }

def find_enrollment_controls(section_json: dict) -> list:
    """
    Function is a bit suspect, because the descriptions given aren't always descriptive. This is how it works in ttb
    """
    enrolment_controls: list[dict[str, Any]] = section_json['enrolmentControls']
    enrolment_control_descriptions = []
    for control in enrolment_controls:
        try:
            description = control['post']['name']
            if description != '*' and description != '':
                enrolment_control_descriptions.append(f'All students in {description}')
        except KeyError:
            pass

    return list(set(enrolment_control_descriptions))


def course_section_json(section_data):
    return {
        'name': section_data['name'],
        'type': section_data['type'],
        'teach_method': section_data['teachMethod'],
        'section_number': section_data['sectionNumber'],

        'meeting_times': [
            time_location_json(meeting_json) for meeting_json in section_data.get("meetingTimes") or [] 
        ],

        'instructors': [
            f'{instructor["firstName"]} {instructor["lastName"]}' for instructor in section_data["instructors"]
        ],

        'current_enrolment': section_data["currentEnrolment"],
        'max_enrolment': section_data["maxEnrolment"],
        'current_waitlist': section_data["currentWaitlist"],
        'delivery_modes': section_data["deliveryModes"],

        'is_cancelled': section_data["cancelInd"] == "Y",
        'is_tba': section_data["tbaInd"] == "Y",

        'enrolment_indicator': find_enrollment_controls(section_data) if section_data['enrolmentInd'] != '' else []
    }

DAYS = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
} 

def format_time(milliseconds: int) -> str:
    total_minutes = milliseconds // 60_000
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"

def time_location_json (meeting_json: dict):
    return {
        'day' : DAYS.get(meeting_json["start"]["day"], "Unknown"),
        'start_time': format_time(meeting_json["start"]["millisofday"]),
        'end_time': format_time(meeting_json["end"]["millisofday"]),
        'location_code': meeting_json["building"]["buildingCode"],
        'session_code': meeting_json["sessionCode"],
        'repetition': meeting_json["repetition"]
    }


def call_uoft_api(course_code: CourseCode, course_title: str, section_code: str) -> Response:
    payload = {
        "courseCodeAndTitleProps": {
            "courseCode": f'{course_code}',
            "courseTitle":f'{course_title}',
            "courseSectionCode": f'{section_code}',
            "searchCourseDescription": False},
        "departmentProps":[],
        "campuses":[],
        "sessions":["20269","20271","20269-20271"],
        "requirementProps": [],
        "instructor": "",
        "courseLevels":[],
        "deliveryModes":[],
        "dayPreferences":[],
        "timePreferences":[],
        "divisions":["ARTSC"],
        "creditWeights":[],
        "availableSpace":False,
        "waitListable":False,
        "page":1,
        "pageSize":20,
        "direction":"asc"}

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://ttb.utoronto.ca",
        "Referer": "https://ttb.utoronto.ca/"
    }

    url = "https://api.easi.utoronto.ca/ttb/getPageableCourses"

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
    except requests.Timeout as error:
        raise UoftAPITimeout("U of T API request timed out.") from error
    except requests.RequestException as error:
        raise UoftAPIError("Could not reach the U of T API.") from error

    validate_response(response)
    return response

def get_all_sessions(course_code: CourseCode, course_title: str) -> list[dict]:
    sessions = []
    for c in ['F', 'S', 'Y']:
        response = call_uoft_api(course_code, course_title, c)
        course = course_json(response)
        if course is not None:
            sessions.append(course)

    return sessions

if __name__ == '__main__':
    sessions = get_all_sessions('PHL100Y1', 'Ancient Wisdom, Modern Insights: A Historical Introduction to Philosophy')
    pprint.pprint(sessions)
