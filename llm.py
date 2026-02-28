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
