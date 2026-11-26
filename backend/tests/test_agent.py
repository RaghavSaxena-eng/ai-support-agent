"""Tests for the agent loop, with Gemini replaced by scripted responses."""

import asyncio

from fastapi.testclient import TestClient
from google.genai import types

from app.agent import MAX_STEPS, SupportAgent
from app.main import app, get_agent
from app.mcp_server import server


def text_response(text):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))]
    )


def tool_response(name, **args):
    part = types.Part(function_call=types.FunctionCall(name=name, args=args))
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=[part]))])


class ScriptedModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate_content(self, model, contents, config):
        self.requests.append(list(contents))
        return self.responses.pop(0)


def make_agent(responses):
    agent = SupportAgent(api_key="test", model="test-model")
    agent.client = type("FakeClient", (), {"models": ScriptedModels(responses)})()
    return agent


def test_plain_answer_without_tools():
    agent = make_agent([text_response("Hi! How can I help?")])
    result = agent.chat([], "hello")
    assert result.reply == "Hi! How can I help?"
    assert result.steps == []


def test_runs_tool_then_answers():
    agent = make_agent([
        tool_response("get_order_status", order_id="AC1042", email="priya@example.com"),
        text_response("Your earbuds have shipped and should arrive by 28 Nov."),
    ])
    result = agent.chat([], "Where is order AC1042? My email is priya@example.com")

    assert len(result.steps) == 1
    assert result.steps[0].tool == "get_order_status"
    assert result.steps[0].result["status"] == "shipped"
    assert "shipped" in result.reply

    # the second request must include the tool result for the model to read
    second_request = agent.client.models.requests[1]
    last = second_request[-1].parts[0]
    assert last.function_response.name == "get_order_status"
    assert last.function_response.response["tracking_number"] == "DL88213490"


def test_stops_after_max_steps():
    looping = [tool_response("search_faq", query="refund")] * MAX_STEPS
    agent = make_agent(looping)
    result = agent.chat([], "refund?")
    assert len(result.steps) == MAX_STEPS
    assert "couldn't finish" in result.reply


def test_history_is_sent_to_the_model():
    agent = make_agent([text_response("Sure.")])
    agent.chat([{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}], "next")
    sent = agent.client.models.requests[0]
    assert [c.role for c in sent] == ["user", "model", "user"]


def test_chat_endpoint_returns_steps():
    agent = make_agent([
        tool_response("list_orders", email="rahul@example.com"),
        text_response("You have two orders."),
    ])
    app.dependency_overrides[get_agent] = lambda: agent
    try:
        res = TestClient(app).post("/api/chat", json={"message": "my orders? rahul@example.com", "history": []})
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 200
    body = res.json()
    assert body["reply"] == "You have two orders."
    assert body["steps"][0]["tool"] == "list_orders"


def test_mcp_server_exposes_all_tools():
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert names == {"get_order_status", "list_orders", "cancel_order", "search_faq", "create_ticket"}
    order_tool = next(t for t in tools if t.name == "get_order_status")
    assert set(order_tool.input_schema["required"]) == {"order_id", "email"}
