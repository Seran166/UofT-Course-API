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


url = "https://api.easi.utoronto.ca/ttb/getPageableCourses"
# @dataclass
class Course:
    c = 'a'
    
    """
    Preconditions:
     - self.specific_id.isalnum()
     - self.section == 'F' or self.section == 'S'
     - self.code
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
        
        sections = course_data['sections']
        for lec_or_tut in sections:
            print(f'{lec_or_tut['type']}: {lec_or_tut['name']}')
            

class CourseSection():
    def __init__(self, section_json: dict) -> None:
        # What gets displayed on ttb is All students in section['post']['name']
        # If it's identical, then they make sure the only one enrolment indicator is shown

        self.name = section_json['name']
        self.type: str = section_json['type']
        self.teach_method = section_json['teachMethod']
        self.section_number = section_json['sectionNumber']

        self.meeting_times: list[TimeLocation] = [
            TimeLocation(meeting_json) for meeting_json in section_json.get("meetingTimes") or []]

        self.instructors = [
            f'{instructor['firstName']} {instructor['lastName']}' for instructor in section_json["instructors"]]

        self.current_enrolment: int = section_json["currentEnrolment"]
        self.max_enrolment: int = section_json["maxEnrolment"]
        self.current_waitlist: int = section_json["currentWaitlist"]
        self.delivery_modes: list[dict] = section_json["deliveryModes"] # len 1

        self.is_cancelled: bool = section_json["cancelInd"] == "Y"
        self.is_tba: bool = section_json["tbaInd"] == "Y"

        if self.type[:3].upper() != self.teach_method:
            print('teach method error')
            raise RuntimeError

        if self.teach_method + self.section_number != self.name:
            print('name error')
            raise RuntimeError

        self.enrolment_indicator = section_json['enrolmentInd']
        if self.enrolment_indicator != '':
            self.enrolment_control_descriptions = self.find_enrollment_controls(section_json)
        else:
            self.enrolment_control_descriptions = []


    def find_enrollment_controls(self, section_json: dict) -> list:
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


class TimeLocation:
    DAYS = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
    } 

    def __init__(self, meeting_json: dict):
        self.day: str = self.DAYS.get(meeting_json["start"]["day"], "Unknown")
        self.start_time: str = self.format_time(meeting_json["start"]["millisofday"])
        self.end_time: str = self.format_time(meeting_json["end"]["millisofday"])
        self.location_code: str = meeting_json["building"]["buildingCode"]
        self.session_code: str = meeting_json["sessionCode"]
        self.repetition: str = meeting_json["repetition"]

    @staticmethod
    def format_time(milliseconds: int) -> str:
        total_minutes = milliseconds // 60_000
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"

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
        "courseCode":"CSC111H1",
        "courseTitle":"Foundations of Computer Science II",
        "courseSectionCode":"S",
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

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=30
)

c = Course(response)

vars(c)


