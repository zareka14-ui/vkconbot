import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import logging

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен из переменных окружения Render
TOKEN = os.getenv("VK_TOKEN")
# Твой ID в ВК (цифрами), чтобы бот присылал тебе уведомления о заявках
ADMIN_ID = os.getenv("ADMIN_ID")

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# Хранилище состояний пользователей (в оперативной памяти)
user_states = {}

def send_msg(user_id, message, keyboard=None):
    post = {
        "user_id": user_id,
        "message": message,
        "random_id": 0
    }
    if keyboard:
        post["keyboard"] = keyboard.get_keyboard()
    vk.messages.send(**post)

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🏗️ Лендинг", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🤖 Чат-бот", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🎨 AI-решение", color=VkKeyboardColor.SECONDARY)
    return keyboard

def start_bot():
    logger.info("VK Bot 'Белая Род' запущен (Long Poll)...")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text
            
            # Логика состояний (State Machine)
            if text.lower() in ['начать', 'привет', 'меню']:
                user_states[user_id] = {"step": "CHOOSING_SERVICE"}
                send_msg(user_id, "🌿 Добро пожаловать в мастерскую «Белая Род»!\nВыберите нужную услугу:", get_main_keyboard())

            elif user_id in user_states:
                state = user_states[user_id]
                
                # Шаг 1: Выбор услуги
                if state["step"] == "CHOOSING_SERVICE":
                    state["service"] = text
                    state["step"] = "DETAILS"
                    send_msg(user_id, f"✅ Выбрано: {text}\n\n📝 Опишите задачу (цели, функции, референсы):")

                # Шаг 2: Детали проекта
                elif state["step"] == "DETAILS":
                    state["details"] = text
                    state["step"] = "BUDGET"
                    send_msg(user_id, "💰 Укажите ваш ориентировочный бюджет:")

                # Шаг 3: Бюджет
                elif state["step"] == "BUDGET":
                    state["budget"] = text
                    state["step"] = "CONTACT"
                    send_msg(user_id, "📞 Как с вами связаться? (Тг, телефон или email):")

                # Шаг 4: Контакты и Финал
                elif state["step"] == "CONTACT":
                    state["contact"] = text
                    
                    # Формируем заявку
                    report = (
                        f"🚀 НОВАЯ ЗАЯВКА (ВК)\n\n"
                        f"👤 Клиент: vk.com/id{user_id}\n"
                        f"🎯 Услуга: {state['service']}\n"
                        f"📝 Задача: {state['details']}\n"
                        f"💰 Бюджет: {state['budget']}\n"
                        f"📞 Контакт: {state['contact']}"
                    )
                    
                    # Отправляем админу
                    if ADMIN_ID:
                        vk.messages.send(user_id=ADMIN_ID, message=report, random_id=0)
                    
                    send_msg(user_id, "🎉 Спасибо! Заявка принята. Я свяжусь с вами в ближайшее время.", get_main_keyboard())
                    del user_states[user_id]

if __name__ == "__main__":
    start_bot()
