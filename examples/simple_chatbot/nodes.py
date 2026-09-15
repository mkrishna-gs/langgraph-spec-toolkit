"""Node and router functions for simple_chatbot.

Each function referenced from spec.yaml (a node's `config.function`, or an
edge's `condition`) must exist here under a matching name. Node functions
take the graph state dict and return a partial state update; router
functions take the state and return a label used to pick a path in the
edge's `paths` mapping. Regenerate graph.py with the `render_python` tool
after adding functions here or editing spec.yaml.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def greet(state: dict) -> dict:
    return {"messages": [SystemMessage(content="You are a terse, helpful assistant.")]}


def _latest_human_text(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def chatbot(state: dict) -> dict:
    messages = state["messages"]
    if isinstance(messages[-1], ToolMessage):
        return {"messages": [AIMessage(content=f"The weather tool says: {messages[-1].content}")]}

    text = _latest_human_text(messages)
    if "weather" in text.lower():
        reply = AIMessage(
            content="Let me check that.",
            tool_calls=[{"name": "get_weather", "args": {}, "id": "call_1"}],
        )
    else:
        reply = AIMessage(content=f"You said: {text}")
    return {"messages": [reply]}


def call_tools(state: dict) -> dict:
    last = state["messages"][-1]
    results = [
        ToolMessage(content="72F and sunny", tool_call_id=call["id"])
        for call in getattr(last, "tool_calls", [])
    ]
    return {"messages": results}


def route_after_chatbot(state: dict) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "continue"
    return "end"
