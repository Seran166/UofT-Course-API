from typing import Any

import requests
from requests import Response
import json
import pprint
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
        course_info = course_data['cmCourseInfo']

        self.specific_id = course_data['id']
        self.name = course_data['name']
        self.section = course_data['sectionCode']
        self.code = course_data['code']

        self.title = course_info['title']
        if self.title != self.name:
            print(f'{self.title} vs {self.name}')

        self.description = course_info['description']
        self.prerequisites = course_info['prerequisitesText']
        self.corequisites = course_info['corequisitesText']
        self.exclusions = course_info['exclusionsText']
        self.recommended = course_info['recommendedPreparation']

        self.breadth_s = course_info['breadthRequirements']

        self.department = course_data['department']['name']
        self.department_code = course_data['department']['code']
        
        sections = course_data['sections']
        for lec_or_tut in sections:
            print(f'{lec_or_tut['type']}: {lec_or_tut['name']}')
            

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




