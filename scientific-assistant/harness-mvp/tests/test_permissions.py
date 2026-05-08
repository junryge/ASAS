from __future__ import annotations

import unittest

from harness.permissions import ToolPermissionContext


class TestToolPermissionContext(unittest.TestCase):
    def test_empty_blocks_nothing(self) -> None:
        ctx = ToolPermissionContext()
        self.assertFalse(ctx.blocks('anything'))

    def test_deny_names_exact_match(self) -> None:
        ctx = ToolPermissionContext.from_iterables(deny_names=['BashTool'])
        self.assertTrue(ctx.blocks('BashTool'))
        self.assertTrue(ctx.blocks('bashtool'))
        self.assertFalse(ctx.blocks('EchoTool'))

    def test_deny_prefixes(self) -> None:
        ctx = ToolPermissionContext.from_iterables(deny_prefixes=['mcp_'])
        self.assertTrue(ctx.blocks('mcp_server'))
        self.assertTrue(ctx.blocks('MCP_Server'))
        self.assertFalse(ctx.blocks('echo'))

    def test_combined(self) -> None:
        ctx = ToolPermissionContext.from_iterables(
            deny_names=['danger'],
            deny_prefixes=['internal_'],
        )
        self.assertTrue(ctx.blocks('danger'))
        self.assertTrue(ctx.blocks('internal_tool'))
        self.assertFalse(ctx.blocks('safe'))

    def test_from_iterables_with_none(self) -> None:
        ctx = ToolPermissionContext.from_iterables()
        self.assertFalse(ctx.blocks('anything'))


if __name__ == '__main__':
    unittest.main()
