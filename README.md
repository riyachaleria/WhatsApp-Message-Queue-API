# WhatsApp Message Queue API

A production-ready RESTful API for managing WhatsApp Business message workflows, built with Flask. Designed to handle webhook events, message processing, and analytics for customer communication platforms.

## 🎯 Overview

This API serves as the backend infrastructure for WhatsApp Business integrations, enabling businesses to receive, process, track, and analyze customer messages at scale. Built during my internship at Yashas AI, a company specializing in WhatsApp Business API automation and AI chatbots.

### Business Problem Solved

When businesses use WhatsApp Business API, they need a system to:
- Receive incoming messages via webhooks
- Track message status (pending/processed/failed)
- Filter and search through conversation history
- Monitor team performance and message volume
- Ensure no customer messages are lost

This API provides that complete solution.

## 🚀 Features

### Core Functionality
- **Message Reception**: Webhook-ready endpoint for WhatsApp Business API integration
- **Status Management**: Track message lifecycle (pending → processed/failed)
- **Smart Filtering**: Filter messages by status, phone number, or content
- **Bulk Operations**: Process or fail multiple messages efficiently
- **Real-time Analytics**: Statistics on message volume, unique senders, and peak hours

### Technical Highlights
- RESTful API design following industry standards
- Comprehensive input validation and error handling
- Proper HTTP status codes (200, 201, 400, 404, 500)
- Search functionality with case-insensitive matching
- Timestamp-based sorting (newest first)

## 🛠️ Tech Stack

- **Framework**: Flask 3.0+
- **Language**: Python 3.8+
- **Data Storage**: In-memory (SQLite integration planned)
- **Testing**: Manual testing with Postman/requests module

## 📋 API Endpoints

### Message Operations

#### Receive Message
```http
POST /api/messages
```

**Request Body:**
```json
{
  "phone": "9876543210",
  "message": "Hi, I need help with my order",
  "sender_name": "riya chaleria"
}
```

**Response (201 Created):**
```json
{
  "message": "Message received successfully",
  "data": {
    "id": 1,
    "phone": "9876543210",
    "message": "Hi, I need help with my order",
    "timestamp": "2024-05-16 14:30:00",
    "status": "pending",
    "sender_name": "riya chaleria"
  }
}
```

**Validation:**
- Phone: 10 digits, starts with 6/7/8/9 (Indian format)
- Message: Non-empty, max 1000 characters
- Sender name: Required, non-empty

---

#### Get All Messages (with Filters)
```http
GET /api/messages
GET /api/messages?status=pending
GET /api/messages?phone=9876543210
GET /api/messages?status=pending&phone=9876543210
```

**Response (200 OK):**
```json
{
  "messages": [
    {
      "id": 1,
      "phone": "9876543210",
      "message": "Hi, I need help",
      "timestamp": "2024-05-16 14:30:00",
      "status": "pending",
      "sender_name": "riya chaleria"
    }
  ],
  "count": 1
}
```

---

#### Search Messages by Keyword
```http
GET /api/messages/search?query=order
```

**Use Case:** Find all messages containing "pricing", "urgent", "order", etc.

---

#### Get Single Message
```http
GET /api/messages/1
```

---

### Status Management

#### Mark as Processed
```http
PATCH /api/messages/1/process
```

**Response (200 OK):**
```json
{
  "message": "Message marked as processed",
  "data": { /* message object */ }
}
```

---

#### Mark as Failed
```http
PATCH /api/messages/1/fail
```

---

#### Bulk Process Messages
```http
PATCH /api/messages/bulk-process
```

**Option 1 - Process specific messages:**
```json
{
  "message_ids": [1, 2, 3]
}
```

**Option 2 - Process ALL pending messages:**
```json
{}
```
*(Empty body or no body)*

**Response:**
```json
{
  "message": "Processed 3 message(s)",
  "processed": [1, 2, 3],
  "not_found": [],
  "already_processed": [],
  "failed_status": []
}
```

---

### Analytics

#### Get Statistics
```http
GET /api/messages/stats
```

**Response (200 OK):**
```json
{
  "total_messages": 45,
  "pending": 5,
  "processed": 38,
  "failed": 2,
  "unique_senders": 23,
  "busiest_hour": "14:00"
}
```

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/whatsapp-message-queue-api.git
cd whatsapp-message-queue-api
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the server**
```bash
python server.py
```

The API will start on `http://localhost:5000`

---

## 🧪 Testing

### Run Test Suite
```bash
python test.py
```

This will:
- Create sample messages
- Test all endpoints
- Validate error handling
- Check filtering and search
- Verify bulk operations

### Manual Testing with curl

**Create a message:**
```bash
curl -X POST http://localhost:5000/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "9876543210",
    "message": "Test message",
    "sender_name": "riya"
  }'
```

**Get all pending messages:**
```bash
curl "http://localhost:5000/api/messages?status=pending"
```

**Mark as processed:**
```bash
curl -X PATCH http://localhost:5000/api/messages/1/process
```

---

## 📊 Error Handling

The API returns descriptive error messages with appropriate HTTP status codes:

**Validation Errors (400):**
```json
{
  "error": "Phone number must be 10 digits"
}
```

**Not Found (404):**
```json
{
  "error": "Message with ID 999 not found"
}
```

**Server Errors (500):**
```json
{
  "error": "Internal server error"
}
```

---

## 🔮 Future Enhancements

### Phase 1 (Next Week)
- [ ] SQLite database integration for data persistence
- [ ] Rate limiting (100 messages per hour per sender) 

### Phase 2 (Future)
- [ ] Priority assignment according to urgency of message
- [ ] PostgreSQL migration for production scalability

---

## 📁 Project Structure

whatsapp-message-queue-api/
│
├── server.py           # Main Flask application
├── test.py            # Test suite
├── README.md          # Project documentation
└── requirements.txt   # Python dependencies

---

## 🏢 Business Context

This API was developed to handle high-volume message processing for a WhatsApp Business automation platform. It enables:

1. **Support Teams**: Manage incoming customer queries efficiently
2. **Sales Teams**: Track and follow up on leads
3. **Analytics**: Monitor response times and team performance
4. **Automation**: Integrate with AI chatbots for intelligent routing

**Current Status**: MVP completed with in-memory storage. Database integration in progress for production deployment.

---

## 👨‍💻 Development

**Author**: Riya Chaleria 
**Context**: Built during Software Development Internship at Yashas AI  
**Timeline**: May 2024 (1 week)  
**Technologies**: Flask, Python, REST API Design

## 👨‍💻 About This Project

This API serves as the message queue backend for customer communication workflows.

### Key Learnings
- RESTful API architecture and best practices
- Input validation and error handling patterns
- Flask framework and routing
- HTTP status codes and response formatting
- Bulk operations and data filtering
- Professional API documentation

---

## 📝 API Design Decisions

### RESTful Architecture
- Resource-based URLs (`/messages` not `/getMessages`)
- Standard HTTP methods (GET, POST, PATCH, DELETE)
- Proper status codes indicating request outcomes
- JSON request/response format

### Why Array of IDs for Bulk Operations?
Provides flexibility: users can process specific messages OR all pending messages with a single endpoint, reducing API surface area while maintaining functionality.

### Why In-Memory First?
Rapid prototyping approach: validate API design and business logic before adding database complexity. This is a common startup practice for MVP development.

---

## 🤝 Contributing

This is a learning project, but suggestions are welcome! Feel free to:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📄 License

This project is shared for portfolio and evaluation purposes only.
Unauthorized copying, distribution, or commercial use is not permitted.

---

## 🔗 Connect

**LinkedIn**: https://www.linkedin.com/in/riya-chaleria-1b8712248/  
**Email**: riyachaleria@gmail.com 

---

**Built with ❤️ during my internship at Yashas AI**