"""
WhatsApp Message Queue API
--------------------------
A Flask-based REST API that simulates a WhatsApp webhook receiver.
Receives incoming messages, stores them in memory, and provides
endpoints to retrieve, filter, process, fail, and delete messages.

Note: All data is stored in-memory and resets on server restart.

Endpoints:
    POST   /api/messages                  — Receive a new message
    GET    /api/messages                  — List all messages (filterable)
    GET    /api/messages/search           — Search messages by keyword
    GET    /api/messages/stats            — Message statistics and analytics
    GET    /api/messages/<id>             — Get a single message by ID
    PATCH  /api/messages/<id>/process     — Mark a message as processed
    PATCH  /api/messages/<id>/fail        — Mark a message as failed
    PATCH  /api/messages/bulk-process     — Bulk mark messages as processed
    PATCH  /api/messages/bulk-fail        — Bulk mark messages as failed
    DELETE /api/messages/delete/<id>      — Delete a message by ID
    DELETE /api/messages/reset            — Reset all data (testing only)

Note:
    All data is stored in-memory. State resets on every server restart.
    This is intentional for a lightweight queue simulation.

Author  : Riya
Version : 1.0.0
"""

from flask import Flask, jsonify, request, Response
from datetime import datetime

app = Flask(__name__)


# ─────────────────────────────────────────────────────────────
# IN-MEMORY DATA STORE
# ─────────────────────────────────────────────────────────────
#
# Using a plain list instead of a database keeps this API
# self-contained and easy to run without any external setup.
# Trade-off: all data is lost on server restart.

messages: list[dict] = []    # Holds all message objects
messages_id_counter: int = 1  # Monotonically increasing ID — never reused


# ─────────────────────────────────────────────────────────────
# VALIDATORS
# ─────────────────────────────────────────────────────────────

def validate_requirefields(data: dict, require_fields: list[str]) -> str | None:
    """
    Check that all required keys exist and are non-empty in the request body.

    Args:
        data           : Parsed JSON body from the request
        require_fields : List of field names that must be present

    Returns:
        An error string listing missing fields, or None if all are present.
    """
    missing = [field for field in require_fields if not data.get(field)]
    if missing:
        return f"missing fields: {', '.join(missing)}"
    return None


def validate_phone(phone: str) -> str | None:
    """
    Validate an Indian mobile number.

    Rules enforced:
        - Must contain digits only (no spaces, dashes, or country code)
        - Must be exactly 10 digits
        - Must start with 6, 7, 8, or 9 (valid Indian mobile prefixes)

    Args:
        phone : Raw phone value from the request body

    Returns:
        An error string describing the violation, or None if valid.
    """
    # Coerce to string in case the client sends a number instead of a string
    if not isinstance(phone, str):
        phone = str(phone)

    if not phone.strip():
        return "Phone cannot be empty"

    if not phone.isdigit():
        return "Phone number must contain only digits"

    if len(phone) != 10:
        return "Phone number must be 10 digits"

    # Indian mobile numbers always begin with 6, 7, 8, or 9
    if phone[0] not in ['6', '7', '8', '9']:
        return "Phone number must start with 6, 7, 8, or 9"

    return None


def validate_name(name: str) -> str | None:
    """
    Validate that the sender name is not blank or whitespace-only.

    Args:
        name : Sender name from the request body

    Returns:
        An error string if invalid, or None if valid.
    """
    if not name.strip():
        return "Sender name cannot be empty"
    return None


def validate_message(message: str) -> str | None:
    """
    Validate the message content.

    Rules enforced:
        - Cannot be blank or whitespace-only
        - Cannot exceed 1000 characters (matches WhatsApp's practical limit)

    Args:
        message : Message text from the request body

    Returns:
        An error string if invalid, or None if valid.
    """
    if not message.strip():
        return "Message cannot be empty"

    if len(message) > 1000:
        return "Message exceeds maximum length of 1000 characters"

    return None


def get_timestamp() -> str:
    """Return the current server time as a formatted string (YYYY-MM-DD HH:MM:SS)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────
# HELPER — shared ID lookup used across multiple routes
# ─────────────────────────────────────────────────────────────

def find_message_by_id(id_str: str) -> tuple:
    """
    Shared guard for endpoints that look up a message by URL param ID.

    Centralising this logic removes repeated if-blocks from every route
    and ensures consistent error responses across the API.

    Handles three failure cases:
        1. No messages exist in memory yet
        2. The ID param is not a valid integer string
        3. No message matches the given ID

    Args:
        id_str : Raw string ID taken from the URL (e.g. "5" or "abc")

    Returns:
        (message, None)          — on success
        (None, error_response)   — on any guard failure
    """
    if not messages:
        return None, (jsonify({'error': 'No messages found'}), 404)

    if not id_str.isdigit():
        return None, (jsonify({'error': 'Message ID must be a number'}), 400)

    message = next((message for message in messages if message['id'] == int(id_str)), None)
    if not message:
        return None, (jsonify({'error': f'Message with ID {int(id_str)} not found'}), 404)

    return message, None


# ─────────────────────────────────────────────────────────────
# ROUTES
# Note: specific paths (search, stats, bulk-*) must be registered
# before the <id> wildcard route, otherwise Flask matches them wrong.
# ─────────────────────────────────────────────────────────────


# ── POST /api/messages ────────────────────────────────────────
@app.route("/api/messages", methods=['POST'])
def receive_messages() -> Response:
    """
    Receive a new incoming message (simulates a WhatsApp webhook).

    Validates all fields before storing. The message is assigned a
    unique auto-incremented ID and given a default status of 'pending'.

    Request body (JSON):
        phone       : str — 10-digit Indian mobile number
        sender_name : str — Display name of the sender
        message     : str — Message content (max 1000 characters)

    Returns:
        201 — Message stored successfully, returns the created object
        400 — Validation failure (missing fields, bad phone format, etc.)
        500 — Unexpected server error
    """
    global messages_id_counter

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate presence of all required fields before individual checks
        error = validate_requirefields(data, ['phone', 'message', 'sender_name'])
        if error:
            return jsonify({'error': error}), 400

        phone_error = validate_phone(data['phone'])
        if phone_error:
            return jsonify({'error': phone_error}), 400

        message_error = validate_message(data['message'])
        if message_error:
            return jsonify({'error': message_error}), 400

        name_error = validate_name(data['sender_name'])
        if name_error:
            return jsonify({'error': name_error}), 400

        # Build the message object — strip whitespace from all user-supplied strings
        message = {
            "id":          messages_id_counter,
            "phone":       data['phone'],
            "message":     data['message'].strip(),
            "timestamp":   get_timestamp(),
            "status":      "pending",            # All messages start as pending
            "sender_name": data['sender_name'].strip()
        }

        messages.append(message)
        messages_id_counter += 1

        return jsonify({'message': 'Message received successfully', 'data': message}), 201

    except Exception as e:
        print(f"Error in receive_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── GET /api/messages ─────────────────────────────────────────
@app.route("/api/messages", methods=['GET'])
def get_messages() -> Response:
    """
    Retrieve all messages with optional query-based filtering.

    Filters are applied additively — combining status and phone
    narrows results further. Results are always sorted newest first.

    Query params (all optional):
        status : str — One of: pending | processed | failed
        phone  : str — Exact match on sender phone number

    Returns:
        200 — Filtered list of messages with a count
        404 — No messages exist in memory yet
        500 — Unexpected server error
    """
    try:
        status = request.args.get('status')
        phone  = request.args.get('phone')

        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        # Work on a copy so filters never mutate the original list
        filtered_messages = messages.copy()

        if status:
            filtered_messages = [message for message in filtered_messages if message['status'] == status]

        if phone:
            filtered_messages = [message for message in filtered_messages if message['phone'] == phone]

        # Sort descending by timestamp so the latest message appears first
        filtered_messages = sorted(filtered_messages, key=lambda message: message['timestamp'], reverse=True)

        return jsonify({'messages': filtered_messages, 'count': len(filtered_messages)}), 200

    except Exception as e:
        print(f"Error in get_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── GET /api/messages/search ──────────────────────────────────
@app.route("/api/messages/search", methods=['GET'])
def get_keyword_messages() -> Response:
    """
    Full-text search across message content (case-insensitive substring match).

    Omitting the query param returns all messages — useful for confirming
    the endpoint is reachable before narrowing down results.

    Query params:
        query : str — Keyword or phrase to search for (optional)

    Returns:
        200 — Matched messages sorted newest first
        404 — No messages exist in memory yet
        500 — Unexpected server error
    """
    try:
        search_query = request.args.get('query')

        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        filtered_messages = messages.copy()

        if search_query:
            # Case-insensitive substring match — keeps search flexible for partial words
            filtered_messages = [
                message for message in filtered_messages
                if search_query.lower() in message['message'].lower()
            ]

        filtered_messages = sorted(filtered_messages, key=lambda message: message['timestamp'], reverse=True)

        return jsonify({'messages': filtered_messages, 'count': len(filtered_messages)}), 200

    except Exception as e:
        print(f"Error in get_keyword_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── PATCH /api/messages/bulk-process ─────────────────────────
@app.route("/api/messages/bulk-process", methods=['PATCH'])
def bulkProcess_messages() -> Response:
    """
    Mark multiple messages as processed in a single request.

    Two modes:
        Selective : Send { "message_ids": [1, 2, 3] } to target specific messages.
        Blanket   : Send no body to process every pending message at once.

    For selective mode, the response details exactly what happened to
    each ID — processed, skipped, not found, or blocked by failed status.

    Returns:
        200 — Operation summary (partial successes also return 200)
        400 — message_ids is present but not an array
        500 — Unexpected server error
    """
    try:
        # silent=True returns None instead of raising 415 when no body is sent
        # force=True ignores Content-Type so plain PATCH with no body still works
        data = request.get_json(silent=True, force=True)

        if data and 'message_ids' in data and data['message_ids']:
            message_ids = data['message_ids']

            if not isinstance(message_ids, list):
                return jsonify({'error': 'message_ids must be an array'}), 400

            processed         = []
            failed_status     = []   # IDs skipped because they are already failed
            not_found         = []
            already_processed = []

            for id in message_ids:
                message = next((message for message in messages if message['id'] == id), None)

                if not message:
                    not_found.append(id)
                elif message['status'] == 'processed':
                    already_processed.append(id)
                elif message['status'] == 'failed':
                    # Failed is a terminal state — cannot be recovered here
                    failed_status.append(id)
                else:
                    message['status'] = 'processed'
                    processed.append(id)

            return jsonify({
                'message':           f'Processed {len(processed)} message(s)',
                'processed':          processed,
                'not_found':          not_found,
                'already_processed':  already_processed,
                'failed_status':      failed_status
            }), 200

        else:
            # Blanket mode — sweep all messages and process only pending ones
            processed = []
            for message in messages:
                if message['status'] == 'pending':
                    message['status'] = 'processed'
                    processed.append(message['id'])

            if not processed:
                return jsonify({
                    'message':         'All pending messages are already processed',
                    'processed_count':  len(processed),
                    'processed_ids':    processed
                }), 200

            return jsonify({
                'message':         'Processed all pending messages',
                'processed_count':  len(processed),
                'processed_ids':    processed
            }), 200

    except Exception as e:
        print(f"Error in bulkProcess_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── PATCH /api/messages/bulk-fail ────────────────────────────
@app.route("/api/messages/bulk-fail", methods=['PATCH'])
def bulkFail_messages() -> Response:
    """
    Mark multiple messages as failed in a single request.

    Two modes:
        Selective : Send { "message_ids": [1, 2, 3] } to target specific messages.
        Blanket   : Send no body to fail every pending message at once.

    Already-processed messages are protected — they cannot be moved to failed.

    Returns:
        200 — Operation summary (partial successes also return 200)
        400 — message_ids is present but not an array
        500 — Unexpected server error
    """
    try:
        data = request.get_json(silent=True, force=True)

        if data and 'message_ids' in data and data['message_ids']:
            message_ids = data['message_ids']

            if not isinstance(message_ids, list):
                return jsonify({'error': 'message_ids must be an array'}), 400

            failed            = []
            already_processed = []   # Cannot roll back a completed message
            not_found         = []
            already_failed    = []

            for id in message_ids:
                message = next((message for message in messages if message['id'] == id), None)

                if not message:
                    not_found.append(id)
                elif message['status'] == 'failed':
                    already_failed.append(id)
                elif message['status'] == 'processed':
                    # Protect processed messages from being accidentally failed
                    already_processed.append(id)
                else:
                    message['status'] = 'failed'
                    failed.append(id)

            return jsonify({
                'message':           f'Failed {len(failed)} message(s)',
                'failed':             failed,
                'not_found':          not_found,
                'already_failed':     already_failed,
                'already_processed':  already_processed
            }), 200

        else:
            # Blanket mode — fail all currently pending messages
            failed = []
            for message in messages:
                if message['status'] == 'pending':
                    message['status'] = 'failed'
                    failed.append(message['id'])

            if not failed:
                return jsonify({
                    'message':      'All pending messages are already failed',
                    'failed_count':  len(failed),
                    'failed_ids':    failed
                }), 200

            return jsonify({
                'message':      'Failed all pending messages',
                'failed_count':  len(failed),
                'failed_ids':    failed
            }), 200

    except Exception as e:
        print(f"Error in bulkFail_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── DELETE /api/messages/reset  (testing only) ───────────────
@app.route("/api/messages/reset", methods=['DELETE'])
def reset_messages() -> Response:
    """
    Wipe all messages from memory and reset the ID counter to 1.

    Intended for automated testing only — ensures each test run
    starts from a clean, predictable state without restarting the server.


    Returns:
        200 — Memory cleared and ID counter reset
    """
    global messages, messages_id_counter
    messages = []
    messages_id_counter = 1
    return jsonify({'message': 'All messages cleared'}), 200


# ── GET /api/messages/stats ───────────────────────────────────
@app.route("/api/messages/stats", methods=['GET'])
def get_stats() -> Response:
    """
    Return a real-time analytics snapshot of all messages in memory.

    Response fields:
        total_messages : int — Total messages stored
        pending        : int — Count with status 'pending'
        processed      : int — Count with status 'processed'
        failed         : int — Count with status 'failed'
        unique_senders : int — Distinct phone numbers seen
        busiest_hour   : str — Peak hour formatted as "HH:00" (e.g. "14:00")

    Returns:
        200 — Stats object
        404 — No messages exist in memory yet
        500 — Unexpected server error
    """
    try:
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        total_messages = len(messages)
        pending        = len([message for message in messages if message['status'] == 'pending'])
        processed      = len([message for message in messages if message['status'] == 'processed'])
        failed         = len([message for message in messages if message['status'] == 'failed'])

        # A set of phone numbers naturally deduplicates repeated senders
        unique_senders = len(set(message['phone'] for message in messages))

        # Tally message counts per hour to find the busiest time window
        hour_counts: dict[int, int] = {}
        for message in messages:
            hour = datetime.strptime(message['timestamp'], "%Y-%m-%d %H:%M:%S").hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        busiest_hour = f"{max(hour_counts, key=hour_counts.get):02d}:00"

        return jsonify({
            "total_messages":  total_messages,
            "pending":         pending,
            "processed":       processed,
            "failed":          failed,
            "unique_senders":  unique_senders,
            "busiest_hour":    busiest_hour
        }), 200

    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── DELETE /api/messages/delete/<id> ─────────────────────────
@app.route("/api/messages/delete/<id>", methods=['DELETE'])
def delete_message(id: str) -> Response:
    """
    Permanently remove a message from the queue by its ID.

    Args (URL):
        id : int — ID of the message to delete

    Returns:
        200 — Message deleted successfully
        400 — ID is not a valid integer
        404 — No messages in memory, or message not found
        500 — Unexpected server error
    """
    global messages

    try:
        message, error = find_message_by_id(id)
        if error:
            return error

        # Rebuild the list excluding the deleted message
        messages = [message for message in messages if message['id'] != int(id)]

        return jsonify({'message': 'Message deleted successfully'}), 200

    except Exception as e:
        print(f"Error in delete_message: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── GET /api/messages/<id> ────────────────────────────────────
@app.route("/api/messages/<id>", methods=['GET'])
def get_id_message(id: str) -> Response:
    """
    Fetch a single message by its unique ID.

    Args (URL):
        id : int — ID of the message to retrieve

    Returns:
        200 — The message object
        400 — ID is not a valid integer
        404 — No messages in memory, or message not found
        500 — Unexpected server error
    """
    try:
        message, error = find_message_by_id(id)
        if error:
            return error

        return jsonify({'data': message}), 200

    except Exception as e:
        print(f"Error in get_id_message: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── PATCH /api/messages/<id>/process ─────────────────────────
@app.route("/api/messages/<id>/process", methods=['PATCH'])
def process_id(id: str) -> Response:
    """
    Transition a message from 'pending' to 'processed'.

    Status transition rules:
        pending   → processed  allowed
        processed → processed  already done
        failed    → processed  terminal state, cannot recover

    Args (URL):
        id : int — ID of the message to process

    Returns:
        200 — Status updated to processed
        400 — Invalid transition or non-numeric ID
        404 — Message not found
        500 — Unexpected server error
    """
    try:
        message, error = find_message_by_id(id)
        if error:
            return error

        if message['status'] == "processed":
            return jsonify({'error': 'Message is already processed'}), 400

        if message['status'] == "failed":
            # Failed is a terminal state — a new message must be submitted if needed
            return jsonify({'error': 'Cannot process a failed message'}), 400

        message['status'] = "processed"

        return jsonify({'message': 'Message marked as processed', 'data': message}), 200

    except Exception as e:
        print(f"Error in process_id: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ── PATCH /api/messages/<id>/fail ────────────────────────────
@app.route("/api/messages/<id>/fail", methods=['PATCH'])
def fail_id(id: str) -> Response:
    """
    Transition a message from 'pending' to 'failed'.

    Status transition rules:
        pending   → failed  allowed
        failed    → failed  already done
        processed → failed  cannot undo a completed message

    Args (URL):
        id : int — ID of the message to fail

    Returns:
        200 — Status updated to failed
        400 — Invalid transition or non-numeric ID
        404 — Message not found
        500 — Unexpected server error
    """
    try:
        message, error = find_message_by_id(id)
        if error:
            return error

        if message['status'] == "failed":
            return jsonify({'error': 'Message is already failed'}), 400

        if message['status'] == "processed":
            # Protect completed messages from being accidentally rolled back
            return jsonify({'error': 'Cannot fail a processed message'}), 400

        message['status'] = "failed"

        return jsonify({'message': 'Message marked as failed', 'data': message}), 200

    except Exception as e:
        print(f"Error in fail_id: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)