import os

from openai import OpenAI


class LLMClient:

    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "ollama"),
            base_url=os.getenv(
                "OPENAI_BASE_URL",
                "http://localhost:11434/v1",
            ),
        )

        self.model = os.getenv(
            "LLM_MODEL",
            "qwen2.5:7b",
        )

    def generate(
        self,
        messages,
        temperature: float = 0.2,
    ):

        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )

            return response.choices[0].message.content

        except Exception as e:

            return f"LLM generation error: {str(e)}"


if __name__ == "__main__":

    client = LLMClient()

    messages = [
        {
            "role": "user",
            "content": input("Введите запрос: "),
        }
    ]

    print(client.generate(messages))