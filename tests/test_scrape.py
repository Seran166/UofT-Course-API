import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import requests
from tests.support import scrape
FIXTURE = Path(__file__).parent / 'fixtures' / 'calendar.html'

def test_parse_file_all_fields():
    courses = scrape.parse_html_with_file(str(FIXTURE))
    assert set(courses) == {'CSC108H1', 'MAT137Y1'}
    course = courses['CSC108H1']
    assert course['title'] == 'Programming'
    assert course['course code'] == 'CSC108H1'
    assert course['course hours'] == '24L/12T'
    assert course['description'] == 'Learn programming .'
    assert course['prerequisites'] == 'MAT135H1 / MAT136H1'
    assert set(course['prerequisite course list']) == {'MAT135H1', 'MAT136H1'}
    assert course['corequisite course list'] == ['MAT137Y1']
    assert course['corequisites'] == 'MAT137Y1'
    assert course['exclusion'] == 'CSC120H1'
    assert course['recommended'] == 'Some experience'
    assert course['breadth'] == '5'

def test_missing_optional_fields():
    course = scrape.parse_html_with_file(str(FIXTURE))['MAT137Y1']
    for key, value in course.items():
        if key not in {'course code', 'title'}:
            assert value is None, key

def test_response_and_file_agree():
    response = Mock(content=FIXTURE.read_bytes())
    assert scrape.parse_html_with_response(response) == scrape.parse_html_with_file(str(FIXTURE))

def test_empty_page():
    assert scrape.parse_html(BeautifulSoup('', 'html.parser')) == {}

def test_missing_file():
    with pytest.raises(FileNotFoundError):
        scrape.parse_html_with_file(str(FIXTURE.with_name('missing.html')))

def test_field_helpers_missing_wrapper_or_content():
    for html in ['', '<span class="target"></span><div class="target"></div>']:
        soup = BeautifulSoup(html, 'html.parser')
        assert scrape.find_field_content(soup, 'target') is None
        assert scrape.find_field_content_body(soup, 'target') is None

def test_description_without_paragraph():
    html = '<div class="no-break w3-row views-row"><h3>CSC108H1 - Test</h3><div class="views-field views-field-body"><div class="field-content">text</div></div></div>'
    assert scrape.parse_html(BeautifulSoup(html, 'html.parser'))['CSC108H1']['description'] is None

def test_extract_codes_case_duplicates_and_punctuation():
    result = scrape.extract_course_codes('(cin105y1), CIN105Y1 / MAT135H1; MGT100H5')
    assert result is not None
    assert set(result) == {'CIN105Y1', 'MAT135H1', 'MGT100H5'}
    assert len(result) == 3

def test_extract_no_matches():
    for text in ['', '10.0 credits', 'XCSC108H1', 'CSC108H9']:
        assert scrape.extract_course_codes(text) is None

def test_reject_code_embedded_in_longer_token():
    assert scrape.extract_course_codes('CSC108H1XYZ') is None

def test_main_downloads_html(tmp_path, monkeypatch, capsys):
    content = FIXTURE.read_bytes()
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / 'expected_responses' / 'uoft.html'
    destination.parent.mkdir()
    destination.write_bytes(b'old calendar')
    result = Mock(content=content)

    with patch.object(scrape.requests, 'get', return_value=result) as get:
        scrape.main()

    result.raise_for_status.assert_called_once_with()
    assert get.call_args.kwargs['timeout'] == 30
    assert destination.read_bytes() == content
    assert 'Saved calendar HTML' in capsys.readouterr().out


def test_main_http_failure_preserves_existing_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / 'expected_responses' / 'uoft.html'
    destination.parent.mkdir()
    destination.write_bytes(b'old calendar')
    result = Mock(content=b'error page')
    result.raise_for_status.side_effect = requests.HTTPError('503')

    with patch.object(scrape.requests, 'get', return_value=result), pytest.raises(requests.HTTPError):
        scrape.main()

    assert destination.read_bytes() == b'old calendar'
