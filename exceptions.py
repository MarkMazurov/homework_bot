class MyUnintendedError(Exception):
    """Непредусмотренная ошибка."""

    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        print('calling str')
        if self.message:
            return 'MyUnintendedError, {0} '.format(self.message)
        else:
            return 'MyUnintendedError has been raised'


class MyEmptyDictError(Exception):
    """Ошибка, когда в ответе от API пришёл пустой словарь."""

    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        print('calling str')
        if self.message:
            return 'MyEmptyDictError, {0} '.format(self.message)
        else:
            return 'MyEmptyDictError has been raised'


class MyUnknownStatusError(Exception):
    """Ошибка при получении неизвестного статуса работы."""

    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        print('calling str')
        if self.message:
            return 'MyUnknownStatusError, {0} '.format(self.message)
        else:
            return 'MyUnknownStatusError has been raised'
