#-----LLM--------
import os, openai

client = openai.OpenAI(
  api_key=os.environ["ASI_API_KEY"],
  base_url="https://inference.asicloud.cudos.org/v1"
)

def useGemma(content):
    resp = client.chat.completions.create(
      model="meta-llama/llama-3.3-70b-instruct",
      messages=[{"role":"user","content":content}],
      max_tokens=100
    )
    return resp.choices[0].message.content.replace("_quote_",'"').replace("_apostrophe_","'")

#-----EMBEDDING (LOCAL)--------
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/e5-large-v2")

def useLocalEmbedding(atom):
    return  model.encode(
        atom,
        normalize_embeddings=True
    ).tolist()

#-----FORMATTING HELPER-------
def repair_commands(s):
    parts = s.split('(')
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # remove all closing parens
        part = part.replace(')', '').strip()
        if not part:
            continue
        # split cmd and rest
        if ' ' in part:
            cmd, rest = part.split(None, 1)
            rest = rest.strip()
            # strip mismatched surrounding quotes
            if rest.startswith(("'", '"')) and rest.endswith(("'", '"')):
                arg = rest[1:-1]
            else:
                arg = rest.strip("'\"")
            out.append(f'({cmd} "{arg}")')
        else:
            # no args
            out.append(f"({part})")
    return "(" + " ".join(out) + ")"
