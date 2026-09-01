import requests
from bs4 import BeautifulSoup, Tag
import pprint


def parse_html_with_response(response: requests.Response):
    """
    Preconditions:
        response.status_code == 200
    """

    html_content = response.content
    soup = BeautifulSoup(html_content, 'html.parser')
    return parse_html(soup)


def parse_html_with_file(filename: str = 'uoft.html'):
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()
        soup = BeautifulSoup(html_content, 'html.parser')

    return parse_html(soup)


def find_field_content(page: Tag, class_field: str) -> Tag | None:
    span = page.find('span', class_=class_field)
    if span is not None:
        field_content = span.find('span', class_='field-content')
        if field_content is not None:
            return field_content

    return None


def find_field_content_body(page: Tag, class_field: str) -> Tag | None:
    span = page.find('div', class_=class_field)
    if span is not None:
        field_content = span.find('span', class_='field-content')
        if field_content is not None:
            return field_content

    return None
    

def parse_html(soup: BeautifulSoup):
    course_pages = soup.find_all('div', class_='no-break w3-row views-row')
    courses = {}
    for page in course_pages:
        title = page.h3.get_text(strip=True) if page.h3 is not None else ""
        course_code = title[:8]

        if not course_code:
            continue

        course_hours = find_field_content(page, 'views-field views-field-field-hours')
        course_hours = course_hours.get_text(" ", strip=True) if course_hours is not None else None
        
        description = find_field_content_body(page, 'views-field views-field-body')
        description = description.get_text(" ", strip=True) if description is not None else None

        prerequisites = find_field_content(page, 'views-field views-field-field-prerequisite')
        prerequisites = prerequisites.get_text(" ", strip=True) if prerequisites is not None else None
        
        exclusion = find_field_content(page, 'views-field views-field-field-exclusion')
        exclusion = exclusion.get_text(" ", strip=True) if exclusion is not None else None

        recommended = find_field_content(page, 'views-field views-field-field-recommended')
        recommended = recommended.get_text(" ", strip=True) if recommended is not None else None

        breadth = find_field_content(page, 'views-field views-field-field-breadth-requirements')
        breadth = breadth.get_text(" ", strip=True) if breadth is not None else None

        course_info = {
                "course code": course_code,
                "course hours": course_hours, 
                "description": description, 
                "prerequisites": prerequisites, 
                "exclusion": exclusion,
                "recommended": recommended, 
                "breadth": breadth
            }
        
        courses[course_code] = course_info

    return courses


def main():
    print("Running...")
    url = 'https://artsci.calendar.utoronto.ca/print/view/pdf/course_search/print_page/debug?page=0'

    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        courses = parse_html_with_response(response)
        pprint.pprint(courses)
        print(len(courses))
    else:
        print(response.status_code)


if __name__ == "__main__":
    main()
