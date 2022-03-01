class MyResponseStatusError(Exception):
    """Кастомное исключение при обращении к эндпоинту."""

    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        print('calling str')
        if self.message:
            return 'MyResponseStatusError, {0} '.format(self.message)
        else:
            return 'MyResponseStatusError has been raised'


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
