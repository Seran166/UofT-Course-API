import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi import HTTPException
from tests.support import api, models, response, no_results_response
from tests.support import uoft_client

@pytest.mark.asyncio
async def test_get_course_normalizes_case(course, db):
    assert await api.get_course('csc108h1', db) is course
    db.get.assert_awaited_once_with(models.Course, 'CSC108H1')

@pytest.mark.asyncio
async def test_unknown_course(db, http):
    db.get.return_value = None
    result = await http.get('/prerequisite-descriptions/CSC108H1')
    assert result.status_code == 404

@pytest.mark.asyncio
async def test_metadata_routes(http):
    for path, expected in [('prerequisite-descriptions', 'MAT135H1'), ('prerequisite-codes', ['MAT135H1']), ('recommended', 'Practice'), ('exclusions', 'CSC120H1')]:
        result = await http.get(f'/{path}/CSC108H1')
        assert result.status_code == 200
        assert result.json() == expected

@pytest.mark.asyncio
async def test_null_prerequisites(course, http):
    course.prerequisite_course_list = None
    result = await http.get('/prerequisite-codes/CSC108H1')
    assert result.json() is None

@pytest.mark.asyncio
async def test_all_data_route(http):
    expected = [uoft_client.course_json(response())]
    with patch.object(api, 'get_all_sessions', return_value=expected) as fetch:
        result = await http.get('/CSC108H1')
    assert result.json() == expected
    fetch.assert_called_once_with('CSC108H1', 'Programming')

@pytest.mark.asyncio
async def test_section_routes(http):
    for path, expected_count in [('sections', 1), ('lectures', 1), ('tutorials', 0)]:
        result = await http.get(f'/{path}/CSC108H1/F')
        assert result.status_code == 200
        assert len(result.json()) == expected_count
    result = await http.get('/enrollment-infos/CSC108H1/F/LEC0101')
    assert result.json() == 20

@pytest.mark.asyncio
async def test_tutorial_filter(http, upstream):
    raw = upstream.return_value.json.return_value['payload']['pageableCourse']['courses'][0]
    tutorial = dict(raw['sections'][0], name='TUT0101', teachMethod='TUT')
    raw['sections'].append(tutorial)
    result = await http.get('/tutorials/CSC108H1/F')
    assert [s['name'] for s in result.json()] == ['TUT0101']

@pytest.mark.asyncio
async def test_invalid_parameters(http, upstream, db):
    for path in ['/BAD', '/sections/CSC108H1/Z', '/enrollment-infos/CSC108H1/F/BAD']:
        assert (await http.get(path)).status_code == 422
    upstream.assert_not_called()
    db.get.assert_not_awaited()

@pytest.mark.asyncio
async def test_missing_title(course, http, upstream, db):
    course.title = None
    for path in ['/CSC108H1', '/sections/CSC108H1/F', '/lectures/CSC108H1/F', '/tutorials/CSC108H1/F', '/enrollment-infos/CSC108H1/F/LEC0101']:
        assert (await http.get(path)).status_code == 404
    upstream.assert_not_called()
    assert db.close.await_count == 5


@pytest.mark.asyncio
@pytest.mark.parametrize('path', [
    '/CSC108H1', '/sections/CSC108H1/F', '/lectures/CSC108H1/F',
    '/tutorials/CSC108H1/F', '/enrollment-infos/CSC108H1/F/LEC0101',
])
async def test_missing_timetable_course_closes_session(http, db, upstream, path):
    db.get.return_value = None
    with patch.object(api, 'get_all_sessions') as fetch_all:
        result = await http.get(path)
    assert result.status_code == 404
    db.close.assert_awaited_once()
    upstream.assert_not_called()
    fetch_all.assert_not_called()


@pytest.mark.asyncio
async def test_title_lookup_failure_closes_session(http, db, upstream):
    db.get.side_effect = RuntimeError('Database lookup failed')
    with pytest.raises(RuntimeError, match='Database lookup failed'):
        await http.get('/sections/CSC108H1/F')
    db.close.assert_awaited_once()
    upstream.assert_not_called()

@pytest.mark.asyncio
async def test_missing_upstream_response(http, upstream):
    upstream.return_value = None
    for path in ['sections', 'lectures', 'tutorials', 'enrollment-infos']:
        suffix = '/LEC0101' if path == 'enrollment-infos' else ''
        assert (await http.get(f'/{path}/CSC108H1/F{suffix}')).status_code == 404

@pytest.mark.asyncio
async def test_db_dependency_closes_on_success_and_error(db):
    for fail in [False, True]:
        with patch.object(api, 'AsyncSessionLocal', return_value=db):
            dependency = api.get_db()
            assert await anext(dependency) is db
            if fail:
                with pytest.raises(ValueError):
                    await dependency.athrow(ValueError('test'))
            else:
                await dependency.aclose()
    assert db.close.await_count == 2

@pytest.mark.asyncio
async def test_lifespan_creates_tables_and_disposes():
    engine = MagicMock()
    connection = engine.begin.return_value.__aenter__.return_value
    connection.run_sync = AsyncMock()
    engine.dispose = AsyncMock()
    with patch.object(api, 'engine', engine):
        async with api.lifespan(api.app):
            connection.run_sync.assert_awaited_once_with(models.Base.metadata.create_all)
            engine.dispose.assert_not_awaited()
    engine.dispose.assert_awaited_once()

@pytest.mark.asyncio
async def test_basic_course_returns_resolved_course(course, db):
    result = await api.basic_course_info('CSC108H1', db)
    if inspect.iscoroutine(result):
        result.close()
    assert result is course

@pytest.mark.asyncio
async def test_postrequisites_validates_course(db):
    db.get.return_value = None
    db.scalars.return_value.all.return_value = []
    with pytest.raises(HTTPException):
        await api.postrequisites('CSC108H1', db)

@pytest.mark.asyncio
async def test_postrequisites_query(db):
    db.scalars.return_value.all.return_value = ['CSC148H1']
    assert await api.postrequisites('CSC108H1', db) == ['CSC148H1']
    statement = db.scalars.call_args.args[0]
    assert ['CSC108H1'] in statement.compile().params.values()

@pytest.mark.asyncio
async def test_unknown_section_returns_404(http):
    result = await http.get('/enrollment-infos/CSC108H1/F/LEC9999')
    assert result.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize('path', [
    '/sections/CSC108H1/F', '/lectures/CSC108H1/F',
    '/tutorials/CSC108H1/F', '/enrollment-infos/CSC108H1/F/LEC0101',
])
async def test_empty_offering_returns_404(http, upstream, path):
    upstream.return_value.json.return_value['payload']['pageableCourse']['courses'] = []
    assert (await http.get(path)).status_code == 404


@pytest.mark.asyncio
async def test_all_data_skips_upstream_no_results_404(http):
    winter = response()
    winter.json.return_value['payload']['pageableCourse']['courses'][0]['sectionCode'] = 'S'
    with patch.object(uoft_client.requests, 'post', side_effect=[
        no_results_response(), winter, no_results_response(),
    ]) as post:
        result = await http.get('/csc108h1')
    assert result.status_code == 200
    assert [offering['section'] for offering in result.json()] == ['S']
    assert [call.kwargs['json']['courseCodeAndTitleProps']['courseSectionCode']
            for call in post.call_args_list] == ['F', 'S', 'Y']


@pytest.mark.asyncio
@pytest.mark.parametrize('path', [
    '/sections/CSC108H1/F', '/lectures/CSC108H1/F',
    '/tutorials/CSC108H1/F', '/enrollment-infos/CSC108H1/F/LEC0101',
])
async def test_upstream_no_results_404_returns_not_found(http, monkeypatch, path):
    monkeypatch.setattr(api, 'call_uoft_api', uoft_client.call_uoft_api)
    with patch.object(uoft_client.requests, 'post', return_value=no_results_response()):
        result = await http.get(path)
    assert result.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize('path', [
    '/CSC108H1', '/sections/CSC108H1/F', '/lectures/CSC108H1/F',
    '/tutorials/CSC108H1/F', '/enrollment-infos/CSC108H1/F/LEC0101',
])
@pytest.mark.parametrize('failure,status', [('timeout', 504), ('connection', 502), ('http', 502), ('json', 502), ('invalid_field', 502)])
async def test_upstream_failure_status(http, upstream, monkeypatch, path, failure, status):
    import requests
    from tests.support import uoft_client

    # Exercise the real client and conversion through each HTTP route.
    monkeypatch.setattr(api, 'call_uoft_api', uoft_client.call_uoft_api)
    result = response()
    if failure == 'http':
        result.status_code = 503
    elif failure == 'json':
        result.json.side_effect = ValueError('private upstream payload')
    elif failure == 'invalid_field':
        result.json.return_value['payload']['pageableCourse']['courses'][0]['sections'][0]['currentEnrolment'] = 'invalid'
    error = {'timeout': requests.Timeout('private URL'), 'connection': requests.ConnectionError('private URL')}.get(failure)
    with patch.object(uoft_client.requests, 'post', return_value=result, side_effect=error):
        answer = await http.get(path)
    assert answer.status_code == status
    assert 'private' not in answer.text


@pytest.mark.asyncio
@pytest.mark.parametrize('path', [
    '/CSC108H1', '/sections/CSC108H1/F', '/lectures/CSC108H1/F',
    '/tutorials/CSC108H1/F', '/enrollment-infos/CSC108H1/F/LEC0101',
])
async def test_upstream_http_runs_off_event_loop_after_session_closes(http, monkeypatch, db, path):
    import threading

    event_loop_thread = threading.get_ident()
    request_threads = []

    def post(*args, **kwargs):
        db.close.assert_awaited_once()
        request_threads.append(threading.get_ident())
        return response()

    monkeypatch.setattr(api, 'call_uoft_api', uoft_client.call_uoft_api)
    with patch.object(uoft_client.requests, 'post', side_effect=post):
        result = await http.get(path)

    assert result.status_code == 200
    assert request_threads
    assert all(thread != event_loop_thread for thread in request_threads)
