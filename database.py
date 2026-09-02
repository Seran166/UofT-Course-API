"""Parse the saved U of T calendar HTML and import courses into PostgreSQL."""

from __future__ import annotations
import os
from dotenv import load_dotenv
from urllib.parse import parse_qs, unquote, urlsplit
import psycopg
from scrape import parse_html_with_file

DEFAULT_HTML_FILE = "expected_responses/uoft.html"

def database_url() -> str:
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE")
    return url


def connect_to_remote() -> psycopg.Connection:
    """Connect using DATABASE_URL, including URLs with an unescaped password."""
    url = database_url()

    try:
        return psycopg.connect(url)
    except psycopg.ProgrammingError as error:
        if "percent-encoded" not in str(error):
            raise

    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    return psycopg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.lstrip("/") or "postgres",
        user=unquote(parsed.username or "postgres"),
        password=unquote(parsed.password or ""),
        sslmode=query.get("sslmode", ["require"])[0],
    )

def connect_to_local() -> psycopg.Connection:
    conn = psycopg.connect('dbname=uoftcourses user=seran16')
    return conn

def create_courses_table(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                course_code TEXT PRIMARY KEY,
                title TEXT,
                breadth TEXT,
                course_hours TEXT,
                description TEXT,
                exclusion TEXT,
                prerequisites TEXT,
                recommended TEXT
            )
            """
        )


def insert_into_database(connection: psycopg.Connection, courses: dict[str, dict[str, str | None]]) -> None:
    rows = [
        (
            course["course code"],
            course["title"],
            course["breadth"],
            course["course hours"],
            course["description"],
            course["exclusion"],
            course["prerequisites"],
            course["recommended"],
        )
        for course in courses.values()
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO courses (
                course_code,
                title,
                breadth,
                course_hours,
                description,
                exclusion,
                prerequisites,
                recommended
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (course_code) DO UPDATE SET
                breadth = EXCLUDED.breadth,
                title = EXCLUDED.title,
                course_hours = EXCLUDED.course_hours,
                description = EXCLUDED.description,
                exclusion = EXCLUDED.exclusion,
                prerequisites = EXCLUDED.prerequisites,
                recommended = EXCLUDED.recommended
            """,
            rows
        )


def main():
    courses = parse_html_with_file()

    with connect_to_local() as connection:
        create_courses_table(connection)
        insert_into_database(connection, courses)

    print(f"Imported {len(courses)} courses into the courses table.")



if __name__ == "__main__":
    main()
