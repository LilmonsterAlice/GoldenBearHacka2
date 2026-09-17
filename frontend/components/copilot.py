from typing import Any

import streamlit as st

from services.api_client import ChatAPIError, post_chat


PRESET_QUESTIONS = [
    "Why is idle interactive capacity recoverable?",
    "What could go wrong if we enforce an idle timeout?",
    "What evidence supports this recommendation?",
]


def _markdown_text(value: Any) -> str:
    """Prevent dollar amounts in API text from being parsed as LaTeX."""
    return str(value).replace("$", r"\$")


def _mock_idle_interactive_response(question: str) -> dict[str, Any]:
    """Return a deterministic mock response for the first vertical slice."""
    normalized = question.casefold()

    if "wrong" in normalized or "risk" in normalized:
        answer = (
            "A strict timeout could interrupt legitimate debugging, environment "
            "setup, or short periods of human inactivity. The safer policy is to "
            "warn first, allow an extension, and roll out the timeout gradually."
        )
        risk = "Productive interactive work may be terminated too early."
        recommendation = "Start with warnings and a reversible pilot policy."
    elif "evidence" in normalized:
        answer = (
            "The mock evidence represents interactive GPU sessions open for more "
            "than four hours while average GPU utilization remained below 5%. "
            "That pattern supports investigating an idle-session policy."
        )
        risk = "Low utilization alone does not prove that every session was wasteful."
        recommendation = "Review the affected jobs before setting the final timeout."
    else:
        answer = (
            "Idle interactive capacity may be recoverable because the allocation "
            "remains reserved while little GPU compute is used. A warning and idle "
            "timeout could release that capacity without changing the research code."
        )
        risk = "Some low-utilization sessions may still support legitimate research."
        recommendation = "Use a warning-first timeout with an extension option."

    return {
        "answer": answer,
        "evidence": [
            "Mock finding: interactive session open longer than 4 hours.",
            "Mock signal: average GPU utilization below 5%.",
        ],
        "risk": risk,
        "recommendation": recommendation,
        "confidence": 0.72,
        "caveats": [
            "This response uses mock evidence only.",
            "It must not be used as a submitted savings claim.",
        ],
    }


def _render_assistant_response(response: dict[str, Any]) -> None:
    st.markdown(_markdown_text(response["answer"]))
    confidence = response.get("confidence")
    if confidence is None:
        st.caption("Confidence: unavailable")
    else:
        st.caption(f"Confidence: {confidence:.0%}")

    with st.expander("Evidence, recommendation, and caveats"):
        st.markdown("**Evidence**")
        if response["evidence"]:
            for item in response["evidence"]:
                if isinstance(item, dict):
                    description = item.get("description")
                    if description:
                        st.markdown(f"- {_markdown_text(description)}")
                    else:
                        st.json(item)
                else:
                    st.markdown(f"- {_markdown_text(item)}")
        else:
            st.markdown("- No grounded evidence returned.")

        st.markdown(f"**Risk:** {_markdown_text(response['risk'])}")
        st.markdown(f"**Recommendation:** {_markdown_text(response['recommendation'])}")

        finding_ids = response.get("finding_ids", [])
        job_ids = response.get("job_ids", [])
        if finding_ids:
            st.markdown(f"**Finding IDs:** {', '.join(finding_ids)}")
        if job_ids:
            st.markdown(f"**Job IDs:** {', '.join(map(str, job_ids))}")

        st.markdown("**Caveats**")
        for caveat in response["caveats"]:
            st.markdown(f"- {_markdown_text(caveat)}")


def _initialize_history() -> None:
    if "copilot_messages" not in st.session_state:
        st.session_state.copilot_messages = [
            {
                "role": "assistant",
                "content": (
                    "Ask me about the Idle Interactive recommendation, its evidence, "
                    "or the cost of being wrong."
                ),
            }
        ]


def _open_copilot() -> None:
    st.session_state.copilot_is_open = True


def _close_copilot() -> None:
    st.session_state.copilot_is_open = False


def _render_copilot_window() -> None:
    """Render a non-modal Copilot window that does not block the dashboard."""
    _initialize_history()
    with st.container(key="copilot_window"):
        title_column, close_column = st.columns([0.88, 0.12])
        title_column.subheader("AI Copilot")
        close_column.button(
            "×",
            key="close_copilot",
            help="Close AI Copilot",
            on_click=_close_copilot,
        )
        st.caption("Idle Interactive prototype · Backend API · Local fallback available")

        with st.container(height=175, border=False, key="copilot_history"):
            for message in st.session_state.copilot_messages:
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant" and "response" in message:
                        _render_assistant_response(message["response"])
                    else:
                        st.markdown(message["content"])

        selected_question = None
        with st.container(border=True, key="copilot_composer"):
            st.markdown("**Suggested questions**")
            for index, question in enumerate(PRESET_QUESTIONS):
                if st.button(
                    question,
                    key=f"copilot_preset_{index}",
                    width="stretch",
                ):
                    selected_question = question

            typed_question = st.chat_input(
                "Ask about Idle Interactive...",
                key="copilot_chat_input",
            )
        question = selected_question or typed_question

        if not question:
            return

        st.session_state.copilot_messages.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.markdown(question)

        try:
            response = post_chat(
                question,
                opportunity_id="idle-interactive",
            )
        except ChatAPIError:
            response = _mock_idle_interactive_response(question)
            response["caveats"].insert(
                0,
                "Backend API unavailable; displaying the local UI fallback.",
            )
        st.session_state.copilot_messages.append(
            {
                "role": "assistant",
                "content": response["answer"],
                "response": response,
            }
        )
        st.rerun()


def render_copilot() -> None:
    """Render a floating Copilot launcher; history survives all app reruns."""
    _initialize_history()
    if "copilot_is_open" not in st.session_state:
        st.session_state.copilot_is_open = False
    st.markdown(
        """
        <style>
        .st-key-copilot_launcher {
            position: fixed;
            right: 1.75rem;
            bottom: 1.75rem;
            width: 4rem;
            z-index: 999;
        }
        .st-key-copilot_launcher button {
            width: 4rem;
            height: 4rem;
            min-height: 4rem;
            padding: 0;
            border-radius: 50%;
            font-size: 1.65rem;
            color: white;
            background: linear-gradient(135deg, #6d5dfc, #1f8fff);
            border: 1px solid rgba(255, 255, 255, 0.35);
            box-shadow: 0 10px 28px rgba(31, 82, 190, 0.35);
        }
        .st-key-copilot_launcher button:hover {
            color: white;
            border-color: white;
            transform: translateY(-2px);
        }
        .st-key-copilot_composer {
            position: sticky;
            bottom: 0;
            z-index: 2;
            padding: 0.75rem 0 0.25rem;
            background: var(--background-color);
        }
        .st-key-copilot_window {
            position: fixed;
            right: 1.25rem;
            bottom: 1.25rem;
            width: min(34rem, calc(100vw - 2.5rem));
            max-width: min(34rem, calc(100vw - 2.5rem));
            height: min(42rem, calc(100vh - 2.5rem));
            max-height: min(42rem, calc(100vh - 2.5rem));
            overflow: hidden;
            z-index: 998;
            padding: 1.25rem;
            border-radius: 1rem;
            color: inherit;
            background: #0e1117;
            opacity: 1;
            border: 3px solid #3b82f6;
            box-shadow:
                0 0 0 1px rgba(59, 130, 246, 0.25),
                0 18px 55px rgba(37, 99, 235, 0.3);
        }
        .st-key-copilot_window > div {
            background: transparent;
        }
        .st-key-copilot_window [data-testid="stChatInput"] {
            background: #262730;
        }
        .st-key-copilot_composer {
            padding: 0.8rem;
            border: 1px solid rgba(59, 130, 246, 0.65);
            border-radius: 0.75rem;
            background: #0e1117;
        }
        .st-key-copilot_composer button {
            height: auto;
            min-height: 2.75rem;
            padding-top: 0.55rem;
            padding-bottom: 0.55rem;
        }
        .st-key-copilot_composer button p {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            line-height: 1.25;
        }
        @media (prefers-color-scheme: light) {
            .st-key-copilot_window,
            .st-key-copilot_composer {
                background: #ffffff;
            }
            .st-key-copilot_window [data-testid="stChatInput"] {
                background: #f0f2f6;
            }
        }
        .st-key-close_copilot button {
            min-height: 2rem;
            height: 2rem;
            padding: 0;
            border: none;
            font-size: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.copilot_is_open:
        _render_copilot_window()
    else:
        with st.container(key="copilot_launcher"):
            st.button(
                "✦",
                key="open_copilot",
                help="Open AI Copilot",
                on_click=_open_copilot,
            )
