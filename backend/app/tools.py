"""The tools the agent can use.

Each tool is a plain Python function with type hints and a docstring. The same
functions are used in two places:

- agent.py turns them into Gemini function declarations (see TOOL_SCHEMAS)
- mcp_server.py exposes them over the Model Context Protocol

Tools return dicts. Errors are returned as {"error": "..."} instead of raising,
so the model can read what went wrong and explain it to the customer.
"""

import re

from .db import connect
from .faq import FAQ

ORDER_ID_RE = re.compile(r"^AC\d{4}$")


def _clean_order_id(order_id: str) -> str:
    return order_id.strip().upper().lstrip("#")


def _clean_email(email: str) -> str:
    return email.strip().lower()


def get_order_status(order_id: str, email: str) -> dict:
    """Look up an order's status, items, delivery estimate and tracking number.

    The email must match the one used for the order.
    """
    order_id, email = _clean_order_id(order_id), _clean_email(email)
    if not ORDER_ID_RE.match(order_id):
        return {"error": "Order IDs look like AC1042."}

    with connect() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

    # same message whether the order doesn't exist or belongs to someone else,
    # so the tool can't be used to discover other people's orders
    if row is None or row["email"] != email:
        return {"error": f"No order {order_id} found for {email}."}

    return {
        "order_id": row["id"],
        "items": row["items"],
        "total_rupees": row["total"],
        "status": row["status"],
        "ordered_on": row["ordered_on"],
        "estimated_delivery": row["eta"],
        "courier": row["courier"],
        "tracking_number": row["tracking_no"],
    }


def list_orders(email: str) -> dict:
    """List all orders placed with an email address, newest first."""
    email = _clean_email(email)
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, items, status, ordered_on FROM orders WHERE email = ? ORDER BY ordered_on DESC",
            (email,),
        ).fetchall()
    if not rows:
        return {"error": f"No orders found for {email}."}
    return {"orders": [dict(r) for r in rows]}


def cancel_order(order_id: str, email: str) -> dict:
    """Cancel an order that has not shipped yet. Only call this after the customer has confirmed."""
    order_id, email = _clean_order_id(order_id), _clean_email(email)
    with connect() as conn:
        row = conn.execute("SELECT email, status FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None or row["email"] != email:
            return {"error": f"No order {order_id} found for {email}."}
        if row["status"] == "cancelled":
            return {"error": f"Order {order_id} is already cancelled."}
        if row["status"] != "processing":
            return {"error": f"Order {order_id} has already {row['status']} and can't be cancelled. "
                             "The customer can return it after delivery."}
        conn.execute("UPDATE orders SET status = 'cancelled', eta = NULL WHERE id = ?", (order_id,))
    return {"order_id": order_id, "status": "cancelled", "refund": "Full refund in 5-7 business days."}


def search_faq(query: str) -> dict:
    """Search the store's help articles (returns, refunds, shipping, warranty, payments)."""
    words = set(re.findall(r"[a-z]+", query.lower())) - {"the", "a", "is", "my", "how", "what", "do", "i", "can"}
    scored = []
    for item in FAQ:
        text = (item["question"] + " " + item["answer"]).lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored:
        return {"results": [], "note": "Nothing in the help articles matches. Consider creating a ticket."}
    return {"results": [item for _, item in scored[:3]]}


def create_ticket(email: str, subject: str, description: str, order_id: str = "") -> dict:
    """Open a support ticket for a human agent. Use for damaged items, payment problems,
    or anything the other tools can't solve."""
    email = _clean_email(email)
    if "@" not in email:
        return {"error": "A valid email is needed to create a ticket."}
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (email, order_id, subject, description) VALUES (?, ?, ?, ?)",
            (email, _clean_order_id(order_id) or None, subject.strip(), description.strip()),
        )
        ticket_id = cur.lastrowid
    return {"ticket_id": f"T-{ticket_id:04d}", "status": "open", "response_time": "within 24 hours"}


TOOLS = {
    fn.__name__: fn
    for fn in (get_order_status, list_orders, cancel_order, search_faq, create_ticket)
}

# JSON schemas for Gemini function calling. Kept next to the functions so it's
# obvious when one changes and the other doesn't.
_EMAIL = {"type": "string", "description": "Customer's email address"}
_ORDER_ID = {"type": "string", "description": "Order ID, e.g. AC1042"}

TOOL_SCHEMAS = {
    "get_order_status": {
        "type": "object",
        "properties": {"order_id": _ORDER_ID, "email": _EMAIL},
        "required": ["order_id", "email"],
    },
    "list_orders": {
        "type": "object",
        "properties": {"email": _EMAIL},
        "required": ["email"],
    },
    "cancel_order": {
        "type": "object",
        "properties": {"order_id": _ORDER_ID, "email": _EMAIL},
        "required": ["order_id", "email"],
    },
    "search_faq": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What the customer is asking about"}},
        "required": ["query"],
    },
    "create_ticket": {
        "type": "object",
        "properties": {
            "email": _EMAIL,
            "subject": {"type": "string", "description": "One-line summary"},
            "description": {"type": "string", "description": "What happened, in a few sentences"},
            "order_id": {**_ORDER_ID, "description": "Related order ID, if any"},
        },
        "required": ["email", "subject", "description"],
    },
}


def run_tool(name: str, args: dict) -> dict:
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(**args)
    except TypeError as e:
        # the model passed arguments the function doesn't accept
        return {"error": f"Bad arguments for {name}: {e}"}
