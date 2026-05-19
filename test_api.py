"""
=============================================================
  WhatsApp Message Queue API - Test Suite
  Author  : Riya Chaleria
  Project : WhatsApp Message Queue API (In-Memory)
  Run     : python test_api.py
  Requires: pip install requests
            Flask server running on http://127.0.0.1:5000
=============================================================
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000/api/messages"

# ─────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────

passed = 0
failed = 0

def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def log(label, res, expect_status=None):
    global passed, failed

    status  = res.status_code
    body    = res.json()
    ok      = "PASS" if (expect_status is None or status == expect_status) else "❌ FAIL"

    if ok == "PASS":
        passed += 1
    else:
        failed += 1

    print(f"\n  {ok}  |  {label}")
    print(f"         Status   : {status}")
    print(f"         Response : {json.dumps(body, indent=10)}")

def summary():
    print(f"\n{'═' * 60}")
    print(f"  TEST SUMMARY")
    print(f"{'═' * 60}")
    print(f"  Total  : {passed + failed}")
    print(f"  Passed : {passed} ")
    print(f"  Failed : {failed} ")
    print(f"{'═' * 60}\n")

# ─────────────────────────────────────────────────────────────
# SETUP — check server + reset memory
# ─────────────────────────────────────────────────────────────

def check_server():
    print("\n  Checking if Flask server is running...")
    try:
        requests.get(BASE_URL, timeout=3)
        print("  Server is UP ")
    except requests.exceptions.ConnectionError:
        print("\n  ERROR: Flask server is not running!")
        print("  Please run:  python server.py")
        print("  Then re-run: python test_api.py\n")
        sys.exit(1)

def reset_server():
    """Clears all in-memory messages before tests begin."""
    requests.delete(f"{BASE_URL}/reset")
    print("  Memory cleared — fresh start ")

# ─────────────────────────────────────────────────────────────
# HELPER — silently post a message, return its id
# ─────────────────────────────────────────────────────────────

def post_message(phone, sender_name, message):
    res = requests.post(BASE_URL, json={
        "phone": phone,
        "sender_name": sender_name,
        "message": message
    })
    return res.json()['data']['id']

# ─────────────────────────────────────────────────────────────
# 1. POST /api/messages
# ─────────────────────────────────────────────────────────────

def test_post_messages():
    section("1. POST /api/messages — Receive Message")

    # Success
    res = requests.post(BASE_URL, json={
        "phone": "9876543210",
        "sender_name": "Arjun Sharma",
        "message": "Hello, I need help with my order."
    })
    log("Valid message → should return 201", res, 201)

    # Missing fields
    res = requests.post(BASE_URL, json={
        "phone": "9876543210"
    })
    log("Missing sender_name and message → should return 400", res, 400)

    # Invalid phone — letters
    res = requests.post(BASE_URL, json={
        "phone": "ABCD123456",
        "sender_name": "Priya",
        "message": "Test message"
    })
    log("Phone with letters → should return 400", res, 400)

    # Invalid phone — wrong starting digit
    res = requests.post(BASE_URL, json={
        "phone": "1234567890",
        "sender_name": "Priya",
        "message": "Test message"
    })
    log("Phone not starting with 6/7/8/9 → should return 400", res, 400)

    # Invalid phone — less than 10 digits
    res = requests.post(BASE_URL, json={
        "phone": "98765",
        "sender_name": "Rahul",
        "message": "Short phone"
    })
    log("Phone less than 10 digits → should return 400", res, 400)

    # Empty message body
    res = requests.post(BASE_URL, json={
        "phone": "9876543210",
        "sender_name": "Sneha",
        "message": "   "
    })
    log("Blank message (spaces only) → should return 400", res, 400)

    # Message too long
    res = requests.post(BASE_URL, json={
        "phone": "9876543210",
        "sender_name": "Sneha",
        "message": "A" * 1001
    })
    log("Message exceeds 1000 chars → should return 400", res, 400)

# ─────────────────────────────────────────────────────────────
# 2. GET /api/messages
# ─────────────────────────────────────────────────────────────

def test_get_messages():
    section("2. GET /api/messages — Retrieve All Messages")

    # Get all
    res = requests.get(BASE_URL)
    log("Get all messages → should return 200", res, 200)

    # Filter by status=pending
    res = requests.get(BASE_URL, params={"status": "pending"})
    log("Filter by status=pending → should return 200", res, 200)

    # Filter by phone
    res = requests.get(BASE_URL, params={"phone": "9876543210"})
    log("Filter by phone=9876543210 → should return 200", res, 200)

    # Filter by non-existent phone
    res = requests.get(BASE_URL, params={"phone": "6000000000"})
    log("Filter by unknown phone → should return empty list", res, 200)

# ─────────────────────────────────────────────────────────────
# 3. GET /api/messages/search
# ─────────────────────────────────────────────────────────────

def test_search_messages():
    section("3. GET /api/messages/search — Search by Keyword")

    # Keyword that exists
    res = requests.get(f"{BASE_URL}/search", params={"query": "order"})
    log("Search 'order' → should find match", res, 200)

    # Keyword that does not exist
    res = requests.get(f"{BASE_URL}/search", params={"query": "xyzabc123"})
    log("Search 'xyzabc123' → should return empty list", res, 200)

    # No query param — returns all
    res = requests.get(f"{BASE_URL}/search")
    log("Search with no query → should return all messages", res, 200)

# ─────────────────────────────────────────────────────────────
# 4. GET /api/messages/<id>
# ─────────────────────────────────────────────────────────────

def test_get_by_id(ids):
    section("4. GET /api/messages/<id> — Get Message by ID")

    # Valid ID
    res = requests.get(f"{BASE_URL}/{ids[0]}")
    log(f"Get message ID {ids[0]} → should return 200", res, 200)

    # Non-existent ID
    res = requests.get(f"{BASE_URL}/9999")
    log("Get message ID 9999 (not found) → should return 404", res, 404)

    # Non-numeric ID
    res = requests.get(f"{BASE_URL}/abc")
    log("Get message ID 'abc' (invalid) → should return 400", res, 400)

# ─────────────────────────────────────────────────────────────
# 5. PATCH /api/messages/<id>/process
# ─────────────────────────────────────────────────────────────

def test_process_message(ids):
    section("5. PATCH /api/messages/<id>/process — Mark as Processed")

    # Process a pending message
    res = requests.patch(f"{BASE_URL}/{ids[1]}/process")
    log(f"Process pending message ID {ids[1]} → should return 200", res, 200)

    # Process already processed
    res = requests.patch(f"{BASE_URL}/{ids[1]}/process")
    log(f"Process already-processed ID {ids[1]} → should return 400", res, 400)

    # Process a failed message (ids[2] will be failed first)
    requests.patch(f"{BASE_URL}/{ids[2]}/fail")
    res = requests.patch(f"{BASE_URL}/{ids[2]}/process")
    log(f"Process a failed message ID {ids[2]} → should return 400", res, 400)

    # Non-existent ID
    res = requests.patch(f"{BASE_URL}/9999/process")
    log("Process non-existent ID 9999 → should return 404", res, 404)

# ─────────────────────────────────────────────────────────────
# 6. PATCH /api/messages/<id>/fail
# ─────────────────────────────────────────────────────────────

def test_fail_message(ids):
    section("6. PATCH /api/messages/<id>/fail — Mark as Failed")

    # Fail a pending message
    res = requests.patch(f"{BASE_URL}/{ids[3]}/fail")
    log(f"Fail pending message ID {ids[3]} → should return 200", res, 200)

    # Fail already failed
    res = requests.patch(f"{BASE_URL}/{ids[3]}/fail")
    log(f"Fail already-failed ID {ids[3]} → should return 400", res, 400)

    # Fail a processed message (ids[1] was processed above)
    res = requests.patch(f"{BASE_URL}/{ids[1]}/fail")
    log(f"Fail a processed message ID {ids[1]} → should return 400", res, 400)

    # Non-existent ID
    res = requests.patch(f"{BASE_URL}/9999/fail")
    log("Fail non-existent ID 9999 → should return 404", res, 404)

# ─────────────────────────────────────────────────────────────
# 7. PATCH /api/messages/bulk-process
# ─────────────────────────────────────────────────────────────

def test_bulk_process(ids):
    section("7. PATCH /api/messages/bulk-process — Bulk Process")

    # Bulk process specific IDs (ids[4] and ids[5] are still pending)
    res = requests.patch(f"{BASE_URL}/bulk-process", json={"message_ids": [ids[4], ids[5]]})
    log(f"Bulk process IDs {ids[4]}, {ids[5]} → should return 200", res, 200)

    # Bulk process already processed
    res = requests.patch(f"{BASE_URL}/bulk-process", json={"message_ids": [ids[4], ids[5]]})
    log("Bulk process already-processed IDs → should show already_processed", res, 200)

    # Bulk process with non-existent IDs
    res = requests.patch(f"{BASE_URL}/bulk-process", json={"message_ids": [9998, 9999]})
    log("Bulk process non-existent IDs → should show not_found", res, 200)

    # Bulk process all pending (no body)
    res = requests.patch(f"{BASE_URL}/bulk-process")
    log("Bulk process all pending (no body) → should return 200", res, 200)

# ─────────────────────────────────────────────────────────────
# 8. PATCH /api/messages/bulk-fail
# ─────────────────────────────────────────────────────────────

def test_bulk_fail(ids):
    section("8. PATCH /api/messages/bulk-fail — Bulk Fail")

    # Bulk fail specific pending IDs (ids[6] and ids[7] still pending)
    res = requests.patch(f"{BASE_URL}/bulk-fail", json={"message_ids": [ids[6], ids[7]]})
    log(f"Bulk fail IDs {ids[6]}, {ids[7]} → should return 200", res, 200)

    # Bulk fail already failed
    res = requests.patch(f"{BASE_URL}/bulk-fail", json={"message_ids": [ids[6], ids[7]]})
    log("Bulk fail already-failed IDs → should show already_failed", res, 200)

    # Bulk fail with mix (one processed, one non-existent)
    res = requests.patch(f"{BASE_URL}/bulk-fail", json={"message_ids": [ids[1], 9999]})
    log("Bulk fail processed + non-existent → should show already_processed + not_found", res, 200)

    # Bulk fail all pending (no body)
    res = requests.patch(f"{BASE_URL}/bulk-fail")
    log("Bulk fail all pending (no body) → should return 200", res, 200)

# ─────────────────────────────────────────────────────────────
# 9. GET /api/messages/stats
# ─────────────────────────────────────────────────────────────

def test_stats():
    section("9. GET /api/messages/stats — Message Statistics")

    res = requests.get(f"{BASE_URL}/stats")
    log("Get stats → should return total, pending, processed, failed, unique_senders, busiest_hour", res, 200)

    data = res.json()
    print(f"\n   Stats Breakdown:")
    print(f"     Total Messages  : {data.get('total_messages')}")
    print(f"     Pending         : {data.get('pending')}")
    print(f"     Processed       : {data.get('processed')}")
    print(f"     Failed          : {data.get('failed')}")
    print(f"     Unique Senders  : {data.get('unique_senders')}")
    print(f"     Busiest Hour    : {data.get('busiest_hour')}")

# ─────────────────────────────────────────────────────────────
# 10. DELETE /api/messages/delete/<id>
# ─────────────────────────────────────────────────────────────

def test_delete(ids):
    section("10. DELETE /api/messages/delete/<id> — Delete Message")

    # Valid delete
    res = requests.delete(f"{BASE_URL}/delete/{ids[0]}")
    log(f"Delete message ID {ids[0]} → should return 200", res, 200)

    # Delete same ID again
    res = requests.delete(f"{BASE_URL}/delete/{ids[0]}")
    log(f"Delete already-deleted ID {ids[0]} → should return 404", res, 404)

    # Confirm it's gone via GET
    res = requests.get(f"{BASE_URL}/{ids[0]}")
    log(f"GET deleted message ID {ids[0]} → should return 404", res, 404)

    # Non-numeric ID
    res = requests.delete(f"{BASE_URL}/delete/abc")
    log("Delete with non-numeric ID 'abc' → should return 400", res, 400)

    # Non-existent ID
    res = requests.delete(f"{BASE_URL}/delete/9999")
    log("Delete non-existent ID 9999 → should return 404", res, 404)

# ─────────────────────────────────────────────────────────────
# MAIN — run all tests
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  WhatsApp Message Queue API — Full Test Suite")
    print("═" * 60)

    check_server()
    reset_server()

    # Seed 8 fresh messages for testing
    print("\n  Seeding test messages...")
    ids = [
        post_message("9876543210", "Arjun Sharma",  "Hello, I need help with my order."),
        post_message("8765432109", "Priya Mehta",   "Meeting confirmed for 3pm tomorrow."),
        post_message("7654321098", "Rahul Verma",   "Please send the invoice asap."),
        post_message("9988776655", "Sneha Gupta",   "My delivery is delayed, please check."),
        post_message("6543210987", "Karan Malhotra","Can I reschedule my appointment?"),
        post_message("9123456780", "Divya Rao",     "Thank you for the quick response!"),
        post_message("8012345679", "Amit Joshi",    "Is the offer still valid today?"),
        post_message("9876543210", "Arjun Sharma",  "Follow up on my previous message."),  # same phone as ids[0]
    ]
    print(f"  Created message IDs: {ids}")

    # Run all test sections
    test_post_messages()
    test_get_messages()
    test_search_messages()
    test_get_by_id(ids)
    test_process_message(ids)
    test_fail_message(ids)
    test_bulk_process(ids)
    test_bulk_fail(ids)
    test_stats()
    test_delete(ids)

    summary()
