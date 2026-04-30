import os, openai, ollama

# Existing cloud clients
ASI_CLIENT = openai.OpenAI(
    api_key=os.environ.get("ASI_API_KEY", "empty"),
    base_url="https://inference.asicloud.cudos.org/v1"
)

ANTHROPIC_CLIENT = openai.OpenAI(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "empty"),
    base_url="https://api.anthropic.com/v1/"
)

def _clean(text):
    return text.replace("_quote_", '"').replace("_apostrophe_", "'")

def _chat_cloud(client, model, content, max_tokens=6000):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
    )
    return _clean(resp.choices[0].message.content)

def _chat_ollama(model, content, max_tokens=6000):
    print('this is my content', content)
    resp = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": content}],
      
        
    )
    return _clean(resp['message']['content'])

def useClaude(content):
    return _chat(
        model="qwen2.5:14b",
        content=content
    )

def useMiniMax(content):
    return _chat(
        model="qwen2.5:14b",
        content=content
    )

def useOllama(content):
    return _chat_ollama(
        model="qwen2.5:14b",
        content=content
    )


def _chat(model, content, max_tokens=6000):
    resp = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": content}],
        
       
    )
    return _clean(resp['message']['content'])
# Embedding
_embedding_model = None

def initLocalEmbedding():
    model_name = "intfloat/e5-large-v2"
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

    