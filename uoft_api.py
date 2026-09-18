"""
These classes aren't needed, but help me organize the json responses given, will eventually transpose them back into a json response anyways
"""

from typing import Any, Optional

import requests
from requests import Response
import json
import pprint
import time
from dataclasses import dataclass


def course_json(course_response: Response) -> dict:
    course_data = dict(course_response.json())['payload']['pageableCourse']['courses'][0]
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


class Course:    
    """
    Preconditions:
     - self.specific_id.isalnum()
     - self.section == 'F' or self.section == 'S'
    """
    def __init__(self, course_response: Response) -> None:
        course_data = dict(course_response.json())['payload']['pageableCourse']['courses'][0]

        self.specific_id = course_data['id']
        self.name = course_data['name']
        self.code = course_data['code']
        self.section = course_data['sectionCode']


        course_info = course_data['cmCourseInfo']
        self.description = course_info['description']
        self.prerequisites = course_info['prerequisitesText']
        self.corequisites = course_info['corequisitesText']
        self.exclusions = course_info['exclusionsText']
        self.recommended = course_info['recommendedPreparation']

        self.title = course_info['title']
        if self.title != self.name:
            print(f'{self.title} vs {self.name}')

        # Note that this is a list of breadths
        self.breadth_s = course_info['breadthRequirements']

        self.department = course_data['department']['name']
        self.department_code = course_data['department']['code']
        self.max_credit = course_data['maxCredit']
        self.min_credit = course_data['minCredit']
        self.credit = self.max_credit
        
        sections_data = course_data['sections']
        self.sections: list[CourseSection] = [CourseSection(section) for section in sections_data]


def find_enrollment_controls(section_json: dict) -> list:
    """
    Function is a bit suspect, because the descriptions given aren't always descriptive. This is how it works in ttb
    """
    enrolment_controls: list[dict[str, Any]] = section_json['enrolmentControls']
    enrolment_control_descriptions = []
    for control in enrolment_controls:
        try:
            description = control['post']['name']
            if description != '*':
                enrolment_control_descriptions.append(f'All students in {description}')
        except KeyError:
            pass

    return enrolment_control_descriptions


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
            f'{instructor['firstName']} {instructor['lastName']}' for instructor in section_data["instructors"]
        ],

        'current_enrolment': section_data["currentEnrolment"],
        'max_enrolment': section_data["maxEnrolment"],
        'current_waitlist': section_data["currentWaitlist"],
        'delivery_modes': section_data["deliveryModes"],

        'is_cancelled': section_data["cancelInd"] == "Y",
        'is_tba': section_data["tbaInd"] == "Y",

        'enrolment_indicator': find_enrollment_controls(section_data) if section_data['enrolmentInd'] != '' else []
    }

class CourseSection():
    def __init__(self, section_data: dict) -> None:
        # What gets displayed on ttb is All students in section['post']['name']
        # If it's identical, then they make sure the only one enrolment indicator is shown

        self.name = section_data['name']
        self.type: str = section_data['type']
        self.teach_method = section_data['teachMethod']
        self.section_number = section_data['sectionNumber']

        self.meeting_times: list[TimeLocation] = [
            TimeLocation(meeting_json) for meeting_json in section_data.get("meetingTimes") or []]

        self.instructors = [
            f'{instructor['firstName']} {instructor['lastName']}' for instructor in section_data["instructors"]]

        self.current_enrolment: int = section_data["currentEnrolment"]
        self.max_enrolment: int = section_data["maxEnrolment"]
        self.current_waitlist: int = section_data["currentWaitlist"]
        self.delivery_modes: list[dict] = section_data["deliveryModes"] # len 1

        self.is_cancelled: bool = section_data["cancelInd"] == "Y"
        self.is_tba: bool = section_data["tbaInd"] == "Y"

        # if self.type[:3].upper() != self.teach_method:
        #     print('teach method error')
        #     raise RuntimeError

        # if self.teach_method + self.section_number != self.name:
        #     print('name error')
        #     raise RuntimeError

        self.enrolment_indicator = section_data['enrolmentInd']
        if self.enrolment_indicator != '':
            self.enrolment_control_descriptions = find_enrollment_controls(section_data)
        else:
            self.enrolment_control_descriptions = []


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

class TimeLocation:
    def __init__(self, meeting_json: dict):
        self.day: str = DAYS.get(meeting_json["start"]["day"], "Unknown")
        self.start_time: str = format_time(meeting_json["start"]["millisofday"])
        self.end_time: str = format_time(meeting_json["end"]["millisofday"])
        self.location_code: str = meeting_json["building"]["buildingCode"]
        self.session_code: str = meeting_json["sessionCode"]
        self.repetition: str = meeting_json["repetition"]


# data_raw = {
#     "courseCodeAndTitleProps": {
#         "courseCode":"AFR460H1",
#         "courseTitle":"Climate Change, Food Security, and Sustainability in Africa",
#         "courseSectionCode":"F",
#         "searchCourseDescription":False},
#     "departmentProps":[],
#     "campuses":[],
#     "sessions":["20269","20271","20269-20271"],
#     "requirementProps":[],
#     "instructor":"",
#     "courseLevels":[],
#     "deliveryModes":[],
#     "dayPreferences":[],
#     "timePreferences":[],
#     "divisions":["ARTSC"],
#     "creditWeights":[],
#     "availableSpace":False,
#     "waitListable":False,
#     "page":1,
#     "pageSize":20,
#     "direction":"asc"}

payload = {
    "courseCodeAndTitleProps": {
        "courseCode":"MAT257Y1",
        "courseTitle":"Analysis II",
        "courseSectionCode":"Y",
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
    "page":1,""
    "pageSize":20,"direction":"asc"}

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://ttb.utoronto.ca",
    "Referer": "https://ttb.utoronto.ca/"
}

# Note for future, take note of enrollment indicators, and that some tutorials are tied to some lecture times
url = "https://api.easi.utoronto.ca/ttb/getPageableCourses"

if __name__ == '__main__':
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    c = Course(response)
    pprint.pprint([vars(t) for s in c.sections for t in s.meeting_times if s.teach_method == "LEC"])

