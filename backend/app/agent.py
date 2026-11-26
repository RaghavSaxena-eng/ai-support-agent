"""The agent loop.

1. Send the conversation + tool declarations to Gemini.
2. If Gemini asks for tool calls, run them and send the results back.
3. Repeat until Gemini answers in plain text (or we hit MAX_STEPS).

We run the loop ourselves instead of using the SDK's automatic function calling
so we can record every step and show it in the UI.
"""

import json
import logging
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from .tools import TOOL_SCHEMAS, TOOLS, run_tool

log = logging.getLogger("agent")

MAX_STEPS = 6

SYSTEM_PROMPT = """You are the customer support assistant for Acme Gadgets, an Indian online electronics store.

How to work:
- Use the tools to look things up. Never make up order details, policies, dates or ticket numbers.
- To look up or change an order you need both the order ID and the email used to place it. Ask for whatever is missing.
- Before cancelling an order, tell the customer what will happen and wait for them to clearly say yes.
- For policy questions (returns, refunds, shipping, warranty, payments) use search_faq and answer from the result.
- If a tool returns an error, explain it simply and suggest the next step.
- If you can't solve something (damaged item, payment charged twice, anything outside the tools), create a ticket and give the customer the ticket ID.

Style: friendly, short and clear. Prices in rupees (Rs). No more than a few sentences unless listing orders."""


@dataclass
class Step:
    tool: str
    args: dict
    result: dict


@dataclass
class AgentReply:
    reply: str
    steps: list[Step] = field(default_factory=list)


def _declarations() -> list[types.FunctionDeclaration]:
    return [
        types.FunctionDeclaration(
            name=name,
            description=(fn.__doc__ or "").strip(),
            parameters_json_schema=TOOL_SCHEMAS[name],
        )
        for name, fn in TOOLS.items()
    ]


def _history_to_contents(history: list[dict]) -> list[types.Content]:
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])]))
    return contents


class SupportAgent:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=_declarations())],
            temperature=0.3,
        )

    def chat(self, history: list[dict], message: str) -> AgentReply:
        contents = _history_to_contents(history)
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
        steps: list[Step] = []

        for _ in range(MAX_STEPS):
            response = self.client.models.generate_content(
                model=self.model, contents=contents, config=self.config,
            )
            calls = response.function_calls or []
            if not calls:
                return AgentReply(reply=(response.text or "").strip(), steps=steps)

            # keep the model's turn (including its function calls) in the conversation
            contents.append(response.candidates[0].content)

            result_parts = []
            for call in calls:
                args = dict(call.args or {})
                result = run_tool(call.name, args)
                log.info("tool %s(%s) -> %s", call.name, json.dumps(args), json.dumps(result)[:200])
                steps.append(Step(tool=call.name, args=args, result=result))
                result_parts.append(types.Part.from_function_response(name=call.name, response=result))
            contents.append(types.Content(role="user", parts=result_parts))

        return AgentReply(
            reply="Sorry, I couldn't finish that request. I've noted the details; please try again or ask me to open a ticket.",
            steps=steps,
        )
