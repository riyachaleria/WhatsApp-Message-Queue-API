"""
WhatsApp Message Queue API
--------------------------
A Flask-based REST API that simulates a WhatsApp webhook receiver.
Receives incoming messages, stores them in memory, and provides
endpoints to retrieve, filter, process, fail, and delete messages.

Note: All data is stored in-memory and resets on server restart.
"""

from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# IN-MEMORY STORE
# ─────────────────────────────────────────────────────────────

messages = []           # Stores all incoming messages as dicts
messages_id_counter = 1 # Auto-incrementing ID for each message

# ─────────────────────────────────────────────────────────────
# VALIDATORS
# ─────────────────────────────────────────────────────────────

def validate_requirefields(data, require_fields):
    """Check that all required fields are present and non-empty in the request body."""
    missing = [field for field in require_fields if not data.get(field)]
    if missing:
        return f"missing fields: {', '.join(missing)}"
    return None


def validate_phone(phone):
    """
    Validate Indian mobile number format:
    - Must be a 10-digit string
    - Must contain only digits
    - Must start with 6, 7, 8, or 9
    """
    if not isinstance(phone, str):
        phone = str(phone)

    if not phone.strip():
        return "Phone cannot be empty"

    if not phone.isdigit():
        return "Phone number must contain only digits"

    if len(phone) != 10:
        return "Phone number must be 10 digits"

    if phone[0] not in ['6', '7', '8', '9']:
        return "Phone number must start with 6, 7, 8, or 9"

    return None


def validate_name(name):
    """Validate that sender name is not blank."""
    if not name.strip():
        return "Sender name cannot be empty"
    return None


def validate_message(message):
    """
    Validate message content:
    - Cannot be blank or whitespace only
    - Cannot exceed 1000 characters
    """
    if not message.strip():
        return "Message cannot be empty"

    if len(message) > 1000:
        return "Message exceeds maximum length of 1000 characters"

    return None


def get_timestamp():
    """Return the current server time as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

# POST /api/messages
@app.route("/api/messages", methods=['POST'])
def receive_messages():
    """
    Receive a new incoming message (simulates a WhatsApp webhook).

    Request body (JSON):
        phone       : str  — Sender's 10-digit mobile number
        sender_name : str  — Sender's display name
        message     : str  — Message content (max 1000 chars)

    Returns:
        201 — Message received and stored successfully
        400 — Validation error (missing fields, invalid phone, etc.)
        500 — Internal server error
    """
    global messages_id_counter

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Check all required fields are present
        error = validate_requirefields(data, ['phone', 'message', 'sender_name'])
        if error:
            return jsonify({'error': error}), 400

        # Validate each field individually
        phone_error = validate_phone(data['phone'])
        if phone_error:
            return jsonify({'error': phone_error}), 400

        message_error = validate_message(data['message'])
        if message_error:
            return jsonify({'error': message_error}), 400

        name_error = validate_name(data['sender_name'])
        if name_error:
            return jsonify({'error': name_error}), 400

        # Build message object and store it
        message = {
            "id":          messages_id_counter,
            "phone":       data['phone'],
            "message":     data['message'].strip(),
            "timestamp":   get_timestamp(),
            "status":      "pending",
            "sender_name": data['sender_name'].strip()
        }
        messages.append(message)
        messages_id_counter += 1

        return jsonify({'message': 'Message received successfully', 'data': message}), 201

    except Exception as e:
        print(f"Error in receive_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# GET /api/messages
@app.route("/api/messages", methods=['GET'])
def get_messages():
    """
    Retrieve all messages, with optional filters.

    Query params (optional):
        status : str — Filter by status (pending / processed / failed)
        phone  : str — Filter by sender's phone number

    Returns:
        200 — List of matching messages (sorted latest first)
        404 — No messages in memory
        500 — Internal server error
    """
    try:
        status = request.args.get('status')
        phone  = request.args.get('phone')

        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        filtered_messages = messages.copy()

        if status:
            filtered_messages = [m for m in filtered_messages if m['status'] == status]

        if phone:
            filtered_messages = [m for m in filtered_messages if m['phone'] == phone]

        # Sort by timestamp, newest first
        filtered_messages = sorted(filtered_messages, key=lambda m: m['timestamp'], reverse=True)

        return jsonify({'messages': filtered_messages, 'count': len(filtered_messages)}), 200

    except Exception as e:
        print(f"Error in get_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# GET /api/messages/search
@app.route("/api/messages/search", methods=['GET'])
def get_keyword_messages():
    """
    Search messages by keyword in the message content (case-insensitive).

    Query params:
        query : str — Keyword to search for (returns all if omitted)

    Returns:
        200 — Matching messages sorted latest first
        404 — No messages in memory
        500 — Internal server error
    """
    try:
        search_query = request.args.get('query')

        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        filtered_messages = messages.copy()

        if search_query:
            filtered_messages = [
                m for m in filtered_messages
                if search_query.lower() in m['message'].lower()
            ]

        filtered_messages = sorted(filtered_messages, key=lambda m: m['timestamp'], reverse=True)

        return jsonify({'messages': filtered_messages, 'count': len(filtered_messages)}), 200

    except Exception as e:
        print(f"Error in get_keyword_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# PATCH /api/messages/bulk-process
@app.route("/api/messages/bulk-process", methods=['PATCH'])
def bulkProcess_messages():
    """
    Mark multiple messages as processed in one request.

    Two modes:
    1. Specific IDs — provide { "message_ids": [1, 2, 3] } in the request body
    2. All pending  — send no body to process every pending message at once

    Returns:
        200 — Summary of processed / skipped / not-found IDs
        400 — message_ids is not an array
        500 — Internal server error
    """
    try:
        data = request.get_json(silent=True, force=True)

        if data and 'message_ids' in data and data['message_ids']:
            message_ids = data['message_ids']

            if not isinstance(message_ids, list):
                return jsonify({'error': 'message_ids must be an array'}), 400

            processed        = []
            failed_status    = []
            not_found        = []
            already_processed = []

            for id in message_ids:
                message = next((m for m in messages if m['id'] == id), None)

                if not message:
                    not_found.append(id)
                elif message['status'] == 'processed':
                    already_processed.append(id)
                elif message['status'] == 'failed':
                    failed_status.append(id)
                else:
                    message['status'] = 'processed'
                    processed.append(id)

            return jsonify({
                'message':          f'Processed {len(processed)} message(s)',
                'processed':         processed,
                'not_found':         not_found,
                'already_processed': already_processed,
                'failed_status':     failed_status
            }), 200

        else:
            # No body provided — process all pending messages
            processed = []
            for message in messages:
                if message['status'] == 'pending':
                    message['status'] = 'processed'
                    processed.append(message['id'])

            if not processed:
                return jsonify({
                    'message':        'All pending messages are already processed',
                    'processed_count': len(processed),
                    'processed_ids':   processed
                }), 200

            return jsonify({
                'message':        'Processed all pending messages',
                'processed_count': len(processed),
                'processed_ids':   processed
            }), 200

    except Exception as e:
        print(f"Error in bulkProcess_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# PATCH /api/messages/bulk-fail
@app.route("/api/messages/bulk-fail", methods=['PATCH'])
def bulkFail_messages():
    """
    Mark multiple messages as failed in one request.

    Two modes:
    1. Specific IDs — provide { "message_ids": [1, 2, 3] } in the request body
    2. All pending  — send no body to fail every pending message at once

    Returns:
        200 — Summary of failed / skipped / not-found IDs
        400 — message_ids is not an array
        500 — Internal server error
    """
    try:
        data = request.get_json(silent=True, force=True)

        if data and 'message_ids' in data and data['message_ids']:
            message_ids = data['message_ids']

            if not isinstance(message_ids, list):
                return jsonify({'error': 'message_ids must be an array'}), 400

            failed            = []
            already_processed = []
            not_found         = []
            already_failed    = []

            for id in message_ids:
                message = next((m for m in messages if m['id'] == id), None)

                if not message:
                    not_found.append(id)
                elif message['status'] == 'failed':
                    already_failed.append(id)
                elif message['status'] == 'processed':
                    already_processed.append(id)
                else:
                    message['status'] = 'failed'
                    failed.append(id)

            return jsonify({
                'message':          f'Failed {len(failed)} message(s)',
                'failed':            failed,
                'not_found':         not_found,
                'already_failed':    already_failed,
                'already_processed': already_processed
            }), 200

        else:
            # No body provided — fail all pending messages
            failed = []
            for message in messages:
                if message['status'] == 'pending':
                    message['status'] = 'failed'
                    failed.append(message['id'])

            if not failed:
                return jsonify({
                    'message':     'All pending messages are already failed',
                    'failed_count': len(failed),
                    'failed_ids':   failed
                }), 200

            return jsonify({
                'message':     'Failed all pending messages',
                'failed_count': len(failed),
                'failed_ids':   failed
            }), 200

    except Exception as e:
        print(f"Error in bulkFail_messages: {e}")
        return jsonify({"error": "Internal server error"}), 500


# DELETE /api/messages/reset  (testing only)
@app.route("/api/messages/reset", methods=['DELETE'])
def reset_messages():
    """
    Clear all messages from memory and reset the ID counter.
    Intended for testing purposes only — not for production use.

    Returns:
        200 — Memory cleared successfully
    """
    global messages, messages_id_counter
    messages = []
    messages_id_counter = 1
    return jsonify({'message': 'All messages cleared'}), 200


# GET /api/messages/stats
@app.route("/api/messages/stats", methods=['GET'])
def get_stats():
    """
    Return a summary of all messages in memory.

    Response includes:
        total_messages : int — Total number of messages
        pending        : int — Count of pending messages
        processed      : int — Count of processed messages
        failed         : int — Count of failed messages
        unique_senders : int — Number of distinct phone numbers
        busiest_hour   : str — Hour with the most messages (e.g. "14:00")

    Returns:
        200 — Stats object
        404 — No messages in memory
        500 — Internal server error
    """
    try:
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        total_messages = len(messages)
        pending        = len([m for m in messages if m['status'] == 'pending'])
        processed      = len([m for m in messages if m['status'] == 'processed'])
        failed         = len([m for m in messages if m['status'] == 'failed'])
        unique_senders = len(set(m['phone'] for m in messages))

        # Count messages per hour to find the busiest hour
        hour_counts = {}
        for message in messages:
            hour = datetime.strptime(message['timestamp'], "%Y-%m-%d %H:%M:%S").hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        busiest_hour = f"{max(hour_counts, key=hour_counts.get):02d}:00"

        return jsonify({
            "total_messages": total_messages,
            "pending":         pending,
            "processed":       processed,
            "failed":          failed,
            "unique_senders":  unique_senders,
            "busiest_hour":    busiest_hour
        }), 200

    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


# DELETE /api/messages/delete/<id>
@app.route("/api/messages/delete/<id>", methods=['DELETE'])
def delete_message(id):
    """
    Permanently delete a message by its ID.

    URL param:
        id : int — ID of the message to delete

    Returns:
        200 — Message deleted successfully
        400 — ID is not a valid number
        404 — No messages in memory, or message not found
        500 — Internal server error
    """
    global messages

    try:
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        if not id.isdigit():
            return jsonify({'error': 'Message ID must be a number'}), 400

        found_message = next((m for m in messages if m['id'] == int(id)), None)

        if not found_message:
            return jsonify({'error': f'Message with ID {int(id)} not found'}), 404

        messages = [m for m in messages if m['id'] != int(id)]

        return jsonify({'message': 'Message deleted successfully'}), 200

    except Exception as e:
        print(f"Error in delete_message: {e}")
        return jsonify({"error": "Internal server error"}), 500


# GET /api/messages/<id>
@app.route("/api/messages/<id>", methods=['GET'])
def get_id_message(id):
    """
    Retrieve a single message by its ID.

    URL param:
        id : int — ID of the message to fetch

    Returns:
        200 — Message object
        400 — ID is not a valid number
        404 — No messages in memory, or message not found
        500 — Internal server error
    """
    try:
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        if not id.isdigit():
            return jsonify({'error': 'Message ID must be a number'}), 400

        found_message = next((m for m in messages if m['id'] == int(id)), None)

        if not found_message:
            return jsonify({'error': f'Message with ID {int(id)} not found'}), 404

        return jsonify({'data': found_message}), 200

    except Exception as e:
        print(f"Error in get_id_message: {e}")
        return jsonify({"error": "Internal server error"}), 500


# PATCH /api/messages/<id>/process
@app.route("/api/messages/<id>/process", methods=['PATCH'])
def process_id(id):
    """
    Mark a specific message as processed.

    Rules:
        - Only pending messages can be processed
        - Already processed or failed messages are rejected

    URL param:
        id : int — ID of the message to process

    Returns:
        200 — Message marked as processed
        400 — Already processed, is failed, or invalid ID
        404 — Message not found
        500 — Internal server error
    """
    try:
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        if not id.isdigit():
            return jsonify({'error': 'Message ID must be a number'}), 400

        found_message = next((m for m in messages if m['id'] == int(id)), None)

        if not found_message:
            return jsonify({'error': f'Message with ID {int(id)} not found'}), 404

        if found_message['status'] == "processed":
            return jsonify({'error': 'Message is already processed'}), 400

        if found_message['status'] == "failed":
            return jsonify({'error': 'Cannot process a failed message'}), 400

        found_message['status'] = "processed"

        return jsonify({'message': 'Message marked as processed', 'data': found_message}), 200

    except Exception as e:
        print(f"Error in process_id: {e}")
        return jsonify({"error": "Internal server error"}), 500


# PATCH /api/messages/<id>/fail
@app.route("/api/messages/<id>/fail", methods=['PATCH'])
def fail_id(id):
    """
    Mark a specific message as failed.

    Rules:
        - Only pending messages can be marked as failed
        - Already failed or processed messages are rejected

    URL param:
        id : int — ID of the message to fail

    Returns:
        200 — Message marked as failed
        400 — Already failed, is processed, or invalid ID
        404 — Message not found
        500 — Internal server error
    """
    try:
        if not messages:
            return jsonify({'error': 'No messages found'}), 404

        if not id.isdigit():
            return jsonify({'error': 'Message ID must be a number'}), 400

        found_message = next((m for m in messages if m['id'] == int(id)), None)

        if not found_message:
            return jsonify({'error': f'Message with ID {int(id)} not found'}), 404

        if found_message['status'] == "failed":
            return jsonify({'error': 'Message is already failed'}), 400

        if found_message['status'] == "processed":
            return jsonify({'error': 'Cannot fail a processed message'}), 400

        found_message['status'] = "failed"

        return jsonify({'message': 'Message marked as failed', 'data': found_message}), 200

    except Exception as e:
        print(f"Error in fail_id: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)