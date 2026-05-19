from flask import Flask,jsonify,request
from datetime import datetime
app = Flask(__name__)

messages = []
messages_id_counter = 1

def validate_requirefields(data,require_fields):
    missing = [field for field in require_fields if not data.get(field)]

    if missing:
        return f"missing fields: {', '.join(missing)}"
    return None

def validate_phone(phone):
    if not isinstance(phone, str):
        phone = str(phone)

    if not phone.strip():
        return f"Phone cannot be empty"
    
    if not phone.isdigit():
        return f'Phone number must contain only digits'

    if not len(phone) == 10:
        return f"Phone number must be 10 digits"
    
    if phone[0] not in ['6', '7', '8', '9']:
        return f'Phone number must start with 6, 7, 8, or 9'
    
    return None

def validate_name(name):
    if not name.strip():
        return f'Sender name cannot be empty'
    return None
    
    # if not name.isalpha():    if only alphabatic name allowed
    #     return f'Sender name have to be in characters'
    
def validate_message(message):
    if not message.strip():
        return f'Message cannot be empty'

    if len(message) > 1000:
        return f'Message exceeds maximum length of 1000 characters'
    
    return None

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# post will receive {phone,message,sender_name}
@app.route("/api/messages",methods=['POST'])
def receive_messages():
    global messages_id_counter

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error' : 'Request body is required'}), 400
        
        error = validate_requirefields(data,['phone','message','sender_name'])

        if error:
            return jsonify({'error' : error}),400
        
        phone_error = validate_phone(data['phone'])
        if phone_error:
            return jsonify({'error' : phone_error}),400

        messege_error = validate_message(data['message'])
        if messege_error:
            return jsonify({'error' : messege_error}),400
        
        name_error = validate_name(data['sender_name'])
        if name_error:
            return jsonify({'error' : name_error}),400
        
        message = {
            "id" : messages_id_counter,
            "phone" : data['phone'],
            "message" : data['message'].strip(),
            "timestamp" : get_timestamp(),
            "status" : "pending",
            "sender_name" : data['sender_name'].strip()
        }
        messages.append(message)
        messages_id_counter += 1

        return jsonify({
            'message': 'Message received successfully',
            'data': message
            }),201
    
    except Exception as e:
        print(f"Error in receive_messages: {e}")
        return jsonify({"error" : "Internal server error"}), 500

@app.route("/api/messages",methods=['GET'])
def get_messages():
    try:
        status = request.args.get('status')
        phone = request.args.get('phone')

        if not messages:
            return jsonify({'error' : 'No messages found'}),404
        
        filtered_messages = messages.copy()
        if status:
            filtered_messages = [message for message in filtered_messages if message['status'] == status]
        
        if phone:
            filtered_messages = [message for message in filtered_messages if message['phone'] == phone]
            
        filtered_messages = sorted(
            filtered_messages,
            key = lambda message : message['timestamp'],
            reverse=True)
            
        return jsonify({
            'messages' : filtered_messages,
            'count' : len(filtered_messages),
        }),200
    
    except Exception as e:
        print(f"Error in get_messages: {e}")
        return jsonify({"error" : "Internal server error"}), 500

@app.route("/api/messages/search",methods=['GET'])
def get_keyword_messages():
    try:
        search_query = request.args.get('query') 

        if not messages:
            return jsonify({'error' : 'No messages found'}),404

        filtered_messages = messages.copy()
        if search_query:
            filtered_messages = [
                message for message in filtered_messages 
                if search_query.lower() in message['message'].lower()
            ]
        
        filtered_messages = sorted(
            filtered_messages,
            key = lambda message : message['timestamp'],
            reverse=True)
            
        return jsonify({
            'messages' : filtered_messages,
            'count' : len(filtered_messages),
        }),200
    
    except Exception as e:
        print(f"Error in get_keyword_messages - {e}")
        return jsonify({"error" : "Internal server error"}), 500

@app.route("/api/messages/bulk-process",methods=['PATCH'])
def bulkProcess_messages():
    try:
        data = request.get_json(silent=True,force=True)

        if data and 'message_ids' in data and data['message_ids']:
            message_ids = data['message_ids']

            if not isinstance(message_ids,list):
                return jsonify({'error' : 'message_ids must be an array'}),400

            processed = []
            failed_status = []
            not_found = []
            already_processed = []

            for id in message_ids:
                message = next((message for message in messages if message['id'] == id),None)

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
                'message' : f'Processed {len(processed)} message(s)',
                'processed' : processed,
                'not_found' : not_found,
                'already_processed' : already_processed,
                'failed_status' : failed_status
            }),200
            
        else:
            processed = []

            for message in messages:
                if message['status'] == 'pending':
                    message['status'] = 'processed'
                    processed.append(message['id'])
    
            if not processed:
                return jsonify({
                    'message' : 'all pending messages are already processed',
                    'processed_count' : len(processed),
                    'processed_ids' : processed
                }),200
            
            return jsonify({
                'message' : 'Processed all pending messages',
                'processed_count' : len(processed),
                'processed_ids' : processed
            }),200

    except Exception as e:
        print(f"Error in bulkProcess_messages - {e}")
        return jsonify({"error" : "Internal server error"}), 500
        
@app.route("/api/messages/bulk-fail",methods=['PATCH'])
def bulkFail_messages():
    try:
        data = request.get_json(silent=True,force=True)

        if data and 'message_ids' in data and data['message_ids']:
            message_ids = data['message_ids']

            if not isinstance(message_ids,list):
                return jsonify({'error' : 'message_ids must be an array'}),400

            failed = []
            already_processed = []
            not_found = []
            already_failed = []

            for id in message_ids:
                message = next((message for message in messages if message['id'] == id),None)

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
                'message' : f'Failed {len(failed)} message(s)',
                'failed' : failed,
                'not_found' : not_found,
                'already_failed' : already_failed,
                'already_processed' : already_processed
            }),200
        
        else:
            failed = []

            for message in messages:
                if message['status'] == 'pending':
                    message['status'] = 'failed'
                    failed.append(message['id'])

            if not failed:
                return jsonify({
                    'message' : 'all pending messages are already failed',
                    'failed_count' : len(failed),
                    'failed_ids' : failed
                }),200
            
            return jsonify({
                'message' : 'Failed all pending messages',
                'failed_count' : len(failed),
                'failed_ids' : failed
            }),200

    except Exception as e:
        print(f"Error in bulkFail_messages - {e}")
        return jsonify({"error" : "Internal server error"}), 500   

# (for testing only)
@app.route("/api/messages/reset", methods=['DELETE'])
def reset_messages():
    global messages, messages_id_counter
    messages = []
    messages_id_counter = 1
    return jsonify({'message': 'All messages cleared'}), 200

@app.route("/api/messages/stats",methods=['GET'])
def get_stats():
    try:
        if not messages:
            return jsonify({'error' : 'No messages found'}),404
    
        total_messages = len(messages)
        pending = len([message for message in messages if message['status'] == 'pending'])
        processed = len([message for message in messages if message['status'] == 'processed'])
        failed = len([message for message in messages if message['status'] == 'failed'])

        unique_senders = len(set(message['phone'] for message in messages))

        busiest_hour = 0
        hour_counts = {}

        for message in messages:
            timestamp = message['timestamp']

            hour = datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S").hour
            hour_counts[hour] = hour_counts.get(hour,0)+1  # get 0 if the hour not present in dict

        busiest = max(hour_counts,key= hour_counts.get)
        busiest_hour = f"{busiest:02d}:00"

        return jsonify({
            "total_messages" : total_messages,
            "pending" : pending,
            "processed" : processed,
            "failed" : failed,
            "unique_senders" : unique_senders,
            "busiest_hour" : busiest_hour
        }),200

    except Exception as e:
        print(f"Error in get_stats - {e}")
        return jsonify({"error" : "Internal server error"}), 500
         

@app.route("/api/messages/delete/<id>",methods=['DELETE'])
def delete_message(id):
    global messages
    try:
        if not messages:
            return jsonify({'error' : 'No messages found'}),404
    
        if not id.isdigit():
            return jsonify({'error' : 'Message ID must be a number'}),400
        
        found_message = next((message for message in messages if message['id'] == int(id)),None)

        if not found_message:
            return jsonify({'error' : f'Message with ID {int(id)} not found'}),404
        
        messages = [message for message in messages if message['id'] != int(id)]
        
        return jsonify({'message' : 'Message deleted successfully'}),200
    
    except Exception as e:
        print(f"Error in delete_message - {e}")
        return jsonify({"error" : "Internal server error"}), 500

@app.route("/api/messages/<id>",methods=['GET'])
def get_id_message(id):
    try: 
        if not messages:
            return jsonify({'error' : 'No messages found'}),404
    
        if not id.isdigit():
            return jsonify({'error' : 'Message ID must be a number'}),400
        
        found_message = next((message for message in messages if message['id'] == int(id)),None)

        if not found_message:
            return jsonify({'error' : f'Message with ID {int(id)} not found'}),404

        return jsonify({'data' : found_message}),200
    
    except Exception as e:
        print(f"Error in get_id_message - {e}")
        return jsonify({"error" : "Internal server error"}), 500

@app.route("/api/messages/<id>/process",methods=['PATCH'])
def process_id(id):
    try:
        if not messages:
            return jsonify({'error' : 'No messages found'}),404
    
        if not id.isdigit():
            return jsonify({'error' : 'Message ID must be a number'}),400
        
        found_message = next((message for message in messages if message['id'] == int(id)),None)

        if not found_message:
            return jsonify({'error' : f'Message with ID {int(id)} not found'}),404

        if found_message['status'] == "processed":
            return jsonify({'error' : 'Message is already processed'}),400
        elif found_message['status'] == "failed":
            return jsonify({'error' : 'Cannot process a failed message'}),400
        
        found_message['status'] = "processed"

        return jsonify({
            'message': 'Message marked as processed',
            'data' : found_message}),200

    except Exception as e:
        print(f"Error in process_id - {e}")
        return jsonify({"error" : "Internal server error"}), 500
    
@app.route("/api/messages/<id>/fail",methods=['PATCH'])
def fail_id(id):
    try:
        if not messages:
            return jsonify({'error' : 'No messages found'}),404
    
        if not id.isdigit():
            return jsonify({'error' : 'Message ID must be a number'}),400
        
        found_message = next((message for message in messages if message['id'] == int(id)),None)

        if not found_message:
            return jsonify({'error' : f'Message with ID {int(id)} not found'}),404

        if found_message['status'] == "failed":
            return jsonify({'error' : 'Message is already failed'}),400
        elif found_message['status'] == "processed":
            return jsonify({'error' : 'Cannot fail a processed message'}),400
        
        found_message['status'] = "failed"

        return jsonify({
            'message': 'Message marked as failed',
            'data' : found_message}),200

    except Exception as e:
        print(f"Error in fail_id - {e}")
        return jsonify({"error" : "Internal server error"}), 500
    
if __name__ == "__main__":
    app.run(debug=True)