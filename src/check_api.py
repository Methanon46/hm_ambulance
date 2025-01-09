import anthropic
import config

client_key = config.ANTHROPIC_API_KEY

client = anthropic.Anthropic(
    api_key=client_key
)

response = client.messages.count_tokens(
    model="claude-3-5-sonnet-20241022",
    system="You are a scientist",
    messages=[{
        "role": "user",
        "content": "Hello, Claude"
    }],
)

print(response.json())
