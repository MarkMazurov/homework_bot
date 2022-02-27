import json
import logging
import os
import time
from http import HTTPStatus
from sys import exit, stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (MyEmptyDictError, MyUnintendedError,
                        MyUnknownStatusError)

load_dotenv()

"""Переменные, которые нужны для работы бота. Лежат в файле .env"""
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# Создаем логгер для приложения. Логи выводим в поток sys.stdout.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=stdout)
logger.addHandler(handler)

# Создаем форматер для красивого вывода сообщений в логах.
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Функция отправки ботом сообщения в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение успешно отправлено в Telegram!')
        return True
    except Exception as error:
        logger.error(error, exc_info=True)
        return False


def get_api_answer(current_timestamp):
    """Отправляем GET-запрос на эндпоинт."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        string = 'Получен статус {}. А нужен 200!'.format(response.status_code)
        raise requests.exceptions.RequestException(string)
    except json.decoder.JSONDecodeError as error:
        string = f'Не переведено в json - {error}'
        logger.error(string, exc_info=True)
        raise json.decoder.JSONDecodeError(string)
    except requests.exceptions.RequestException as error:
        string = f'Статус ответа - {response.status_code}: {error}'
        logger.error(string, exc_info=True)
        raise requests.exceptions.RequestException(string)
    except MyUnintendedError as error:
        string = f'Непредусмотренная ошибка в get_api_answer: {error}'
        logger.error(string, exc_info=True)
        raise MyUnintendedError(string)


def check_response(response):
    """Функция для проверки корректности ответа API.
    В случае положительного ответа возвращает список домашних работ.
    """
    if type(response) != dict:
        string = 'В response пришёл не словарь!'
        logger.error(string, exc_info=True)
        raise TypeError(string)
    if ('homeworks' and 'current_date') not in response.keys():
        string = 'В словаре нет одного из ключей!'
        logger.error(string, exc_info=True)
        raise KeyError(string)
    if type(response['homeworks']) != list:
        string = 'Отсутствует список домашних работ!'
        logger.error(string, exc_info=True)
        raise TypeError(string)
    if not response:
        string = 'В ответе пришёл пустой словарь!'
        logger.error(string, exc_info=True)
        raise MyEmptyDictError(string)
    try:
        homeworks_list = response['homeworks']
        return homeworks_list
    except MyUnintendedError as error:
        string = f'Непредусмотренная ошибка в check_response: {error}'
        logger.error(string, exc_info=True)
        raise MyUnintendedError(string)


def parse_status(homework):
    """Функция для извлечения статуса домашней работы."""
    if ('homework_name' and 'status') not in homework.keys():
        string = 'В homework отсутствует один из нужных ключей.'
        logger.error(string, exc_info=True)
        raise KeyError(string)
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except MyUnintendedError as error:
        string = f'Непредусмотренная ошибка в parse_status: {error}'
        logger.error(string, exc_info=True)
        raise MyUnintendedError(string)

    if homework_status not in HOMEWORK_STATUSES:
        string = 'Неизвестный статус домашней работы!'
        logger.debug(string)
        raise MyUnknownStatusError(string)

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция для проверки наличия переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main():
    """Основная логика работы бота."""
    # Проверяем, все ли переменные окружения нам доступны.
    # Если нет - принудительно завершаем программу.
    if check_tokens() is False:
        logger.critical('Отсутствует обязательная переменная окружения!')
        exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    # Переменная, которая не даст отправить повторное сообщение.
    sent_message = ''

    while True:
        try:
            # Отправляем GET-запрос к API.
            response = get_api_answer(current_timestamp)

            # Проверям полученный от API ответ.
            check = check_response(response)

            # Проверяем наличие новых домашек в списке.
            if len(check) == 0:
                logger.debug('Нет свежих домашних работ.')

            # Получаем нужную работу из списка домашек.
            homework = check[0]

            # Извлекаем статус нужной домашней работы.
            message = parse_status(homework)

            # Передаем боту текст сообщения и отправляем письмо.
            if message != sent_message:
                check_send = send_message(bot, message)
                if check_send:
                    sent_message = message

            # Записываем в переменную время последнего запроса.
            current_timestamp = response['current_date']

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message != sent_message:
                check_send = send_message(bot, message)
                if check_send:
                    sent_message = message

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
