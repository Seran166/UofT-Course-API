"""Shared synthetic inputs and import setup; never load local credentials."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uoft_course_api import models, scrape, uoft_client, init_database

# Engine construction normally reads .env at import time. Intercept construction
# so importing the API cannot use a developer's database configuration.
with patch("dotenv.load_dotenv"), patch(
    "sqlalchemy.ext.asyncio.create_async_engine", return_value=MagicMock()
):
    from uoft_course_api import api


def meeting():
    return {
        "start": {"day": 1, "millisofday": 32400000},
        "end": {"millisofday": 36000000},
        "building": {"buildingCode": "BA"},
        "sessionCode": "20269", "repetition": "WEEKLY",
    }


def section():
    return {
        "name": "LEC0101", "type": "Lecture", "teachMethod": "LEC",
        "sectionNumber": "0101", "meetingTimes": [meeting()],
        "instructors": [{"firstName": "Ada", "lastName": "Lovelace"}],
        "currentEnrolment": 20, "maxEnrolment": 30, "currentWaitlist": 2,
        "deliveryModes": [{"session": "20269", "mode": "INPER"}], "cancelInd": "N", "tbaInd": "N",
        "enrolmentInd": "", "enrolmentControls": [],
    }


def response():
    result = MagicMock(status_code=200)
    result.json.return_value = {"payload": {"pageableCourse": {"courses": [{
        "name": "Programming", "id": "test-id", "sectionCode": "F",
        "code": "CSC108H1", "maxCredit": 0.5,
        "department": {"name": "Computer Science", "code": "CSC"},
        "cmCourseInfo": {
            "description": "Learn programming", "prerequisitesText": "None",
            "corequisitesText": None, "exclusionsText": "CSC120H1",
            "recommendedPreparation": None, "breadthRequirements": ["The Physical and Mathematical Universes (5)"],
        },
        "sections": [section()],
    }]}}}
    return result
