# AI Features Setup Guide

Nexus ERP includes AI-powered features that require an OpenAI API key. This guide explains how to set up and configure AI capabilities.

## Overview

Nexus ERP uses OpenAI's GPT models for the following features:

1. **AI Chatbot** - Natural language interface for querying ERP data
2. **Demand Forecasting** - Predictive analytics for inventory planning
3. **Anomaly Detection** - Automatic detection of unusual patterns in data
4. **OCR Service** - Document parsing and data extraction
5. **Natural Language Queries** - Convert natural language to database queries

## Getting an OpenAI API Key

### Step 1: Create OpenAI Account

1. Visit [OpenAI's website](https://platform.openai.com/)
2. Sign up for an account
3. Verify your email address

### Step 2: Add Payment Method

1. Go to [Billing settings](https://platform.openai.com/account/billing)
2. Add a payment method
3. Add credits to your account (minimum $5 recommended)

### Step 3: Generate API Key

1. Navigate to [API Keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Give it a name (e.g., "Nexus ERP Production")
4. Copy the key immediately (it won't be shown again)

## Configuration

### Environment Variable

Add your API key to the `.env` file:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=gpt-4o
```

### Using Docker

```bash
# In docker-compose.yml, the variable is passed through
# Just set it in your .env file
docker compose up -d
```

### Verifying Configuration

```bash
# Check if the key is set
docker compose exec backend env | grep OPENAI

# Test the API connection
docker compose exec backend python -c "
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model='gpt-4o',
    messages=[{'role': 'user', 'content': 'Hello!'}],
    max_tokens=50
)
print('API working:', response.choices[0].message.content)
"
```

## Model Selection

Nexus ERP supports the following models:

| Model | Use Case | Cost (per 1M tokens) |
|-------|----------|---------------------|
| `gpt-4o` | Default, best quality | $5 input / $15 output |
| `gpt-4o-mini` | Fast, economical | $0.15 input / $0.60 output |
| `gpt-4-turbo` | High complexity tasks | $10 input / $30 output |

### Changing the Model

```env
# For cost optimization
OPENAI_MODEL=gpt-4o-mini

# For best quality
OPENAI_MODEL=gpt-4o
```

## Feature Configuration

### AI Chatbot

The chatbot uses the system prompt defined in `chatbot_service.py`. It supports:
- Natural language queries in English and Arabic
- Context-aware responses
- Action execution (queries, order creation)

### Forecasting Service

Uses ensemble methods with AI refinement:
- ARIMA (AutoRegressive Integrated Moving Average)
- Exponential Smoothing (Holt-Winters)
- Linear Regression
- AI-powered refinement using OpenAI

### OCR Service

For document parsing:
- Primary: OpenAI GPT-4 Vision API
- Fallback: pytesseract (for local OCR)

## Cost Management

### Estimated Usage

| Feature | Average Tokens/Request | Est. Daily Cost |
|---------|----------------------|-----------------|
| Chatbot | 500-1000 | $0.01-0.02 per user |
| Forecasting | 2000-3000 | $0.02-0.05 per run |
| OCR | 3000-5000 | $0.03-0.08 per document |
| Anomaly Detection | 1000-2000 | $0.01-0.03 per analysis |

### Cost Optimization Tips

1. **Use gpt-4o-mini for simple tasks**
   ```env
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **Reduce max_tokens**
   ```python
   # In llm_provider.py
   config = LLMConfig(max_tokens=500)  # Lower limit
   ```

3. **Enable caching** (already implemented)
   - Responses are cached for 1 hour
   - Reduces duplicate API calls

4. **Monitor usage**
   ```python
   from app.services.ai.llm_provider import get_llm_service
   stats = get_llm_service().get_stats()
   print(f"Total cost: ${stats['total_cost']:.4f}")
   ```

## Rate Limits

OpenAI has rate limits based on your tier:

| Tier | RPM (Requests/min) | TPM (Tokens/min) |
|------|-------------------|------------------|
| Free | 3 | 40,000 |
| Tier 1 | 500 | 200,000 |
| Tier 2 | 5,000 | 2,000,000 |

Nexus ERP handles rate limits automatically with:
- Exponential backoff
- Retry logic (3 retries by default)
- Fallback to mock responses if all retries fail

## Testing Without API Key

Nexus ERP includes a mock provider for development:

```python
from app.services.ai.llm_provider import LLMService

# Use mock provider
service = LLMService(default_provider="mock")
response = await service.complete(messages=[...])
```

Or set in environment:
```env
LLM_PROVIDER=mock
```

## Troubleshooting

### API Key Not Working

```bash
# Test directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

Common issues:
- Key has been revoked
- Insufficient credits
- Wrong environment variable name

### Rate Limit Exceeded

Error message: "Rate limit exceeded"

Solutions:
1. Wait and retry (automatic)
2. Upgrade OpenAI tier
3. Reduce request frequency

### Timeout Errors

If AI requests timeout:

```python
# Increase timeout in llm_provider.py
client = AsyncOpenAI(api_key=api_key, timeout=60.0)  # 60 seconds
```

### Memory Issues

For large documents:
1. Split into smaller chunks
2. Use streaming responses
3. Reduce max_tokens

## Privacy & Data Handling

- **Data sent to OpenAI**: Text queries and document content
- **Data retention**: OpenAI retains data for 30 days (default)
- **Opt out**: Contact OpenAI support to disable training on your data

### Sensitive Data

Avoid sending to AI:
- Credit card numbers
- Social security numbers
- Passwords
- Personal identification numbers

Use `MASKED` placeholders in prompts for sensitive fields.

## Support

For AI-related issues:
1. Check OpenAI status: [status.openai.com](https://status.openai.com/)
2. Review logs: `docker compose logs backend | grep -i "ai\|openai"`
3. Test with mock provider to isolate issues
