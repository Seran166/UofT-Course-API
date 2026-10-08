import contextlib
import io
import runpy
import pytest
from unittest.mock import MagicMock, patch
import psycopg
from tests.support import init_database as db, scrape, api
from tests.test_scrape import FIXTURE

def test_engine_configuration_without_connection():
    with patch('dotenv.load_dotenv'), patch.dict('os.environ', {'DATABASE_URL': 'postgresql+psycopg://test:test@localhost/test'}), patch('sqlalchemy.ext.asyncio.create_async_engine') as create, patch('sqlalchemy.ext.asyncio.async_sessionmaker') as factory:
        runpy.run_path(str(FIXTURE.parents[2] / 'src/uoft_course_api/create_engine.py'))
    create.assert_called_once_with('postgresql+psycopg://test:test@localhost/test', pool_pre_ping=True)
    factory.assert_called_once_with(autoflush=False, autocommit=False, bind=create.return_value)

def test_database_url():
    with patch.object(db, 'load_dotenv'), patch.dict('os.environ', {'DATABASE_URL': 'postgresql://example/test'}):
        assert db.database_url() == 'postgresql://example/test'

def test_missing_url():
    with patch.object(db, 'load_dotenv'), patch.dict('os.environ', {}, clear=True), pytest.raises(RuntimeError):
        db.database_url()

def test_remote_connect():
    with patch.object(db, 'database_url', return_value='postgresql://example/test'), patch.object(db.psycopg, 'connect') as connect:
        assert db.connect_to_remote() is connect.return_value
        connect.assert_called_once_with('postgresql://example/test')

def test_remote_fallback_decodes_credentials():
    url = 'postgresql://test:p%25word@example:5444/courses?sslmode=verify-full'
    connection = MagicMock()
    with patch.object(db, 'database_url', return_value=url), patch.object(db.psycopg, 'connect', side_effect=[psycopg.ProgrammingError('percent-encoded'), connection]) as connect:
        assert db.connect_to_remote() is connection
    assert connect.call_args.kwargs == dict(host='example', port=5444, dbname='courses', user='test', password='p%word', sslmode='verify-full')

def test_remote_fallback_defaults():
    with patch.object(db, 'database_url', return_value='postgresql://example'), patch.object(db.psycopg, 'connect', side_effect=[psycopg.ProgrammingError('percent-encoded'), MagicMock()]) as connect:
        db.connect_to_remote()
    assert connect.call_args.kwargs == dict(host='example', port=5432, dbname='postgres', user='postgres', password='', sslmode='require')

def test_unrelated_connection_error_propagates():
    with patch.object(db, 'database_url', return_value='postgresql://example/test'), patch.object(db.psycopg, 'connect', side_effect=psycopg.ProgrammingError('other')) as connect, pytest.raises(psycopg.ProgrammingError):
        db.connect_to_remote()
    connect.assert_called_once()

def test_local_connect():
    with patch.object(db.psycopg, 'connect') as connect:
        assert db.connect_to_local() is connect.return_value
    connect.assert_called_once()

def test_create_table():
    connection = MagicMock()
    db.create_courses_table(connection)
    sql = connection.cursor.return_value.__enter__.return_value.execute.call_args.args[0]
    assert 'CREATE TABLE IF NOT EXISTS courses' in sql
    assert 'course_code TEXT PRIMARY KEY' in sql

def test_insert_parsed_courses():
    connection = MagicMock()
    courses = scrape.parse_html_with_file(str(FIXTURE))
    db.insert_into_database(connection, courses)
    sql, rows = connection.cursor.return_value.__enter__.return_value.executemany.call_args.args
    assert 'ON CONFLICT (course_code) DO UPDATE' in sql
    assert sql.count('%s') == 11
    assert len(rows) == 2
    assert rows[0][:5] == ('CSC108H1', 'Programming', '5', '24L/12T', 'Learn programming .')
    assert set(rows[0][9]) == {'MAT135H1', 'MAT136H1'}
    assert rows[1][2:] == (None,) * 9

def test_empty_import():
    connection = MagicMock()
    db.insert_into_database(connection, {})
    assert connection.cursor.return_value.__enter__.return_value.executemany.call_args.args[1] == []

def test_main_import_workflow():
    with patch.object(db, 'parse_html_with_file', return_value={'test': {}}), patch.object(db, 'connect_to_remote') as connect, patch.object(db, 'create_courses_table') as create, patch.object(db, 'insert_into_database') as insert, contextlib.redirect_stdout(io.StringIO()) as output:
        db.main()
    connection = connect.return_value.__enter__.return_value
    create.assert_called_once_with(connection)
    insert.assert_called_once_with(connection, {'test': {}})
    assert 'Imported 1 courses' in output.getvalue()
