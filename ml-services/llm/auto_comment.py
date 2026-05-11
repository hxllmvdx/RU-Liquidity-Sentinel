from client import LLMClient
from prompt_templates import AUTO_COMMENT_PROMPT
from vector_store import VectorStore


class LiquidityAgent:

    def __init__(self):

        self.llm = LLMClient()

        self.vector_store = VectorStore()

        self.load_historical_context()

    def load_historical_context(self):

        docs = [

            """
            Март 2022:
            Резкий рост спроса на repo funding.
            RUONIA существенно выросла.
            Банковский сектор испытывал
            дефицит ликвидности.
            """,

            """
            Сентябрь 2023:
            Налоговый период вызвал
            краткосрочный liquidity stress.
            Спрос на недельное репо ЦБ вырос.
            """,

            """
            Декабрь 2024:
            Слабый спрос на аукционах ОФЗ
            сопровождался ухудшением
            liquidity conditions.
            """,
        ]

        self.vector_store.add_documents(docs)

    def ask(
        self,
        question,
        market_context=None,
    ):

        historical_context = self.vector_store.search(
            question
        )

        retrieved_context = "\n\n".join(
            historical_context
        )

        prompt = AUTO_COMMENT_PROMPT.format(
            lsi_value="N/A",
            status="N/A",
            m1="N/A",
            m2="N/A",
            m3="N/A",
            m4="N/A",
            m5="N/A",
            active_flags="N/A",
            ruonia="N/A",
            repo_cover="N/A",
            repo_rate_spread="N/A",
            ofz_cover="N/A",
            seasonal_factor="N/A",
            upcoming_tax_dates="N/A",
            upcoming_ofz_auctions="N/A",
            historical_context=retrieved_context,
            retrieved_context=retrieved_context,
        )

        messages = [
            {
                "role": "system",
                "content": prompt,
            }
        ]

        if market_context:

            messages.append(
                {
                    "role": "user",
                    "content": f"""
Текущий рыночный контекст:

{market_context}
""",
                }
            )

        messages.append(
            {
                "role": "user",
                "content": f"""
Вопрос:
{question}
""",
            }
        )

        return self.llm.generate(
            messages=messages,
            temperature=0.2,
        )


if __name__ == "__main__":

    agent = LiquidityAgent()

    response = agent.ask(
        question="Что происходит с ликвидностью?",
        market_context="""
RUONIA выросла до 18.2%.
Repo cover ratio = 2.7.
Спрос на недельное репо ЦБ вырос.
        """,
    )

    print(response)