# UofT Course API

A FastAPI application for University of Toronto St. George course information. It combines
stored calendar data with live timetable data from the U of T API. 

Get course descriptions, prerequisites, other courses that mention a course as a prerequisite, exclusions, sections, instructors,
meeting times, and enrolment counts.

## Setup

Requires Python 3.13+ and a PostgreSQL database. Run these commands from the
project root:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -e .
```

Create a `.env` file in the project root with your database connection:

```dotenv
DATABASE_URL=postgresql+psycopg://username:password@host:5432/database_name
```

## Import course data

Import the saved calendar HTML in `expected_responses/uoft.html` into your
database before requesting courses:

```bash
DATABASE_URL='postgresql://username:password@host:5432/database_name' \
    python -m uoft_course_api.init_database
```

If you want a more up to date file, run 
```bash
python -m uoft_course_api.scrape
```

The importer uses a regular `postgresql://` URL, while the API uses
`postgresql+psycopg://`. This command sets the URL for the importer only and
does not change `.env`. Use the same database and SSL settings for both.

## Run

```bash
python -m uvicorn uoft_course_api.api:app --app-dir src --reload
```

Open [the interactive API docs](http://127.0.0.1:8000/docs) to try the endpoints
and see their response fields.

## Examples

| Request | Returns |
| --- | --- |
| `/CSC108H1` | Live course details across available F/S/Y offerings |
| `/basic-course-infos/CSC108H1` | Stored calendar information |
| `/prerequisite-descriptions/CSC108H1` | Prerequisite text |
| `/prerequisite-codes/CSC108H1` | Course codes mentioned in prerequisites |
| `/postrequisites/CSC108H1` | Stored courses mentioning this prerequisite |
| `/sections/CSC108H1/F` | All sections for the offering |
| `/lectures/CSC108H1/F` | Lecture sections |
| `/tutorials/CSC108H1/F` | Tutorial sections |
| `/enrollment-infos/CSC108H1/F/LEC0101` | Current enrolment count |

F, S, and Y select fall, winter, and full-year offerings. The client currently
searches the 2026–2027 academic periods. Timetable data is fetched on each
request; calendar information comes from the database.

Extracted prerequisite codes are mentions only: they do not preserve AND/OR
relationships, required grades, or credit requirements.

## Tests

```bash
python -m pip install -r tests/requirements.txt
python -m pytest -c tests/pytest.ini
```

Tests use mocked database and HTTP calls. See [tests/README.md](tests/README.md)
for more details.

## License

[MIT](LICENSE). This project is unofficial and is not affiliated with the
University of Toronto.
