import config
import pyowm
import urllib.request
import json
import os
import random
import logging
import telebot
import time
from telebot import types

# TODO: collect userinfo

logging.basicConfig(filename='bot.log', level=logging.DEBUG)
menu_markup = types.ReplyKeyboardMarkup()
menu_markup.row('/girl', '/exchange', '/weather')
clear_markup = types.ReplyKeyboardRemove()


bot = telebot.TeleBot(config.token)


def get_icon_by_status(status: str, sunset=None, sunrise=None) -> str:
    if status == 'Clear':
        if time.time() > sunrise and time.time() < sunset:
            return '☀️'
        else:
            return '🌚'
    if status == 'Clouds':
        return '☁️'
    else:
        return ''


def send_weather(cid, city: str):
    city = city
    owm = pyowm.OWM('config.owm')
    try:
        observation = owm.weather_at_place(city + ',RU')
    except pyowm.exceptions.not_found_error.NotFoundError:
        bot.send_message(cid, 'Мы не смогли найти такой город')
    else:
        w = observation.get_weather()
        temp = w.get_temperature('celsius')
        current_temp = str(temp['temp']).split('.')[0]
        status = w.get_status()
        icon = get_icon_by_status(status, w._sunset_time, w._sunrise_time)
        msg = city + ': ' + icon + ' ' + current_temp + ' °C'
        bot.send_message(cid, msg)


def pick_random_file(dir: str, ext=[]) -> str:
    '''
    Returns random file from a provided directory. If extension list is passed
    to the function the list of files will be normalized.
    '''
    file_list = os.listdir(dir)
    if ext:
        file_list = [x for x in file_list if x.rpartition('.')[-1] in ext]
    if file_list:
        random_file = random.choice(file_list)
        return random_file
    else:
        logging.warning('pick_random_file: No files with needed extensions.')
        return -1


# Обработчик команд '/start' и '/help'.
@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    bot.send_message(message.chat.id, 'Приветик!', reply_markup=menu_markup)


@bot.message_handler(commands=['settings'])
def handle_settings(message):
    bot.send_message(message.chat.id, 'Пока не готово')


@bot.message_handler(commands=['weather', 'w'])
def handle_weather(message):
    user_id = str(message.from_user.id)

    try:
        with open('users.json') as users_file:
            users_data = json.loads(users_file.read())
    except FileNotFoundError:
        users_data = {}

    try:
        user_city = users_data[user_id]['city']
    except KeyError:
        sent = bot.send_message(message.chat.id, 'Жду название города на английском')
        bot.register_next_step_handler(sent, city_choice)
    else:
        send_weather(message.chat.id, user_city)


def city_choice(message):
    user_city = message.text
    try:
        owm = pyowm.OWM(config.owm)
        observation = owm.weather_at_place(user_city + ',RU')
        owm = None
        observation = None
    except pyowm.exceptions.not_found_error.NotFoundError:
        bot.send_message(message.chat.id, 'Мы не смогли найти такой город')
    else:
        try:
            with open('users.json') as users_file:

                users_data = json.loads(users_file.read())
        except FileNotFoundError:
            users_data = {}
        user_id = message.from_user.id
        try:
            users_data[user_id]
        except KeyError:
            users_data[user_id] = {}
        users_data[user_id]['city'] = user_city
        with open('users.json', 'w+') as users_file:
            json.dump(users_data, users_file, ensure_ascii=False)
        send_weather(message.chat.id, user_city)


# Обработчик команды для поиска картинок с девушками
@bot.message_handler(commands=['girl'])
def handle_girl(message):
    # with open('message.log', 'a') as myfile:
    #     myfile.write(message.from_user.id + ': ' + message.text + '\n')
    filename = pick_random_file(config.photo_dir, config.pictures_ext)
    try:
        str(filename)
    except TypeError:
        logging.warning('handle_girls: No files with needed extensions.')
        bot.send_message(message.chat.id, 'Check folder or file extensions')
    else:
        bot.send_message(message.chat.id, 'Looking for a pretty girl for you')
        path = config.photo_dir + filename
        photo = open(path, 'rb')
        msg = bot.send_photo(message.chat.id, photo)
        file_id = msg.photo[-1].file_id
        logging.debug('handle_girl: ' + file_id)
        # bot.send_message(message.chat.id,
        #                  file_id,
        #                  reply_to_message_id=msg.message_id)
        # bot.send_photo(message.chat.id, file_id)


@bot.message_handler(commands=['ex', 'exchange', 'курс', 'доллар', 'USD'])
def handle_exchange(message):
    # with open('message.log', 'a') as myfile:
    #     myfile.write(message.from_user.id + ': ' + message.text + '\n')
    with urllib.request.urlopen("https://www.cbr-xml-daily.ru/daily_json.js") as url:
        data = json.loads(url.read().decode())
    USD = '$: ' + str(data['Valute']['USD']['Value'])
    EUR = '€: ' + str(data['Valute']['EUR']['Value'])
    bot.send_message(message.chat.id, USD)
    bot.send_message(message.chat.id, EUR)


# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_msg(message):
    # with open('message.log', 'a') as myfile:
    #     myfile.write(message.from_user.id + ': ' + message.text + '\n')
    bot.send_message(message.chat.id,
                     random.choice(config.replies),
                     reply_markup=clear_markup)


# Возвращает любое сообщение
# @bot.message_handler(func=lambda message: True, content_types=['text'])
# def echo_msg(message):
#    bot.send_message(message.chat.id, message.text, reply_markup=clear_markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)
