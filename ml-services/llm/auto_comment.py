from client import LLMClient
from prompt_templates import AUTO_COMMENT_PROMPT


client = LLMClient()


def generate_auto_comment(context):

    prompt = AUTO_COMMENT_PROMPT.format(
        context=context
    )

    return client.generate(prompt)


if __name__ == "__main__":

    market_context = """
    RUONIA выросла до 18.2%.
    Спрос на недельное repo ЦБ усилился.
    Repo cover ratio достиг 2.7.
    Наблюдается снижение спроса на OFZ аукционах.
    Приближается налоговый период.
    """

    result = generate_auto_comment(
        market_context
    )

    print()
    print(result)
    print()