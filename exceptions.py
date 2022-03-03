class MyResponseStatusError(Exception):
    """Кастомное исключение при обращении к эндпоинту."""

    pass


class MyUnknownStatusError(Exception):
    """Ошибка при получении неизвестного статуса работы."""

    pass
