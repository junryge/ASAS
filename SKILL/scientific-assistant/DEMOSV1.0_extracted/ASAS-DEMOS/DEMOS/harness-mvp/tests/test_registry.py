from __future__ import annotations

import unittest

from harness.models import Tool
from harness.permissions import ToolPermissionContext
from harness.registry import ToolRegistry, builtin_tools


class TestToolRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.echo = Tool('echo', 'Echo input', handler=lambda p: p)
        self.upper = Tool('upper', 'Uppercase', handler=lambda p: p.upper())

    def test_register_and_get(self) -> None:
        self.registry.register(self.echo)
        self.assertEqual(self.registry.get('echo'), self.echo)

    def test_case_insensitive_lookup(self) -> None:
        self.registry.register(self.echo)
        self.assertEqual(self.registry.get('ECHO'), self.echo)
        self.assertEqual(self.registry.get('Echo'), self.echo)

    def test_get_unknown_returns_none(self) -> None:
        self.assertIsNone(self.registry.get('nonexistent'))

    def test_unregister(self) -> None:
        self.registry.register(self.echo)
        self.assertTrue(self.registry.unregister('echo'))
        self.assertIsNone(self.registry.get('echo'))

    def test_unregister_unknown_returns_false(self) -> None:
        self.assertFalse(self.registry.unregister('ghost'))

    def test_list_all(self) -> None:
        self.registry.register(self.echo)
        self.registry.register(self.upper)
        self.assertEqual(len(self.registry.list_all()), 2)

    def test_find(self) -> None:
        self.registry.register(self.echo)
        self.registry.register(self.upper)
        results = self.registry.find('echo')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'echo')

    def test_find_by_description(self) -> None:
        self.registry.register(self.echo)
        self.registry.register(self.upper)
        results = self.registry.find('uppercase')
        self.assertEqual(len(results), 1)

    def test_filter_with_permissions(self) -> None:
        self.registry.register(self.echo)
        self.registry.register(self.upper)
        ctx = ToolPermissionContext.from_iterables(deny_names=['echo'])
        filtered = self.registry.filter(ctx)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, 'upper')

    def test_filter_without_permissions(self) -> None:
        self.registry.register(self.echo)
        self.assertEqual(len(self.registry.filter()), 1)

    def test_execute_success(self) -> None:
        self.registry.register(self.upper)
        result = self.registry.execute('upper', 'hello')
        self.assertTrue(result.handled)
        self.assertEqual(result.output, 'HELLO')

    def test_execute_unknown_tool(self) -> None:
        result = self.registry.execute('ghost', 'hello')
        self.assertFalse(result.handled)
        self.assertIn('Unknown tool', result.output)

    def test_execute_handler_error(self) -> None:
        bad = Tool('bad', 'Always fails', handler=lambda p: 1 / 0)
        self.registry.register(bad)
        result = self.registry.execute('bad', 'test')
        self.assertFalse(result.handled)
        self.assertIn('Error', result.output)

    def test_render_index(self) -> None:
        self.registry.register(self.echo)
        output = self.registry.render_index()
        self.assertIn('Tool entries: 1', output)
        self.assertIn('echo', output)

    def test_builtin_tools(self) -> None:
        tools = builtin_tools()
        self.assertGreaterEqual(len(tools), 5)
        names = [t.name for t in tools]
        self.assertIn('echo', names)
        self.assertIn('upper', names)
        self.assertIn('word-count', names)


if __name__ == '__main__':
    unittest.main()
