#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
magi_flow.py
MAGI Flow - 비주얼 워크플로우 빌더 & 실행 엔진
pc_assistant.py 의 API를 노드로 연결하여 파이프라인 실행

사용법:
    python magi_flow.py              # 기본 포트 8300
    python magi_flow.py --port 8300  # 포트 지정
"""

import os
import json
import uuid
import time
import asyncio
import logging
import argparse
import traceback
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("MAGIFlow")

# ========================================
# 설정
# ========================================
BASE_DIR = Path(__file__).parent
FLOWS_DIR = BASE_DIR / "flows"
FLOWS_DIR.mkdir(exist_ok=True)

# pc_assistant.py 서버 주소 (같은 머신이면 localhost)
MAGI_API_BASE = os.environ.get("MAGI_API_BASE", "http://localhost:10002/assistant")

app = FastAPI(title="MAGI Flow - Visual Workflow Builder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# 데이터 모델
# ========================================
class NodeConfig(BaseModel):
    id: str
    type: str                    # llm_chat, knowledge_search, api_call, transform, condition, output
    label: str = ""
    config: Dict[str, Any] = {}  # 노드별 설정
    position: Dict[str, float] = {"x": 0, "y": 0}


class EdgeConfig(BaseModel):
    id: str
    source: str       # 출발 노드 ID
    target: str       # 도착 노드 ID
    sourceHandle: str = "output"
    targetHandle: str = "input"


class FlowConfig(BaseModel):
    id: str = ""
    name: str = "새 워크플로우"
    description: str = ""
    nodes: List[NodeConfig] = []
    edges: List[EdgeConfig] = []
    created: str = ""
    updated: str = ""


class RunRequest(BaseModel):
    flow_id: str = ""
    flow: Optional[FlowConfig] = None  # 인라인 플로우도 지원
    inputs: Dict[str, Any] = {}        # 시작 입력값


# ========================================
# 노드 실행기 (Node Executors)
# ========================================
class NodeExecutor:
    """노드 타입별 실행 로직"""

    @staticmethod
    async def execute(node: NodeConfig, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        executor_map = {
            "input": NodeExecutor._exec_input,
            "llm_chat": NodeExecutor._exec_llm_chat,
            "llm_stream": NodeExecutor._exec_llm_stream,
            "knowledge_search": NodeExecutor._exec_knowledge_search,
            "knowledge_list": NodeExecutor._exec_knowledge_list,
            "api_call": NodeExecutor._exec_api_call,
            "transform": NodeExecutor._exec_transform,
            "condition": NodeExecutor._exec_condition,
            "merge": NodeExecutor._exec_merge,
            "output": NodeExecutor._exec_output,
            "delay": NodeExecutor._exec_delay,
            "loop": NodeExecutor._exec_loop,
            "template": NodeExecutor._exec_template,
            # ★ GGUF/API 분리 노드들
            "switch_env": NodeExecutor._exec_switch_env,
            "switch_model": NodeExecutor._exec_switch_model,
            "model_list": NodeExecutor._exec_model_list,
            "magi_status": NodeExecutor._exec_magi_status,
            "llm_gguf": NodeExecutor._exec_llm_gguf,
            "llm_api": NodeExecutor._exec_llm_api,
            "system_prompt": NodeExecutor._exec_system_prompt,
            "set_params": NodeExecutor._exec_set_params,
        }
        exec_fn = executor_map.get(node.type)
        if not exec_fn:
            return {"error": f"알 수 없는 노드 타입: {node.type}", "success": False}
        try:
            result = await exec_fn(node, inputs, context)
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"노드 실행 오류 [{node.id}:{node.type}]: {e}\n{traceback.format_exc()}")
            return {"error": str(e), "success": False}

    # ---- 입력 노드 ----
    @staticmethod
    async def _exec_input(node, inputs, context):
        """워크플로우 시작점 - 사용자 입력을 전달"""
        value = node.config.get("value", "") or inputs.get("user_input", "")
        return {"data": value}

    # ---- LLM 채팅 (pc_assistant /api/chat) ----
    @staticmethod
    async def _exec_llm_chat(node, inputs, context):
        message = _resolve_template(node.config.get("prompt", "{{input}}"), inputs)
        files = node.config.get("files", None)
        payload = {"message": message}
        if files:
            payload["files"] = files

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{MAGI_API_BASE}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return {"data": data.get("response", ""), "raw": data}

    # ---- LLM 스트리밍 ----
    @staticmethod
    async def _exec_llm_stream(node, inputs, context):
        message = _resolve_template(node.config.get("prompt", "{{input}}"), inputs)
        chunks = []
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{MAGI_API_BASE}/api/chat/stream",
                                     json={"message": message}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            if event.get("type") == "chunk":
                                chunks.append(event["content"])
                            elif event.get("type") == "done":
                                break
                        except json.JSONDecodeError:
                            pass
        full_response = "".join(chunks)
        return {"data": full_response}

    # ---- 지식베이스 검색 (pc_assistant /api/knowledge/suggest) ----
    @staticmethod
    async def _exec_knowledge_search(node, inputs, context):
        query = _resolve_template(node.config.get("query", "{{input}}"), inputs)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{MAGI_API_BASE}/api/knowledge/suggest", json={"query": query})
            resp.raise_for_status()
            data = resp.json()
        return {"data": data}

    # ---- 지식베이스 목록 ----
    @staticmethod
    async def _exec_knowledge_list(node, inputs, context):
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{MAGI_API_BASE}/api/knowledge")
            resp.raise_for_status()
            data = resp.json()
        return {"data": data.get("files", [])}

    # ---- 외부 API 호출 ----
    @staticmethod
    async def _exec_api_call(node, inputs, context):
        url = _resolve_template(node.config.get("url", ""), inputs)
        method = node.config.get("method", "GET").upper()
        headers = node.config.get("headers", {})
        body = node.config.get("body", None)
        if body and isinstance(body, str):
            body = _resolve_template(body, inputs)
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass

        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                resp = await client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                return {"error": f"지원하지 않는 HTTP 메서드: {method}"}
            try:
                data = resp.json()
            except Exception:
                data = resp.text
        return {"data": data, "status_code": resp.status_code}

    # ---- 데이터 변환 (Python 표현식) ----
    @staticmethod
    async def _exec_transform(node, inputs, context):
        expression = node.config.get("expression", "input")
        # 안전한 eval 환경 구성
        safe_globals = {"__builtins__": {}, "json": json, "len": len, "str": str,
                        "int": int, "float": float, "list": list, "dict": dict,
                        "sorted": sorted, "enumerate": enumerate, "range": range,
                        "zip": zip, "map": map, "filter": filter, "sum": sum,
                        "min": min, "max": max, "abs": abs, "round": round,
                        "isinstance": isinstance, "type": type, "True": True,
                        "False": False, "None": None}
        safe_locals = {"input": inputs.get("data", inputs), "inputs": inputs, "context": context}
        result = eval(expression, safe_globals, safe_locals)
        return {"data": result}

    # ---- 조건 분기 ----
    @staticmethod
    async def _exec_condition(node, inputs, context):
        expression = node.config.get("condition", "True")
        safe_globals = {"__builtins__": {}, "len": len, "str": str, "int": int,
                        "float": float, "True": True, "False": False, "None": None}
        safe_locals = {"input": inputs.get("data", inputs), "inputs": inputs}
        result = eval(expression, safe_globals, safe_locals)
        branch = "true" if result else "false"
        return {"data": inputs.get("data", inputs), "branch": branch}

    # ---- 병합 ----
    @staticmethod
    async def _exec_merge(node, inputs, context):
        strategy = node.config.get("strategy", "concat")
        if strategy == "concat" and isinstance(inputs.get("data"), list):
            return {"data": "\n".join(str(x) for x in inputs["data"])}
        return {"data": inputs}

    # ---- 출력 ----
    @staticmethod
    async def _exec_output(node, inputs, context):
        label = node.config.get("label", "결과")
        return {"data": inputs.get("data", inputs), "label": label}

    # ---- 딜레이 ----
    @staticmethod
    async def _exec_delay(node, inputs, context):
        seconds = float(node.config.get("seconds", 1))
        await asyncio.sleep(seconds)
        return {"data": inputs.get("data", inputs)}

    # ---- 루프 ----
    @staticmethod
    async def _exec_loop(node, inputs, context):
        items = inputs.get("data", [])
        if not isinstance(items, list):
            items = [items]
        return {"data": items, "is_loop": True, "items": items}

    # ---- 텍스트 템플릿 ----
    @staticmethod
    async def _exec_template(node, inputs, context):
        template = node.config.get("template", "{{input}}")
        result = _resolve_template(template, inputs)
        return {"data": result}

    # ========================================
    # ★ GGUF/API 전용 노드들
    # ========================================

    # ---- 환경 전환 (local/dev/prod/common) ----
    @staticmethod
    async def _exec_switch_env(node, inputs, context):
        """LLM 모드 전환: local(GGUF) ↔ API(dev/prod/common)"""
        env = node.config.get("env", "local")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{MAGI_API_BASE}/api/set_env", json={"env": env})
            resp.raise_for_status()
            data = resp.json()
        mode_label = "GGUF 로컬" if env == "local" else f"API ({env})"
        return {"data": data, "mode": mode_label}

    # ---- GGUF 모델 변경 ----
    @staticmethod
    async def _exec_switch_model(node, inputs, context):
        """로컬 GGUF 모델 변경 (qwen3-14b, qwen3-8b, gemma3-12b 등)"""
        model_key = _resolve_template(node.config.get("model_key", "qwen3-8b"), inputs)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{MAGI_API_BASE}/api/models/switch",
                                     json={"model_key": model_key})
            resp.raise_for_status()
            data = resp.json()
        return {"data": data}

    # ---- 모델 목록 조회 ----
    @staticmethod
    async def _exec_model_list(node, inputs, context):
        """사용 가능한 GGUF 모델 + 현재 모드 조회"""
        async with httpx.AsyncClient(timeout=15) as client:
            resp_models = await client.get(f"{MAGI_API_BASE}/api/models")
            resp_status = await client.get(f"{MAGI_API_BASE}/api/status")
            models = resp_models.json()
            status = resp_status.json()
        return {
            "data": {
                "mode": status.get("mode", "unknown"),
                "env": status.get("env", "unknown"),
                "current_model": status.get("model_name", "unknown"),
                "models": models.get("models", [])
            }
        }

    # ---- MAGI 상태 조회 ----
    @staticmethod
    async def _exec_magi_status(node, inputs, context):
        """MAGI 시스템 전체 상태 (모드, 모델, 토큰 사용량 등)"""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{MAGI_API_BASE}/api/status")
            resp.raise_for_status()
            data = resp.json()
        return {"data": data}

    # ---- GGUF 전용 LLM 호출 (로컬 모드 강제) ----
    @staticmethod
    async def _exec_llm_gguf(node, inputs, context):
        """GGUF 로컬 모델로 강제 전환 후 채팅"""
        message = _resolve_template(node.config.get("prompt", "{{input}}"), inputs)
        model_key = node.config.get("model_key", "")  # 빈 문자열이면 현재 모델 유지

        async with httpx.AsyncClient(timeout=120) as client:
            # 1. 로컬 모드로 전환
            await client.post(f"{MAGI_API_BASE}/api/set_env", json={"env": "local"})

            # 2. 모델 변경 (지정된 경우)
            if model_key:
                await client.post(f"{MAGI_API_BASE}/api/models/switch",
                                  json={"model_key": model_key})

            # 3. 채팅 요청
            resp = await client.post(f"{MAGI_API_BASE}/api/chat",
                                     json={"message": message})
            resp.raise_for_status()
            data = resp.json()

        return {"data": data.get("response", ""), "raw": data, "mode": "GGUF_LOCAL"}

    # ---- API 전용 LLM 호출 (API 모드 강제) ----
    @staticmethod
    async def _exec_llm_api(node, inputs, context):
        """API 모델로 강제 전환 후 채팅 (dev/prod/common)"""
        message = _resolve_template(node.config.get("prompt", "{{input}}"), inputs)
        env = node.config.get("env", "common")  # dev, prod, common

        async with httpx.AsyncClient(timeout=120) as client:
            # 1. API 모드로 전환
            await client.post(f"{MAGI_API_BASE}/api/set_env", json={"env": env})

            # 2. 채팅 요청
            resp = await client.post(f"{MAGI_API_BASE}/api/chat",
                                     json={"message": message})
            resp.raise_for_status()
            data = resp.json()

        return {"data": data.get("response", ""), "raw": data, "mode": f"API_{env.upper()}"}

    # ---- 시스템 프롬프트 설정/조회 ----
    @staticmethod
    async def _exec_system_prompt(node, inputs, context):
        """시스템 프롬프트 조회 또는 설정"""
        action = node.config.get("action", "get")  # get / set
        async with httpx.AsyncClient(timeout=15) as client:
            if action == "set":
                content = _resolve_template(node.config.get("prompt_text", ""), inputs)
                resp = await client.post(f"{MAGI_API_BASE}/api/prompt/system",
                                         json={"content": content})
            else:
                resp = await client.get(f"{MAGI_API_BASE}/api/prompt/system")
            resp.raise_for_status()
            data = resp.json()
        return {"data": data}

    # ---- LLM 파라미터 설정 ----
    @staticmethod
    async def _exec_set_params(node, inputs, context):
        """LLM 파라미터 설정 (temperature, max_tokens 등)"""
        params = {}
        if "temperature" in node.config:
            params["temperature"] = float(node.config["temperature"])
        if "max_tokens" in node.config:
            params["max_tokens"] = int(node.config["max_tokens"])
        if "repeat_penalty" in node.config:
            params["repeat_penalty"] = float(node.config["repeat_penalty"])

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{MAGI_API_BASE}/api/params", json=params)
            resp.raise_for_status()
            data = resp.json()
        return {"data": data}


# ========================================
# 워크플로우 실행 엔진
# ========================================
class FlowEngine:
    """토폴로지 정렬 기반 DAG 실행 엔진"""

    def __init__(self, flow: FlowConfig):
        self.flow = flow
        self.node_map = {n.id: n for n in flow.nodes}
        self.results: Dict[str, Any] = {}
        self.execution_log: List[Dict] = []

    def _build_graph(self) -> Dict[str, List[str]]:
        """인접 리스트 (target → sources)"""
        deps = {n.id: [] for n in self.flow.nodes}
        for edge in self.flow.edges:
            if edge.target in deps:
                deps[edge.target].append(edge.source)
        return deps

    def _topo_sort(self) -> List[str]:
        deps = self._build_graph()
        in_degree = {nid: len(srcs) for nid, srcs in deps.items()}
        queue = [nid for nid, d in in_degree.items() if d == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for edge in self.flow.edges:
                if edge.source == nid:
                    in_degree[edge.target] -= 1
                    if in_degree[edge.target] == 0:
                        queue.append(edge.target)
        if len(order) != len(self.flow.nodes):
            logger.warning("순환 참조 감지! 일부 노드가 실행되지 않을 수 있습니다.")
        return order

    async def run(self, inputs: Dict[str, Any], ws: Optional[WebSocket] = None) -> Dict[str, Any]:
        """워크플로우 실행"""
        order = self._topo_sort()
        context = {"flow_id": self.flow.id, "start_time": time.time(), "inputs": inputs}

        for node_id in order:
            node = self.node_map.get(node_id)
            if not node:
                continue

            # 입력 수집: 연결된 소스 노드들의 결과
            deps = self._build_graph()
            node_inputs = dict(inputs)  # 기본 입력 복사
            for src_id in deps.get(node_id, []):
                if src_id in self.results:
                    src_result = self.results[src_id]
                    if "data" in src_result:
                        node_inputs["data"] = src_result["data"]
                        node_inputs["input"] = src_result["data"]

            # 조건 분기 확인 (이전 condition 노드의 branch 결과)
            skip = False
            for edge in self.flow.edges:
                if edge.target == node_id and edge.source in self.results:
                    src_result = self.results[edge.source]
                    if "branch" in src_result:
                        expected = edge.sourceHandle  # "true" or "false"
                        if src_result["branch"] != expected:
                            skip = True
                            break

            if skip:
                self.results[node_id] = {"data": None, "skipped": True}
                if ws:
                    await ws.send_json({"type": "node_skip", "node_id": node_id})
                continue

            # 실행
            start = time.time()
            if ws:
                await ws.send_json({"type": "node_start", "node_id": node_id, "label": node.label})

            result = await NodeExecutor.execute(node, node_inputs, context)
            elapsed = time.time() - start

            self.results[node_id] = result
            log_entry = {
                "node_id": node_id, "type": node.type, "label": node.label,
                "success": result.get("success", False), "elapsed": round(elapsed, 3),
                "data_preview": str(result.get("data", ""))[:200]
            }
            self.execution_log.append(log_entry)

            if ws:
                await ws.send_json({
                    "type": "node_done", "node_id": node_id,
                    "success": result.get("success", False),
                    "elapsed": round(elapsed, 3),
                    "preview": str(result.get("data", ""))[:500]
                })

            logger.info(f"✅ [{node.type}] {node.label or node_id} → {elapsed:.2f}s")

        # 최종 결과: output 노드들의 데이터
        final = {}
        for node in self.flow.nodes:
            if node.type == "output" and node.id in self.results:
                label = self.results[node.id].get("label", node.id)
                final[label] = self.results[node.id].get("data")

        if not final:
            # output 노드가 없으면 마지막 노드 결과
            last_id = order[-1] if order else None
            if last_id and last_id in self.results:
                final["result"] = self.results[last_id].get("data")

        return {
            "success": True,
            "outputs": final,
            "execution_log": self.execution_log,
            "total_time": round(time.time() - context["start_time"], 3)
        }


# ========================================
# 유틸리티
# ========================================
def _resolve_template(template: str, inputs: Dict[str, Any]) -> str:
    """{{변수}} 치환"""
    result = template
    for key, value in inputs.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if not isinstance(value, str) else value)
    # {{input}} 특수 처리
    if "{{input}}" in result and "data" in inputs:
        result = result.replace("{{input}}", str(inputs["data"]))
    return result


# ========================================
# API 엔드포인트
# ========================================

@app.get("/")
async def serve_ui():
    """메인 플로우 에디터 UI"""
    ui_path = BASE_DIR / "magi_flow_ui.html"
    if ui_path.exists():
        return FileResponse(ui_path, media_type="text/html")
    return HTMLResponse("<h1>MAGI Flow</h1><p>magi_flow_ui.html 파일이 필요합니다.</p>")


# ---- 플로우 CRUD ----
@app.get("/api/flows")
async def list_flows():
    flows = []
    for f in FLOWS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            flows.append({"id": data.get("id", f.stem), "name": data.get("name", f.stem),
                          "description": data.get("description", ""),
                          "nodes": len(data.get("nodes", [])),
                          "updated": data.get("updated", "")})
        except Exception:
            pass
    flows.sort(key=lambda x: x.get("updated", ""), reverse=True)
    return {"success": True, "flows": flows}


@app.post("/api/flows/save")
async def save_flow(flow: FlowConfig):
    if not flow.id:
        flow.id = str(uuid.uuid4())[:8]
    flow.updated = datetime.now().isoformat()
    if not flow.created:
        flow.created = flow.updated
    path = FLOWS_DIR / f"{flow.id}.json"
    path.write_text(flow.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"💾 플로우 저장: {flow.name} ({flow.id})")
    return {"success": True, "id": flow.id}


@app.get("/api/flows/{flow_id}")
async def get_flow(flow_id: str):
    path = FLOWS_DIR / f"{flow_id}.json"
    if not path.exists():
        return JSONResponse({"success": False, "error": "플로우를 찾을 수 없습니다."}, status_code=404)
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"success": True, "flow": data}


@app.delete("/api/flows/{flow_id}")
async def delete_flow(flow_id: str):
    path = FLOWS_DIR / f"{flow_id}.json"
    if path.exists():
        path.unlink()
    return {"success": True}


# ---- 플로우 실행 ----
@app.post("/api/flows/run")
async def run_flow(req: RunRequest):
    """동기 실행 (HTTP)"""
    flow = await _load_flow(req)
    if not flow:
        return JSONResponse({"success": False, "error": "플로우를 찾을 수 없습니다."}, status_code=404)
    engine = FlowEngine(flow)
    result = await engine.run(req.inputs)
    return result


@app.websocket("/ws/flow/run")
async def ws_run_flow(ws: WebSocket):
    """WebSocket 실시간 실행 (노드별 진행 상황 전송)"""
    await ws.accept()
    try:
        data = await ws.receive_json()
        req = RunRequest(**data)
        flow = await _load_flow(req)
        if not flow:
            await ws.send_json({"type": "error", "message": "플로우를 찾을 수 없습니다."})
            return
        await ws.send_json({"type": "start", "flow_name": flow.name, "node_count": len(flow.nodes)})
        engine = FlowEngine(flow)
        result = await engine.run(req.inputs, ws=ws)
        await ws.send_json({"type": "complete", **result})
    except WebSocketDisconnect:
        logger.info("WebSocket 연결 종료")
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ---- 노드 타입 정보 ----
@app.get("/api/node-types")
async def get_node_types():
    """사용 가능한 노드 타입 목록 (UI에서 사이드바에 표시)"""
    return {"success": True, "types": [
        {"type": "input", "label": "📥 입력", "category": "기본",
         "description": "워크플로우 시작점. 사용자 입력을 받습니다.",
         "config_schema": {"value": {"type": "text", "label": "기본값", "default": ""}}},

        {"type": "llm_chat", "label": "🤖 LLM 채팅", "category": "MAGI",
         "description": "MAGI LLM에 메시지를 보내고 응답을 받습니다.",
         "config_schema": {"prompt": {"type": "textarea", "label": "프롬프트", "default": "{{input}}"}}},

        {"type": "llm_stream", "label": "🌊 LLM 스트리밍", "category": "MAGI",
         "description": "MAGI LLM 스트리밍 응답을 받습니다.",
         "config_schema": {"prompt": {"type": "textarea", "label": "프롬프트", "default": "{{input}}"}}},

        {"type": "knowledge_search", "label": "📚 지식 검색", "category": "MAGI",
         "description": "MAGI 지식베이스에서 관련 정보를 검색합니다.",
         "config_schema": {"query": {"type": "text", "label": "검색어", "default": "{{input}}"}}},

        {"type": "knowledge_list", "label": "📋 지식 목록", "category": "MAGI",
         "description": "지식베이스 문서 목록을 가져옵니다.",
         "config_schema": {}},

        {"type": "api_call", "label": "🌐 API 호출", "category": "연동",
         "description": "외부 REST API를 호출합니다.",
         "config_schema": {
             "url": {"type": "text", "label": "URL", "default": ""},
             "method": {"type": "select", "label": "메서드", "options": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
             "headers": {"type": "json", "label": "헤더", "default": {}},
             "body": {"type": "textarea", "label": "Body", "default": ""}}},

        {"type": "transform", "label": "🔄 변환", "category": "처리",
         "description": "Python 표현식으로 데이터를 변환합니다.",
         "config_schema": {"expression": {"type": "textarea", "label": "표현식", "default": "input"}}},

        {"type": "template", "label": "📝 텍스트 템플릿", "category": "처리",
         "description": "{{변수}}를 사용해 텍스트를 조합합니다.",
         "config_schema": {"template": {"type": "textarea", "label": "템플릿", "default": "{{input}}"}}},

        {"type": "condition", "label": "❓ 조건 분기", "category": "흐름",
         "description": "조건에 따라 True/False 경로로 분기합니다.",
         "config_schema": {"condition": {"type": "text", "label": "조건식", "default": "True"}}},

        {"type": "merge", "label": "🔗 병합", "category": "흐름",
         "description": "여러 입력을 하나로 합칩니다.",
         "config_schema": {"strategy": {"type": "select", "label": "전략", "options": ["concat", "list", "dict"], "default": "concat"}}},

        {"type": "delay", "label": "⏱️ 딜레이", "category": "흐름",
         "description": "지정 시간만큼 대기합니다.",
         "config_schema": {"seconds": {"type": "number", "label": "초", "default": 1}}},

        {"type": "loop", "label": "🔁 루프", "category": "흐름",
         "description": "리스트의 각 항목에 대해 반복합니다.",
         "config_schema": {}},

        {"type": "output", "label": "📤 출력", "category": "기본",
         "description": "워크플로우 결과를 출력합니다.",
         "config_schema": {"label": {"type": "text", "label": "출력 이름", "default": "결과"}}},

        # ★ GGUF 로컬 모델 노드들
        {"type": "llm_gguf", "label": "🖥️ GGUF 로컬 LLM", "category": "GGUF",
         "description": "로컬 GGUF 모델(Qwen3, Gemma3 등)로 강제 전환 후 채팅합니다.",
         "config_schema": {
             "prompt": {"type": "textarea", "label": "프롬프트", "default": "{{input}}"},
             "model_key": {"type": "select", "label": "GGUF 모델",
                           "options": ["", "qwen3-14b", "qwen3-8b", "qwen3.5-9b", "gemma3-12b",
                                       "oh-dcft-claude", "qwen25-7b", "llama-korean-8b"],
                           "default": ""}}},

        {"type": "switch_model", "label": "🔀 GGUF 모델 변경", "category": "GGUF",
         "description": "로컬 GGUF 모델을 변경합니다 (모델 로딩 시간 소요).",
         "config_schema": {
             "model_key": {"type": "select", "label": "모델 선택",
                           "options": ["qwen3-14b", "qwen3-8b", "qwen3.5-9b", "gemma3-12b",
                                       "oh-dcft-claude", "qwen25-7b", "llama-korean-8b"],
                           "default": "qwen3-8b"}}},

        {"type": "model_list", "label": "📋 GGUF 모델 목록", "category": "GGUF",
         "description": "사용 가능한 GGUF 모델 목록과 현재 모드를 조회합니다.",
         "config_schema": {}},

        # ★ API 모델 노드들
        {"type": "llm_api", "label": "☁️ API LLM", "category": "API",
         "description": "SK Hynix API 모델(480B/235B/120B)로 강제 전환 후 채팅합니다.",
         "config_schema": {
             "prompt": {"type": "textarea", "label": "프롬프트", "default": "{{input}}"},
             "env": {"type": "select", "label": "API 환경",
                     "options": ["dev", "prod", "common"],
                     "default": "common"}}},

        # ★ 시스템 설정 노드들
        {"type": "switch_env", "label": "⚡ 환경 전환", "category": "설정",
         "description": "LLM 모드를 전환합니다: local(GGUF) ↔ API(dev/prod/common).",
         "config_schema": {
             "env": {"type": "select", "label": "환경",
                     "options": ["local", "dev", "prod", "common"],
                     "default": "local"}}},

        {"type": "magi_status", "label": "📊 MAGI 상태", "category": "설정",
         "description": "현재 MAGI 시스템 상태 (모드, 모델, 토큰 사용량)를 조회합니다.",
         "config_schema": {}},

        {"type": "system_prompt", "label": "📜 시스템 프롬프트", "category": "설정",
         "description": "시스템 프롬프트를 조회하거나 변경합니다.",
         "config_schema": {
             "action": {"type": "select", "label": "동작", "options": ["get", "set"], "default": "get"},
             "prompt_text": {"type": "textarea", "label": "프롬프트 내용 (set 시)", "default": ""}}},

        {"type": "set_params", "label": "🎛️ LLM 파라미터", "category": "설정",
         "description": "LLM 파라미터를 설정합니다 (temperature, max_tokens 등).",
         "config_schema": {
             "temperature": {"type": "number", "label": "Temperature", "default": 0.7},
             "max_tokens": {"type": "number", "label": "Max Tokens", "default": 4096},
             "repeat_penalty": {"type": "number", "label": "Repeat Penalty", "default": 1.1}}},
    ]}


# ---- MAGI 상태 확인 ----
@app.get("/api/magi/status")
async def magi_status():
    """pc_assistant 서버 연결 상태 확인"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{MAGI_API_BASE}/api/status")
            data = resp.json()
            return {"connected": True, "status": data}
    except Exception as e:
        return {"connected": False, "error": str(e)}


# ---- 헬퍼 ----
async def _load_flow(req: RunRequest) -> Optional[FlowConfig]:
    if req.flow:
        return req.flow
    if req.flow_id:
        path = FLOWS_DIR / f"{req.flow_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return FlowConfig(**data)
    return None


# ========================================
# 메인
# ========================================
if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="MAGI Flow - Visual Workflow Builder")
    parser.add_argument("--port", type=int, default=8300, help="서버 포트 (기본: 8300)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="바인드 주소")
    parser.add_argument("--magi-url", type=str, default=None, help="MAGI API 주소")
    args = parser.parse_args()

    if args.magi_url:
        MAGI_API_BASE = args.magi_url

    logger.info(f"🚀 MAGI Flow 시작 → http://localhost:{args.port}")
    logger.info(f"📡 MAGI API: {MAGI_API_BASE}")
    uvicorn.run(app, host=args.host, port=args.port)
