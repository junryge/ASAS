from __future__ import annotations

import argparse

from .context import render_context, scan_workspace
from .engine import EngineConfig, HarnessEngine
from .models import Tool, default_tasks
from .permissions import ToolPermissionContext
from .registry import ToolRegistry, builtin_tools
from .router import ToolRouter
from .session import list_sessions, load_session


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in builtin_tools():
        registry.register(tool)
    return registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Harness MVP - Tool execution harness')
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('list', help='List all registered tools')
    subparsers.add_parser('tasks', help='List default tasks')
    subparsers.add_parser('context', help='Show workspace context')

    find_parser = subparsers.add_parser('find', help='Search tools by query')
    find_parser.add_argument('query')
    find_parser.add_argument('--limit', type=int, default=20)

    route_parser = subparsers.add_parser('route', help='Route a prompt to matching tools')
    route_parser.add_argument('prompt')
    route_parser.add_argument('--limit', type=int, default=5)

    run_parser = subparsers.add_parser('run', help='Execute a prompt through the turn loop')
    run_parser.add_argument('prompt')
    run_parser.add_argument('--max-turns', type=int, default=3)
    run_parser.add_argument('--structured-output', action='store_true')
    run_parser.add_argument('--deny-tool', action='append', default=[])
    run_parser.add_argument('--deny-prefix', action='append', default=[])

    exec_parser = subparsers.add_parser('exec-tool', help='Execute a single tool by name')
    exec_parser.add_argument('name')
    exec_parser.add_argument('payload')

    subparsers.add_parser('session-list', help='List persisted sessions')

    load_parser = subparsers.add_parser('session-load', help='Load a persisted session')
    load_parser.add_argument('session_id')

    subparsers.add_parser('summary', help='Render a full session report')

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = _build_registry()

    if args.command == 'list':
        print(registry.render_index())
        return 0

    if args.command == 'tasks':
        for task in default_tasks():
            print(f'- [{task.id}] {task.description}')
        return 0

    if args.command == 'context':
        print(render_context(scan_workspace()))
        return 0

    if args.command == 'find':
        print(registry.render_index(limit=args.limit, query=args.query))
        return 0

    if args.command == 'route':
        router = ToolRouter(registry)
        matches = router.route(args.prompt, limit=args.limit)
        if not matches:
            print('No tool matches found.')
            return 0
        for match in matches:
            print(f'{match.name}\t{match.score}\t{match.description}')
        return 0

    if args.command == 'run':
        permission_ctx = None
        if args.deny_tool or args.deny_prefix:
            permission_ctx = ToolPermissionContext.from_iterables(args.deny_tool, args.deny_prefix)
        config = EngineConfig(
            max_turns=args.max_turns,
            structured_output=args.structured_output,
        )
        engine = HarnessEngine.create(registry, config)
        results = engine.run_loop(args.prompt, permission_ctx=permission_ctx)
        for idx, result in enumerate(results, start=1):
            print(f'## Turn {idx}')
            print(result.output)
            print(f'stop_reason={result.stop_reason}')
        path = engine.persist()
        print(f'\nSession persisted: {path}')
        return 0

    if args.command == 'exec-tool':
        result = registry.execute(args.name, args.payload)
        print(result.output)
        return 0 if result.handled else 1

    if args.command == 'session-list':
        sessions = list_sessions()
        if not sessions:
            print('No persisted sessions.')
        else:
            for sid in sessions:
                print(sid)
        return 0

    if args.command == 'session-load':
        session = load_session(args.session_id)
        print(f'{session.session_id}')
        print(f'{len(session.messages)} messages')
        print(f'in={session.input_tokens} out={session.output_tokens}')
        return 0

    if args.command == 'summary':
        engine = HarnessEngine.create(registry)
        print(engine.render_session_report())
        return 0

    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
