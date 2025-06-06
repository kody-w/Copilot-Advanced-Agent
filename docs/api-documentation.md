# API Documentation

## Overview

The Azure AI Chatbot exposes a single HTTP endpoint that accepts POST requests with JSON payloads. The API uses function-level authentication and supports CORS for web integration.

## Base URL

```
https://<your-function-app>.azurewebsites.net/api/businessinsightbot_function
```

## Authentication

The API uses function key authentication. Include the function key as a query parameter:

```
?code=<your-function-key>
```

## Endpoints

### POST /api/businessinsightbot_function

Send a message to the chatbot and receive a response.

#### Request Headers

```http
Content-Type: application/json
```

#### Request Body

```json
{
  "user_input": "string",
  "conversation_history": [
    {
      "role": "user|assistant",
      "content": "string"
    }
  ],
  "user_guid": "string (optional)"
}
```

##### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_input` | string | Yes | The user's message to the chatbot |
| `conversation_history` | array | No | Array of previous messages in the conversation |
| `user_guid` | string | No | Unique identifier for user-specific memory. If not provided, uses default GUID |

##### Conversation History Format

Each message in the conversation history should have:
- `role`: Either "user" or "assistant"
- `content`: The message content

#### Response

##### Success Response (200 OK)

```json
{
  "assistant_response": "string",
  "agent_logs": "string",
  "user_guid": "string"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `assistant_response` | string | The chatbot's response to the user |
| `agent_logs` | string | Logs of any agents that were executed |
| `user_guid` | string | The GUID used for this conversation |

##### Error Responses

**400 Bad Request**
```json
{
  "error": "Missing or empty user_input in JSON payload"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "details": "string"
}
```

## Examples

### Basic Chat Request

```bash
curl -X POST "https://mybot.azurewebsites.net/api/businessinsightbot_function?code=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "What can you help me with?",
    "conversation_history": []
  }'
```

### Continuing a Conversation

```bash
curl -X POST "https://mybot.azurewebsites.net/api/businessinsightbot_function?code=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Tell me more about that",
    "conversation_history": [
      {
        "role": "user",
        "content": "What can you help me with?"
      },
      {
        "role": "assistant",
        "content": "I can help you with various tasks including..."
      }
    ]
  }'
```

### User-Specific Memory

```bash
curl -X POST "https://mybot.azurewebsites.net/api/businessinsightbot_function?code=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Remember that my favorite color is blue",
    "user_guid": "12345678-1234-1234-1234-123456789012",
    "conversation_history": []
  }'
```

### Initialize User Session

Send just a GUID as the first message to load user-specific memories:

```bash
curl -X POST "https://mybot.azurewebsites.net/api/businessinsightbot_function?code=abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "12345678-1234-1234-1234-123456789012",
    "conversation_history": []
  }'
```

## JavaScript/TypeScript Example

```javascript
async function sendMessage(message, conversationHistory = [], userGuid = null) {
  const response = await fetch(
    `${API_URL}?code=${FUNCTION_KEY}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_input: message,
        conversation_history: conversationHistory,
        user_guid: userGuid
      })
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Usage
try {
  const result = await sendMessage("Hello!", [], "my-user-guid");
  console.log("Bot:", result.assistant_response);
} catch (error) {
  console.error("Error:", error);
}
```

## Python Example

```python
import requests
import json

def chat_with_bot(message, conversation_history=None, user_guid=None):
    url = f"{API_URL}?code={FUNCTION_KEY}"
    
    payload = {
        "user_input": message,
        "conversation_history": conversation_history or [],
        "user_guid": user_guid
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()

# Usage
try:
    result = chat_with_bot("Hello!", user_guid="my-user-guid")
    print(f"Bot: {result['assistant_response']}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
```

## Rate Limits

- **Requests per minute**: Depends on your Azure Function App tier
  - Consumption plan: ~100 requests per minute
  - Premium plan: Higher limits available
- **Payload size**: Maximum 100MB (Azure Functions limit)
- **Timeout**: 10 minutes (configured in host.json)

## CORS Configuration

The API supports CORS with the following default configuration:
- **Allowed Origins**: * (all origins)
- **Allowed Methods**: GET, POST, OPTIONS
- **Allowed Headers**: *

For production, configure specific origins in your Function App settings.

## Webhooks and Events

The chatbot can trigger external webhooks through agents. For example, the Email Drafting Agent sends data to a Power Automate flow.

## Error Handling

The API returns appropriate HTTP status codes:
- **200**: Success
- **400**: Bad request (invalid input)
- **401**: Unauthorized (missing or invalid function key)
- **500**: Internal server error

Always check the response status and handle errors appropriately in your client application.

## Best Practices

1. **Conversation History**: Keep conversation history to maintain context, but trim old messages to avoid token limits
2. **User GUIDs**: Use consistent GUIDs for users to maintain their memory across sessions
3. **Error Handling**: Always implement proper error handling and retry logic
4. **Rate Limiting**: Implement client-side rate limiting to avoid hitting Azure limits
5. **Timeouts**: Set appropriate timeouts (recommended: 30 seconds)

## Testing

Use the provided Postman collection in `examples/postman/` or test with curl commands as shown in the examples above.