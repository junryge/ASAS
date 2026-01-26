"""
OHT2 시뮬레이터 - 웹 서버
웹소켓 기반 실시간 시뮬레이션 데이터 전송

사용법:
    python server.py [--port 8765] [--host localhost]
"""

import asyncio
import json
import argparse
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("[WARNING] websockets 모듈이 없습니다. pip install websockets")

from core import SimulationEngine, create_demo_layout, JobPriority


class OHT2SimulatorServer:
    """OHT2 시뮬레이터 서버"""

    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.engine = create_demo_layout()
        self.clients = set()
        self.is_running = False

    async def register(self, websocket):
        """클라이언트 등록"""
        self.clients.add(websocket)
        print(f"[INFO] Client connected. Total: {len(self.clients)}")

    async def unregister(self, websocket):
        """클라이언트 등록 해제"""
        self.clients.discard(websocket)
        print(f"[INFO] Client disconnected. Total: {len(self.clients)}")

    async def broadcast(self, message: str):
        """모든 클라이언트에 메시지 전송"""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )

    async def handle_client(self, websocket, path):
        """클라이언트 연결 처리"""
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.handle_command(data, websocket)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def handle_command(self, data: dict, websocket):
        """클라이언트 명령 처리"""
        command = data.get('command')

        if command == 'start':
            self.is_running = True
            await websocket.send(json.dumps({'status': 'started'}))

        elif command == 'stop':
            self.is_running = False
            self.engine.stop()
            await websocket.send(json.dumps({'status': 'stopped'}))

        elif command == 'pause':
            self.engine.pause()
            await websocket.send(json.dumps({'status': 'paused'}))

        elif command == 'resume':
            self.engine.resume()
            await websocket.send(json.dumps({'status': 'resumed'}))

        elif command == 'reset':
            self.engine.reset()
            await websocket.send(json.dumps({'status': 'reset'}))

        elif command == 'create_job':
            source = data.get('source', 1)
            dest = data.get('dest', 10)
            priority_str = data.get('priority', 'NORMAL')
            is_hotlot = data.get('is_hotlot', False)

            priority = JobPriority[priority_str]
            job = self.engine.create_job(source, dest, priority, is_hotlot)

            await websocket.send(json.dumps({
                'status': 'job_created',
                'job_id': job.id
            }))

        elif command == 'get_state':
            state = self.engine.get_state()
            await websocket.send(json.dumps(state))

    async def simulation_loop(self):
        """시뮬레이션 루프"""
        while True:
            if self.is_running and not self.engine.is_paused:
                self.engine.tick()
                state = self.engine.get_state()
                await self.broadcast(json.dumps(state))
            await asyncio.sleep(0.1)  # 100ms 간격

    async def run(self):
        """서버 실행"""
        if not HAS_WEBSOCKETS:
            print("[ERROR] websockets 모듈이 필요합니다.")
            return

        # 시뮬레이션 루프 시작
        asyncio.create_task(self.simulation_loop())

        # 웹소켓 서버 시작
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"[INFO] WebSocket server started at ws://{self.host}:{self.port}")
            await asyncio.Future()  # 무한 대기


class StaticFileHandler(SimpleHTTPRequestHandler):
    """정적 파일 서버 핸들러"""

    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        """경로 변환"""
        if self.directory:
            path = path.lstrip('/')
            return str(Path(self.directory) / path)
        return super().translate_path(path)


def run_http_server(port: int = 8080):
    """HTTP 서버 실행 (정적 파일 제공)"""
    web_dir = Path(__file__).parent / 'web'
    handler = partial(StaticFileHandler, directory=str(web_dir))

    with HTTPServer(('', port), handler) as httpd:
        print(f"[INFO] HTTP server started at http://localhost:{port}")
        httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description='OHT2 Simulator Server')
    parser.add_argument('--host', default='localhost', help='WebSocket host')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket port')
    parser.add_argument('--http-port', type=int, default=8080, help='HTTP port')
    parser.add_argument('--no-http', action='store_true', help='Disable HTTP server')
    args = parser.parse_args()

    # HTTP 서버 (별도 스레드)
    if not args.no_http:
        http_thread = threading.Thread(
            target=run_http_server,
            args=(args.http_port,),
            daemon=True
        )
        http_thread.start()

    # 웹소켓 서버
    server = OHT2SimulatorServer(args.host, args.ws_port)

    print("\n" + "=" * 50)
    print("OHT2 Simulator Server")
    print("=" * 50)
    print(f"Web UI: http://localhost:{args.http_port}")
    print(f"WebSocket: ws://{args.host}:{args.ws_port}")
    print("=" * 50 + "\n")

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")


if __name__ == '__main__':
    main()
