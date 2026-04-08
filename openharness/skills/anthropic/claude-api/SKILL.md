---
name: claude-api
description: Build apps with the Claude API or Anthropic SDK. TRIGGER when code imports anthropic or @anthropic-ai/sdk, or when the user asks to use the Claude API, Anthropic SDKs, or Agent SDK.
---
# Claude API Skill

Build applications using the Claude API and Anthropic SDK.

## Python SDK

```python
import anthropic

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)
print(message.content[0].text)
```

## Streaming

```python
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a poem"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## Tool Use

```python
tools = [{
    "name": "get_weather",
    "description": "Get current weather for a location",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        },
        "required": ["location"]
    }
}]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in Seoul?"}]
)
```

## Best Practices
- Use the latest model (claude-sonnet-4-20250514 or claude-opus-4-20250514)
- Set appropriate max_tokens
- Use system prompts for consistent behavior
- Handle rate limits with exponential backoff
- Use streaming for better UX in interactive applications
