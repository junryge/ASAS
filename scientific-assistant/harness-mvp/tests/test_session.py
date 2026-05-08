from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.session import StoredSession, list_sessions, load_session, save_session


class TestSessionStore(unittest.TestCase):
    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            session = StoredSession(
                session_id='test123',
                messages=('hello', 'world'),
                input_tokens=10,
                output_tokens=20,
            )
            path = save_session(session, Path(tmpdir))
            self.assertTrue(path.exists())

            loaded = load_session('test123', Path(tmpdir))
            self.assertEqual(loaded.session_id, 'test123')
            self.assertEqual(loaded.messages, ('hello', 'world'))
            self.assertEqual(loaded.input_tokens, 10)
            self.assertEqual(loaded.output_tokens, 20)

    def test_list_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            save_session(StoredSession('aaa', ('m',), 1, 1), Path(tmpdir))
            save_session(StoredSession('bbb', ('m',), 1, 1), Path(tmpdir))
            sessions = list_sessions(Path(tmpdir))
            self.assertEqual(sessions, ['aaa', 'bbb'])

    def test_list_sessions_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions = list_sessions(Path(tmpdir))
            self.assertEqual(sessions, [])

    def test_list_sessions_nonexistent_dir(self) -> None:
        sessions = list_sessions(Path('/nonexistent/dir/for/test'))
        self.assertEqual(sessions, [])

    def test_load_nonexistent_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                load_session('nonexistent', Path(tmpdir))

    def test_frozen(self) -> None:
        session = StoredSession('id', (), 0, 0)
        with self.assertRaises(AttributeError):
            session.session_id = 'new'  # type: ignore[misc]


if __name__ == '__main__':
    unittest.main()
