import os, openai


ASI_CLIENT = None
if os.environ.get("ASI_API_KEY"):
    ASI_CLIENT = openai.OpenAI(
        api_key=os.environ.get("ASI_API_KEY"),
        base_url="https://inference.asicloud.cudos.org/v1"
    )

ANTHROPIC_CLIENT = None
if os.environ.get("ANTHROPIC_API_KEY"):
    ANTHROPIC_CLIENT = openai.OpenAI(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        base_url="https://api.anthropic.com/v1/"
    )

OLLAMA_CLIENT = openai.OpenAI(
    base_url="http://localhost:11434/v1", 
    api_key="ollama"
)

OPENROUTER_CLIENT = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", "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")
)

def _clean(text):
    return text.replace("_quote_", '"').replace("_apostrophe_", "'")

def _chat(client, model, content, max_tokens=6000, thinking=False):
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens
    }
    if thinking:
        kwargs["extra_body"] = {
            "enable_thinking": True,
            "thinking_budget": 6000
        }
    resp = client.chat.completions.create(**kwargs)
    return _clean(resp.choices[0].message.content)

def useMiniMax(content):
    if ASI_CLIENT is None:
        return useDefault(content)
    return _chat(
        client=ASI_CLIENT,
        model="minimax/minimax-m2.7",
        content=content,
        thinking=True
    )

def useClaude(content):
    if ANTHROPIC_CLIENT is None:
        return useDefault(content)
    return _chat(
        client=ANTHROPIC_CLIENT,
        model="claude-3-5-sonnet-20241022",
        content=content,
        thinking=True
    )

def useDefault(content):
    return useOllama(content)

def useOllama(content, model="gemma3:1b"):
    return _chat(
        client=OLLAMA_CLIENT,
        model=str(model).strip('"'),
        content=content,
        thinking=False
    )

def useOpenRouter(content, model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"):
    return _chat(
        client=OPENROUTER_CLIENT,
        model=str(model).strip('"'),
        content=content,
        thinking=False
    )

_embedding_model = None

def initLocalEmbedding():
    model_name="intfloat/e5-large-v2"
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model

def useLocalEmbedding(atom):
    global _embedding_model
    if _embedding_model is None:
        raise RuntimeError("Call initLocalEmbedding() first.")
    return _embedding_model.encode(
        atom,
        normalize_embeddings=True
    ).tolist()
