### Homework_bot
### Описание
Telegram-бот, который обращается к API сервиса Практикум.Домашка и узнает статус домашней работы:взята ли в ревью, проверена ли, а если проверена - то принял ее ревьер или вернул на доработку

### Технологии
- python 3.7
- python-telegram-bot
- dotenv

### Установка
- склонировать репозиторий
```sh
git clone github.com/Vitaly1996/homework_bot.git
```
- создать и активировать виртуальное окружение для проекта

```sh
python -m venv venv
source venv/scripts/activate (Windows)    
source venv/bin/activate (MacOS/Linux)
python3 -m pip install --upgrade pip
```
- установить зависимости

```sh
python pip install -r requirements.txt
```
- в корневой директории проекта создать файл .env и записать в него следующие переменные окружения:    
PRACTICUM_TOKEN = <Ваш токен практикума>    
TELEGRAM_TOKEN = <Ваш токен telegram>     
TELEGRAM_CHAT_ID = <Ваш chat_id telegram>    

