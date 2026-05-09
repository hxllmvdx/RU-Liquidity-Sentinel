import openai
openai.api_key = ""

def embed_text(text: str):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )

    return response['data'][0]['embedding']
