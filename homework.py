import json
import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from sys import exit, stdout

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

from exceptions import MyResponseStatusError, MyUnknownStatusError

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

# Дополнительно выводим логи в файл logs.log
sec_handler = RotatingFileHandler(
    'logs.log',
    maxBytes=50_000_000,
    backupCount=5
)
logger.addHandler(sec_handler)

# Создаем форматер для красивого вывода сообщений в логах.
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
handler.setFormatter(formatter)
sec_handler.setFormatter(formatter)


def send_message(bot, message):
    """Функция отправки ботом сообщения в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение успешно отправлено в Telegram!')
    except TelegramError:
        string = 'Сбой при отправке сообщения!'
        logger.error(string, exc_info=True)
        raise TelegramError(string)


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
        string = f'Получен статус {response.status_code}. А нужен 200!'
        logger.error(string, exc_info=True)
        raise MyResponseStatusError(string)
    except json.decoder.JSONDecodeError as error:
        string = f'Не переведено в json - {error}'
        logger.error(string, exc_info=True)
        raise json.decoder.JSONDecodeError(string)
    except requests.RequestException as error:
        string = f'Ошибка при выполнении GET-запроса: {error}'
        logger.error(string, exc_info=True)
        raise requests.RequestException(string)


def check_response(response):
    """Функция для проверки корректности ответа API.
    В случае положительного ответа возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        string = 'В response пришёл не словарь!'
        logger.error(string, exc_info=True)
        raise TypeError(string)
    if 'homeworks' not in response:
        string = 'В словаре нет ключа "homeworks"!'
        logger.error(string, exc_info=True)
        raise KeyError(string)
    if 'current_date' not in response:
        string = 'В словаре нет ключа "current_date"!'
        logger.error(string, exc_info=True)
        raise KeyError(string)
    if not isinstance(response['homeworks'], list):
        string = 'Отсутствует список домашних работ!'
        logger.error(string, exc_info=True)
        raise TypeError(string)
    homeworks_list = response['homeworks']
    return homeworks_list


def parse_status(homework):
    """Функция для извлечения статуса домашней работы."""
    if 'homework_name' not in homework:
        string = 'В homework отсутствует ключ "homework_name".'
        logger.error(string, exc_info=True)
        raise KeyError(string)
    if 'status' not in homework:
        string = 'В homework отсутствует ключ "status".'
        logger.error(string, exc_info=True)
        raise KeyError(string)
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_STATUSES:
        string = 'Неизвестный статус домашней работы!'
        logger.debug(string)
        raise MyUnknownStatusError(string)

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция для проверки наличия переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    correct_tokens = []

    for key, token in tokens.items():
        if token is None:
            logger.critical(f'Отсутствует переменная окружения: {key}')
        if token:
            correct_tokens.append(token)
    if len(correct_tokens) == 3:
        return True
    return False


def main():
    """Основная логика работы бота."""
    # Проверяем, все ли переменные окружения нам доступны.
    # Если нет - принудительно завершаем программу.
    if not check_tokens():
        exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    # Переменная, которая не даст отправить повторное сообщение.
    sent_message = None
    sent_error_message = None

    while True:
        try:
            # Отправляем GET-запрос к API.
            response = get_api_answer(current_timestamp)

            # Проверям полученный от API ответ.
            check = check_response(response)

            # Проверяем наличие новых домашек в списке.
            if len(check) == 0:
                string = 'Нет свежих домашних работ.'
                logger.debug(string)
                raise IndexError(string)

            # Получаем нужную работу из списка домашек.
            homework = check[0]

            # Извлекаем статус нужной домашней работы.
            message = parse_status(homework)

            # Передаем боту текст сообщения и отправляем письмо.
            if message != sent_message:
                send_message(bot, message)
                sent_message = message

            # Записываем в переменную время последнего запроса.
            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logger.error(error_message, exc_info=True)
            if error_message != sent_error_message:
                send_message(bot, error_message)
                sent_error_message = error_message

        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
