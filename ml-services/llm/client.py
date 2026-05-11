from openai import OpenAI

class LLMClient:

    def __init__(self):

        self.client = OpenAI(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )

        self.model = "qwen2.5:7b"

    def generate(
        self,
        prompt: str,
    ) -> str:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content