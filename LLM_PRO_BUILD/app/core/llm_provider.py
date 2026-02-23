#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 LLM 프로바이더 - API 우선, GGUF 폴백
"""

import os
import re
import gc
import time
import logging

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class LLMProvider:
    """API + GGUF 통합 LLM 호출"""

    def __init__(self, config):
        self.config = config
        self.local_llm = None  # llama-cpp 모델 인스턴스

    def load_local_model(self) -> bool:
        """GGUF 로컬 모델 로드"""
        try:
            from llama_cpp import Llama

            model_path = self.config.gguf_model_path
            if not os.path.exists(model_path):
                logger.error(f"GGUF 파일 없음: {model_path}")
                return False

            # GPU 지원 확인
            try:
                from llama_cpp import llama_supports_gpu_offload
                gpu_ok = llama_supports_gpu_offload()
                logger.info(f"llama-cpp GPU 오프로드 지원: {gpu_ok}")
            except Exception:
                gpu_ok = False

            # 모델별 설정
            gguf_cfg = self.config.get_gguf_config()
            gpu_layers = gguf_cfg.get("gpu_layers", 35)
            n_ctx = gguf_cfg.get("ctx", 8192)

            logger.info(f"GGUF 모델 로딩: {self.config.current_gguf_model} | path={model_path}")
            logger.info(f"  n_gpu_layers={gpu_layers}, n_ctx={n_ctx}, GPU={gpu_ok}")

            # CPU 스레드 수 자동 감지 (물리 코어의 절반 ~ 전체 사용)
            n_threads = max(4, (os.cpu_count() or 8) // 2)

            self.local_llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=gpu_layers,
                n_batch=512,
                verbose=False
            )
            logger.info(f"  n_threads={n_threads} (auto-detected, cpu_count={os.cpu_count()})")
            logger.info(f"GGUF 모델 로드 완료! (n_gpu_layers={gpu_layers})")
            return True

        except ImportError as ie:
            import sys
            logger.error(f"llama-cpp-python import 실패: {ie}")
            logger.error(f"현재 Python: {sys.executable} (v{sys.version.split()[0]})")
            logger.error(f"설치 확인: {sys.executable} -m pip install llama-cpp-python")
            return False
        except Exception as e:
            logger.error(f"GGUF 모델 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def unload_local_model(self):
        """로컬 모델 해제"""
        if self.local_llm is not None:
            del self.local_llm
            self.local_llm = None
            gc.collect()

    def switch_model(self, model_key: str) -> bool:
        """GGUF 모델 전환"""
        if not self.config.switch_gguf_model(model_key):
            return False
        self.unload_local_model()
        return self.load_local_model()

    def call(self, prompt: str, system_prompt: str = "", max_tokens: int = 0,
             session=None) -> dict:
        """LLM 호출 (모드에 따라 자동 선택)
        Args:
            session: 외부 requests.Session 객체 (취소 지원용, 선택)
                     session.close() 호출 시 진행 중인 요청 즉시 중단
        """
        if max_tokens <= 0:
            max_tokens = self.config.get_max_tokens()
        if self.config.llm_mode == "local":
            return self._call_gguf(prompt, system_prompt, max_tokens)
        else:
            return self._call_api(prompt, system_prompt, max_tokens, session=session)

    def _call_api(self, prompt: str, system_prompt: str = "",
                  max_tokens: int = 4096, session=None) -> dict:
        """SK Hynix API 호출
        Args:
            session: 외부 requests.Session (취소 시 session.close()로 즉시 중단)
        """
        if not HAS_REQUESTS:
            return {"success": False, "error": "requests 미설치 (pip install requests)"}
        if not self.config.api_token:
            return {"success": False, "error": "API 토큰 없음"}

        headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.api_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3
        }

        # 외부 세션이 있으면 사용 (cancel 시 session.close()로 즉시 중단 가능)
        http = session if session else requests

        try:
            response = http.post(
                self.config.api_url, headers=headers, json=data, timeout=300
            )
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return {"success": True, "content": content}
            else:
                return {"success": False, "error": f"API 오류: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _call_gguf(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> dict:
        """GGUF 로컬 모델 호출"""
        if self.local_llm is None:
            return {"success": False, "error": "로컬 모델이 로드되지 않았습니다"}

        # Qwen3 ChatML 포맷
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        try:
            logger.info(f"GGUF 추론 시작 (prompt {len(full_prompt)}자, max_tokens={max_tokens})")
            t0 = time.time()

            output = self.local_llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=0.3,
                top_p=0.9,
                stop=["<|im_end|>", "<|im_start|>"],
                echo=False
            )

            elapsed = time.time() - t0
            content = output["choices"][0]["text"].strip()
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            logger.info(f"GGUF 추론 완료: {elapsed:.1f}초, 응답 {len(content)}자")
            return {"success": True, "content": content}
        except Exception as e:
            logger.error(f"GGUF 추론 오류: {e}")
            return {"success": False, "error": str(e)}

    def call_gguf_chat(self, messages: list, max_tokens: int = 0, stream: bool = False) -> dict:
        """OpenAI 호환 형식으로 GGUF 호출 (aider/gguf_server용)"""
        if max_tokens <= 0:
            max_tokens = self.config.get_max_tokens()
        if self.local_llm is None:
            return {"success": False, "error": "로컬 모델 미로드"}

        system_prompt = ""
        user_prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                user_prompt = content
            elif role == "assistant":
                user_prompt += f"\n\nassistant: {content}"

        full = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt} /no_think<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        try:
            t0 = time.time()
            output = self.local_llm(
                full, max_tokens=max_tokens, temperature=0.3, top_p=0.9,
                stop=["<|im_end|>", "<|im_start|>"], echo=False
            )
            elapsed = time.time() - t0
            raw_text = output["choices"][0]["text"].strip()
            usage = output.get("usage", {})

            # <think>...</think> 제거
            cleaned = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
            if not cleaned and '</think>' in raw_text:
                cleaned = raw_text.split('</think>', 1)[-1].strip()
            if not cleaned:
                cleaned = raw_text

            logger.info(f"GGUF 추론 완료 [chat]: {elapsed:.1f}초, {len(cleaned)}자")
            return {"success": True, "content": cleaned, "usage": usage}
        except Exception as e:
            logger.error(f"GGUF chat 오류: {e}")
            return {"success": False, "error": str(e)}
