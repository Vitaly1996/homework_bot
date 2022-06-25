import os
import sys
import time
import enum
import threading

import logging
import telegram
import requests

from dotenv import load_dotenv
from http import HTTPStatus
from typing import Dict, List, Union

from exceptions import (
    APIResponseError, APIStatusCodeError, ExchangeError, TelegramError
)


class State(enum.Enum):
    """Описывает состояния экземпляра state."""

    INITIAL = 0
    RUNNING = 1
    STOPPED = 2


state = State.INITIAL
state_lock = threading.Lock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

COUNT_PREVIOUS_WEEK = 21686400
RETRY_TIME = 6
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщений в telegram чат."""
    try:
        logging.info(
            'Отправляем сообщение в телеграм: %s', message
        )
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as exc:
        raise TelegramError(
            f'Ошибка отправки сообщения в телеграмм: {exc}'
        ) from exc
    else:
        logging.info('Сообщение в телеграм успешно отправлено')


def get_api_answer(current_timestamp: int):
    """Делает запрос к эндпоинту API и возвращает ответ."""
    try:
        logging.info('Запрашиваем статус ДЗ')
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as exc:
        raise ExchangeError(f'Ошибка подключения к сервису ЯП: {exc}') from exc
    else:
        if api_answer.status_code == HTTPStatus.OK:
            response = api_answer.json()

        else:
            APIStatusCodeError('Статус код не 200')
    return response


def check_response(response: Dict[str, List[Dict[str, Union[int, str]]]]) \
        -> Dict[str, Union[int, str]]:
    """Проверка ответа api на корректность."""
    logging.info('Проверка ответа от API начата')

    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарём')
    homework = response.get('homeworks')

    if not isinstance(homework[0], dict):
        raise TypeError('Ответ не является словарём.')

    if homework is None:
        raise APIResponseError(
            'В ответе API отсутствует необходимый ключ "homeworks, '
            f'response = {response}'
        )

    for item in homework:
        if not isinstance(item, dict):
            raise TypeError(
                'В ответе от API в списке пришли не словари, '
                f'response = {response}'
            )
    logging.info('Проверка ответа от API завершена.Ошибок не обнаружено')
    return homework


def parse_status(homework: dict) -> str:
    """Извлечение статуса домашней работы."""
    logging.info('Извлекаем статус домашней работы')
    homework_status = homework['status']
    homework_name = homework['homework_name']
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        raise Exception('Обнаружен недокументированный статус.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all((
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = (
            'Отсутствуют обязательные переменные окружения:'
            'PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.'
            'Программа принудительно остановлена.'
        )
        logging.critical(error_message)
        sys.exit(error_message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - COUNT_PREVIOUS_WEEK

    global state
    with state_lock:
        state = State.RUNNING

    current_report = None
    prev_report = current_report

    while True:
        with state_lock:
            if state == State.STOPPED:
                break

        try:
            response = get_api_answer(current_timestamp)
            result_check = check_response(response)
            homework = result_check[0]
            current_report = parse_status(homework)
            if current_report == prev_report:
                logging.debug(
                    'Статус домашней работы не обновился.'
                    'Придется ещё немного подождать.'
                )
        except Exception as exc:
            error_message = f'Сбой в работе программы: {exc}'
            current_report = error_message
            logging.exception(error_message)

        try:
            if current_report != prev_report:
                send_message(bot, current_report)
                prev_report = current_report

        except TelegramError as exc:
            error_message = f'Сбой в работе программы: {exc}'
            logging.exception(error_message)

        time.sleep(RETRY_TIME)


def repl():
    """Выполняет мягкую остановку бесконечного цикла по команде."""
    global state
    while True:
        command = input('Please, press "s" to stop')
        if command == 's':
            with state_lock:
                state = state.STOPPED
                break


if __name__ == '__main__':
    log_format = (
        '%(asctime)s [%(levelname)s]-'
        '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
    )
    log_file = os.path.join(BASE_DIR, 'output.log')
    log_stream = sys.stdout
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(log_stream)
        ],
    )
    repl_thread = threading.Thread(target=repl)
    repl_thread.start()
    main()
