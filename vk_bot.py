import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("VK_TOKEN")
# Преобразуем в int сразу, чтобы избежать ошибок API
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except (ValueError, TypeError):
    ADMIN_ID = None

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

user_states = {}

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (HEALTH CHECK) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()

# --- ЛОГИКА БОТА ---
def send_msg(user_id, message, keyboard=None):
    post = {
        "user_id": user_id,
        "message": message,
        "random_id": 0
    }
    if keyboard:
        post["keyboard"] = keyboard.get_keyboard()
    try:
        vk.messages.send(**post)
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")

def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🏗️ Лендинг", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🤖 Чат-бот", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("✨ Комплексное решение", color=VkKeyboardColor.SECONDARY)
    return keyboard

def start_bot():
    logger.info("VK Bot запущен...")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text

            if text.lower() in ['начать', 'привет', 'меню']:
                user_states[user_id] = {"step": "CHOOSING_SERVICE"}
                welcome_text = (
                    "✨ Приветствуем в нашей мастерской!\n\n"
                    "Мы создаем цифровую упаковку для ваших проектов и практик: "
                    "от эстетичных лендингов до умных чат-ботов.\n\n"
                    "Выберите интересующее направление:"
                )
                send_msg(user_id, welcome_text, get_main_keyboard())

            elif user_id in user_states:
                state = user_states[user_id]
                
                if state["step"] == "CHOOSING_SERVICE":
                    state["service"] = text
                    state["step"] = "DETAILS"
                    send_msg(user_id, f"✅ Выбрано: {text}\n\n📝 Опишите кратко суть вашей задачи:")

                elif state["step"] == "DETAILS":
                    state["details"] = text
                    state["step"] = "CONTACT"
                    send_msg(user_id, "📱 Как мастер может с вами связаться? (Тг или номер телефона):")

                elif state["step"] == "CONTACT":
                    state["contact"] = text
                    
                    report = (
                        f"🚀 НОВАЯ ЗАЯВКА (ВК)\n\n"
                        f"👤 Клиент: vk.com/id{user_id}\n"
                        f"🎯 Услуга: {state['service']}\n"
                        f"📝 Задача: {state['details']}\n"
                        f"📞 Контакт: {state['contact']}"
                    )
                    
                    if ADMIN_ID:
                        send_msg(ADMIN_ID, report)
                    
                    send_msg(user_id, "🌸 Благодарим за доверие! Заявка принята. Мастер свяжется с вами в ближайшее время.", get_main_keyboard())
                    del user_states[user_id]

if __name__ == "__main__":
    # Запускаем веб-сервер в фоновом потоке
    threading.Thread(target=run_health_check, daemon=True).start()
    # Запускаем бота
    start_bot()
