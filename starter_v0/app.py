from __future__ import annotations

import json
import os
import re
from datetime import datetime
from html import escape
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
PROVIDER_KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
SAMPLE_PROMPTS = [
    "Kiem tra xem https://openai.com/blog/gpt-5 co phu hop de trich dan khong.",
    "Tim tin AI chip trong thang nay.",
    "Lay cac tweet top ve OpenAI.",
    "Tom tat bai nay: https://www.reuters.com/technology/",
    "Dang ban tin AI market update hom nay len Telegram giup minh.",
]


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


def selected_model_name(provider_name: str, model_override: str | None) -> str | None:
    if model_override:
        return model_override
    provider = make_provider(provider_name)
    return getattr(provider, "default_model", None)


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
        "model": selected_model_name(provider_name, model),
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.session_state.history = []


def provider_ready(provider_name: str) -> bool:
    key_name = PROVIDER_KEYS.get(provider_name)
    return bool(key_name and os.getenv(key_name))


def render_shell() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width: 1180px; padding-top: 1.25rem;}
        [data-testid="stSidebar"] .stButton button {width: 100%; text-align: left;}
        .metric-strip {display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem; margin: .25rem 0 1rem;}
        .metric-box {border: 1px solid rgba(49, 51, 63, .18); border-radius: 8px; padding: .75rem .85rem; background: rgba(250, 250, 250, .7);}
        .metric-label {font-size: .78rem; color: rgba(49, 51, 63, .72); margin-bottom: .2rem;}
        .metric-value {font-size: .95rem; font-weight: 650; overflow-wrap: anywhere;}
        @media (max-width: 760px) {.metric-strip {grid-template-columns: 1fr 1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_strip(provider_name: str, model: str | None, artifact_version: str, tool_count: int) -> None:
    api_status = "ready" if provider_ready(provider_name) else "missing key"
    safe_provider = escape(provider_name)
    safe_model = escape(model or "default")
    safe_artifact = escape(artifact_version)
    st.markdown(
        f"""
        <div class="metric-strip">
          <div class="metric-box"><div class="metric-label">Provider</div><div class="metric-value">{safe_provider}</div></div>
          <div class="metric-box"><div class="metric-label">Model</div><div class="metric-value">{safe_model}</div></div>
          <div class="metric-box"><div class="metric-label">Artifact</div><div class="metric-value">{safe_artifact}</div></div>
          <div class="metric-box"><div class="metric-label">Tools</div><div class="metric-value">{tool_count} / API {api_status}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_catalog(declarations: list[dict[str, Any]]) -> None:
    with st.expander("Tool catalog", expanded=False):
        for item in declarations:
            st.markdown(f"**{item['name']}**")
            st.caption(item.get("description", ""))


def render_trace(turn: dict[str, Any]) -> None:
    events = turn.get("tool_events") or []
    label = f"Tool trace ({len(events)})" if events else "Tool trace"
    with st.expander(label, expanded=bool(events)):
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
                st.code(
                    compact_json({"status": status, "tool": call.get("name"), "args": call.get("args"), "result": result_payload}),
                    language="json",
                )


def render_history() -> None:
    for turn in st.session_state.transcript.get("turns", []):
        with st.chat_message("user"):
            st.write(turn.get("user", ""))
        with st.chat_message("assistant"):
            st.write(turn.get("assistant_text") or turn.get("error") or "")
            render_trace(turn)


def queue_prompt(prompt: str) -> None:
    st.session_state.pending_prompt = prompt


def handle_turn(user_text: str, provider_name: str, model: str | None, history_window: int, max_tool_rounds: int) -> dict[str, Any]:
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
            *trim_history(st.session_state.history, history_window),
            {"role": "user", "content": user_text},
        ]
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=model,
            max_tool_rounds=max_tool_rounds,
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
    return turn_record


def main() -> None:
    clear_dead_proxy_env()
    load_lab_env(ROOT)
    st.set_page_config(page_title="Research Agent Lab", layout="wide")
    render_shell()

    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    declarations = load_tool_declarations(tools_path)

    with st.sidebar:
        st.header("Run Settings")
        provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)
        version = st.text_input("Version", value="v3")
        model = st.text_input("Model override", value="") or None
        history_window = int(st.number_input("History window", min_value=0, max_value=20, value=5, step=1))
        max_tool_rounds = int(st.number_input("Max tool rounds", min_value=1, max_value=8, value=4, step=1))
        if st.button("New transcript", type="primary"):
            init_transcript(provider_name, model, version, max_tool_rounds, history_window)
            st.rerun()

        st.divider()
        render_tool_catalog(declarations)
        st.divider()
        st.caption("Sample prompts")
        for index, prompt in enumerate(SAMPLE_PROMPTS, start=1):
            st.button(prompt, key=f"sample_{index}", on_click=queue_prompt, args=(prompt,))

    artifact = build_artifact_version(version, system_prompt_path, tools_path)
    selected_model = selected_model_name(provider_name, model)

    config_key = (provider_name, model, version, max_tool_rounds, history_window, artifact.artifact_version)
    if "transcript" not in st.session_state or st.session_state.get("config_key") != config_key:
        init_transcript(provider_name, model, version, max_tool_rounds, history_window)
        st.session_state.config_key = config_key

    st.title("Research Agent Lab")
    render_metric_strip(provider_name, selected_model, artifact.artifact_version, len(declarations))

    if not provider_ready(provider_name):
        st.warning(f"Missing {PROVIDER_KEYS.get(provider_name)}. Add it to .env before sending a live request.")

    render_history()

    queued_prompt = st.session_state.pop("pending_prompt", None)
    typed_prompt = st.chat_input("Ask the research agent")
    user_text = queued_prompt or typed_prompt
    if not user_text:
        if st.session_state.transcript.get("turns"):
            with st.sidebar:
                st.download_button(
                    "Download transcript",
                    data=compact_json(st.session_state.transcript),
                    file_name=st.session_state.transcript_path.name,
                    mime="application/json",
                )
        return

    with st.chat_message("user"):
        st.write(user_text)

    with st.spinner("Running agent and tools..."):
        turn_record = handle_turn(user_text, provider_name, model, history_window, max_tool_rounds)

    with st.chat_message("assistant"):
        st.write(turn_record.get("assistant_text") or turn_record.get("error") or "")
        render_trace(turn_record)
        st.caption(f"Transcript: {st.session_state.transcript_path}")

    with st.sidebar:
        st.download_button(
            "Download transcript",
            data=compact_json(st.session_state.transcript),
            file_name=st.session_state.transcript_path.name,
            mime="application/json",
        )


if __name__ == "__main__":
    main()
