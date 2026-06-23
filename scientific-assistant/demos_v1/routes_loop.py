"""
demos_v1/routes_loop.py — loop_engine(루프 엔지니어링) 실행 라우트

UIO 가 generator 에이전트(모델 A) + verifier 에이전트(모델 B, 다른 모델)를 골라
목표(goal)를 주면, loop_engine 으로 generate→verify 를 조건 충족까지 반복한다.

핵심: generator 와 verifier 를 '다른 모델'로 분리해 self-bias(자기채점 후함)를 막는다.

POST /api/loop/run
  body: {
    goal: "...",                 # 측정 가능한 목표
    generator_env: "<env id>",   # 짓는 AI 모델 (ENV_CONFIG 키)
    verifier_env:  "<env id>",   # 검사 AI 모델 (다른 모델 권장)
    max_rounds: 4,
    pass_score: 8.0,             # 루브릭 통과 점수(0~10)
    criteria: "정확성·명료성 엄격 채점",
    min_length: 0,               # 하드체크(선택)
    contains: ["AMHS"],          # 포함 필수 문자열(선택)
    max_tokens: 2048,
    name: "uio_loop"
  }
"""
from __future__ import annotations
from flask import request, jsonify


def register_loop_routes(app):
    @app.route("/api/loop/run", methods=["POST"])
    def api_loop_run():
        try:
            import loop_engine as le
        except Exception as e:
            return jsonify({"error": f"loop_engine import 실패: {e}"}), 200
        from demos_v1.models import ENV_CONFIG

        d = request.get_json(force=True, silent=True) or {}
        goal = (d.get("goal") or "").strip()
        gen_env = (d.get("generator_env") or d.get("generator") or "").strip()
        ver_env = (d.get("verifier_env") or d.get("verifier") or "").strip()
        if not goal:
            return jsonify({"error": "goal(목표)이 필요합니다."}), 400
        # env 해석: 'auto'/없는 env 면 실제 API 모델로 폴백 (gguf 제외)
        api_ids = [k for k in ENV_CONFIG if not str(k).startswith("gguf-")]

        def _resolve(env_id, avoid=None):
            if env_id and env_id in ENV_CONFIG and not str(env_id).startswith("gguf-"):
                return env_id
            # auto/없음 → avoid(상대편)와 다른 API 모델 우선
            for k in api_ids:
                if k != avoid:
                    return k
            return api_ids[0] if api_ids else None

        gen_env = _resolve(gen_env)
        ver_env = _resolve(ver_env, avoid=gen_env)   # 가능하면 generator 와 다른 모델
        gen = ENV_CONFIG.get(gen_env) if gen_env else None
        ver = ENV_CONFIG.get(ver_env) if ver_env else None
        if not gen or not ver:
            return jsonify({"error": "사용 가능한 API 모델이 없습니다 (서버 env 설정 확인)."}), 400

        try:
            max_rounds = max(1, min(int(d.get("max_rounds") or 4), 8))
        except (TypeError, ValueError):
            max_rounds = 4
        try:
            pass_score = float(d.get("pass_score") or 8.0)
        except (TypeError, ValueError):
            pass_score = 8.0
        try:
            max_tokens = int(d.get("max_tokens") or 2048)
        except (TypeError, ValueError):
            max_tokens = 2048
        criteria = (d.get("criteria") or "정확성·구조·실무성을 엄격하게 채점").strip()
        # 참고 데이터/컨텍스트 — generator 가 매 라운드 이걸 보고 분석한다 (없으면 일반론·환각)
        context_data = (d.get("context") or "").strip()

        # base_url: 데모스 env url 에서 /chat/completions 떼기 (loop_engine 이 다시 붙임)
        base = gen["url"].rsplit("/chat/completions", 1)[0]
        token = (gen.get("token") or ver.get("token") or "").strip()

        cfg = le.LLMConfig(
            base_url=base, token=token,
            generator_model=gen["model"], verifier_model=ver["model"],
            verify_ssl=False, max_tokens=max_tokens,
            timeout=90, retries=1,   # 안 되면 매달리지 말고 빨리 에러 반환
        )
        client = le.LLMClient(cfg)

        # 하드체크(closed loop 바닥)
        checks = []
        try:
            ml = int(d.get("min_length") or 0)
            if ml > 0:
                checks.append(le.check_min_length(ml))
        except (TypeError, ValueError):
            pass
        for s in (d.get("contains") or []):
            s = str(s).strip()
            if s:
                checks.append(le.check_contains(s))
        checks.append(le.check_no_placeholder())
        suite = le.CheckSuite(checks)

        rubric = le.Rubric(criteria, pass_score=pass_score)
        verifier = le.VerifierAgent(
            client, check_suite=suite, rubric=rubric,
            generator_model=gen["model"], verifier_model=ver["model"],
        )
        generator = le.Generator(client)
        # 참고 데이터가 있으면 매 라운드 generator 맥락으로 주입 (실제 데이터 분석)
        ctx_provider = (lambda c=context_data: c) if context_data else None
        spec = le.LoopSpec(
            name=(d.get("name") or "uio_loop"), goal=goal,
            generator=generator, verifier=verifier, max_rounds=max_rounds,
            context_provider=ctx_provider,
        )

        try:
            result = le.Loop(spec).run()
        except Exception as e:
            return jsonify({"error": f"루프 실행 실패: {e}",
                            "generator_model": gen["model"],
                            "verifier_model": ver["model"]}), 200

        rounds = []
        for r in result.rounds:
            v = r.verdict
            rounds.append({
                "index": r.index,
                "done": bool(v.done),
                "score": (v.rubric.score if getattr(v, "rubric", None) else None),
                "failures": [cr.name for cr in v.critical_failures],
                "artifact_preview": (r.artifact or "")[:600],
            })

        return jsonify({
            "status": result.status.value,
            "n_rounds": result.n_rounds,
            "rounds": rounds,
            "final_artifact": result.final_artifact,
            "generator_model": gen["model"],
            "verifier_model": ver["model"],
            "self_bias_warning": (gen["model"] == ver["model"]),
        })
