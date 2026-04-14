from __future__ import annotations

import unittest

from harness.transcript import TranscriptStore


class TestTranscriptStore(unittest.TestCase):
    def test_append(self) -> None:
        ts = TranscriptStore()
        ts.append('hello')
        self.assertEqual(len(ts.entries), 1)
        self.assertFalse(ts.flushed)

    def test_compact(self) -> None:
        ts = TranscriptStore()
        for i in range(20):
            ts.append(f'entry {i}')
        ts.compact(keep_last=5)
        self.assertEqual(len(ts.entries), 5)
        self.assertEqual(ts.entries[0], 'entry 15')

    def test_compact_no_op_when_small(self) -> None:
        ts = TranscriptStore()
        ts.append('one')
        ts.compact(keep_last=10)
        self.assertEqual(len(ts.entries), 1)

    def test_replay(self) -> None:
        ts = TranscriptStore()
        ts.append('a')
        ts.append('b')
        result = ts.replay()
        self.assertEqual(result, ('a', 'b'))
        self.assertIsInstance(result, tuple)

    def test_flush(self) -> None:
        ts = TranscriptStore()
        ts.append('msg')
        ts.flush()
        self.assertTrue(ts.flushed)

    def test_append_resets_flushed(self) -> None:
        ts = TranscriptStore()
        ts.flush()
        self.assertTrue(ts.flushed)
        ts.append('new')
        self.assertFalse(ts.flushed)


if __name__ == '__main__':
    unittest.main()
