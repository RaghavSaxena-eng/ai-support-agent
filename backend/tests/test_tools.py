from app.tools import TOOL_SCHEMAS, TOOLS, cancel_order, create_ticket, get_order_status, list_orders, run_tool, search_faq


def test_every_tool_has_a_schema():
    assert set(TOOLS) == set(TOOL_SCHEMAS)


def test_order_status_needs_matching_email():
    ok = get_order_status("AC1042", "priya@example.com")
    assert ok["status"] == "shipped"
    assert ok["tracking_number"] == "DL88213490"

    wrong_email = get_order_status("AC1042", "someone@example.com")
    missing = get_order_status("AC9999", "priya@example.com")
    # both cases return the same kind of message, so order IDs can't be probed
    assert "error" in wrong_email and "error" in missing


def test_order_id_is_normalized():
    assert get_order_status(" #ac1042 ", "PRIYA@example.com")["order_id"] == "AC1042"


def test_invalid_order_id_format():
    assert "error" in get_order_status("12345", "priya@example.com")


def test_list_orders_newest_first():
    orders = list_orders("priya@example.com")["orders"]
    assert [o["id"] for o in orders] == ["AC1042", "AC1043"]


def test_cancel_only_processing_orders():
    assert cancel_order("AC1057", "rahul@example.com")["status"] == "cancelled"
    assert get_order_status("AC1057", "rahul@example.com")["status"] == "cancelled"

    shipped = cancel_order("AC1042", "priya@example.com")
    assert "can't be cancelled" in shipped["error"]

    already = cancel_order("AC1061", "rahul@example.com")
    assert "already cancelled" in already["error"]


def test_search_faq_finds_refund_article():
    results = search_faq("how long does a refund take")["results"]
    assert results
    assert "refund" in results[0]["question"].lower()


def test_search_faq_no_match():
    assert search_faq("xyzzy")["results"] == []


def test_create_ticket_returns_id():
    t1 = create_ticket("neha@example.com", "Speaker damaged", "Arrived with a cracked grille", "AC1066")
    t2 = create_ticket("neha@example.com", "Another issue", "Something else")
    assert t1["ticket_id"] == "T-0001"
    assert t2["ticket_id"] == "T-0002"


def test_run_tool_handles_bad_input():
    assert "error" in run_tool("delete_everything", {})
    assert "error" in run_tool("list_orders", {"wrong_arg": 1})
