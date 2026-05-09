class CbrClientError(RuntimeError):
    pass


class CbrParserError(RuntimeError):
    pass


class CbrEmptyResultError(CbrParserError):
    pass
