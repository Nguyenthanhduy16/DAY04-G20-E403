from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import run_model_tool_loop, trim_history, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"


def clear_dead_proxy_env() -> None:
    for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        if os.getenv(key) == "http://127.0.0.1:9":
            os.environ.pop(key, None)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def init_transcript(provider_name: str, model: str | None, version: str, max_tool_rounds: int, history_window: int) -> None:
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    artifact = build_artifact_version(version, system_prompt_path, tools_path)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version), safe_slug(provider_name), timestamp])
    st.session_state.transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": model,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.session_state.history = []


def render_trace(turn: dict[str, Any]) -> None:
    with st.expander("Tool trace", expanded=bool(turn.get("tool_events"))):
        st.caption(f"status={turn.get('status')} | rounds={len(turn.get('rounds', []))}")
        for round_item in turn.get("rounds", []):
            st.markdown(f"**Round {round_item.get('round')}**")
            calls = round_item.get("tool_calls") or []
            results = round_item.get("tool_results") or []
            if not calls:
                st.caption("No tool call")
            for index, call in enumerate(calls):
                result = results[index] if index < len(results) else {}
                result_payload = result.get("result", {}) if isinstance(result, dict) else {}
                status = "error" if isinstance(result_payload, dict) and result_payload.get("error") else "ok"
                st.code(compact_json({"status": status, "tool": call.get("name"), "args": call.get("args"), "result": result_payload}), language="json")


def render_history() -> None:
    for turn in st.session_state.transcript.get("turns", []):
        with st.chat_message("user"):
            st.write(turn.get("user", ""))
        with st.chat_message("assistant"):
            st.write(turn.get("assistant_text") or turn.get("error") or "")
            render_trace(turn)


def main() -> None:
    clear_dead_proxy_env()
    load_lab_env(ROOT)

    st.set_page_config(page_title="Research Agent Lab", layout="wide")
    st.title("Research Agent Lab")

    with st.sidebar:
        provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)
        version = st.text_input("Version", value="v3")
        model = st.text_input("Model override", value="") or None
        history_window = st.number_input("History window", min_value=0, max_value=20, value=5, step=1)
        max_tool_rounds = st.number_input("Max tool rounds", min_value=1, max_value=8, value=4, step=1)
        reset = st.button("New transcript")

        system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
        tools_path = ARTIFACTS_DIR / "tools.yaml"
        artifact = build_artifact_version(version, system_prompt_path, tools_path)
        st.caption(f"artifact={artifact.artifact_version}")
        st.caption(f"prompt={artifact.prompt_hash[:12]}")
        st.caption(f"tools={artifact.tools_hash[:12]}")

    if reset or "transcript" not in st.session_state:
        init_transcript(provider_name, model, version, int(max_tool_rounds), int(history_window))

    render_history()

    user_text = st.chat_input("Ask the research agent")
    if not user_text:
        return

    with st.chat_message("user"):
        st.write(user_text)

    turn_record: dict[str, Any] = {
        "turn_index": len(st.session_state.transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    try:
        system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
        declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
        openai_tools = to_openai_tools(declarations)
        provider = make_provider(provider_name)
        messages = [
            {"role": "system", "content": system_prompt},
            *trim_history(st.session_state.history, int(history_window)),
            {"role": "user", "content": user_text},
        ]
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=model,
            max_tool_rounds=int(max_tool_rounds),
        )
        turn_record.update(result)
        assistant_text = result.get("assistant_text", "")
        st.session_state.history.append({"role": "user", "content": user_text})
        st.session_state.history.append({"role": "assistant", "content": assistant_text})
    except Exception as exc:
        turn_record.update({
            "status": "provider_error",
            "error": f"{type(exc).__name__}: {exc}",
            "assistant_text": "Provider error. Check API key, quota, network, or proxy settings.",
        })

    turn_record["ended_at"] = now_iso()
    st.session_state.transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, st.session_state.transcript)

    with st.chat_message("assistant"):
        st.write(turn_record.get("assistant_text") or turn_record.get("error") or "")
        render_trace(turn_record)
        st.caption(f"Transcript: {st.session_state.transcript_path}")


if __name__ == "__main__":
    main()