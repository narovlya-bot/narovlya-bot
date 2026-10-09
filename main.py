import os
import http.server
import threading
import telebot
from telebot import types


# --- НАСТРОЙКИ ---
API_TOKEN "8691191999:AAFAtz2tltAY3GQosohgwpm4zUsWWx17puk"
ADMIN_ID = 1099402750
PORT = int(os.environ.get("PORT", "10000"))

bot = telebot.TeleBot(API_TOKEN)
user_data = {}


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
class RenderHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Бот активен".encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def run_health_server():
    httpd = http.server.HTTPServer(("0.0.0.0", PORT), RenderHandler)
    print(f"[HTTP] Веб-сервер на порту {PORT}", flush=True)
    httpd.serve_forever()


# --- КЛАВИАТУРЫ ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("⚠️ Сообщить о проблеме"),
        types.KeyboardButton("ℹ️ Справочная информация"),
    )
    return markup


def get_info_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📋 Документы при приеме на работу", callback_data="info_docs"),
        types.InlineKeyboardButton("🤝 Обязанности нанимателя при приеме", callback_data="info_boss"),
        types.InlineKeyboardButton("🎓 Распределение и пенсионный стаж", callback_data="info_pension"),
        types.InlineKeyboardButton("🚫 Кому не ставится испытательный срок", callback_data="info_test"),
        types.InlineKeyboardButton("🤒 Расчет больничного для новичков", callback_data="info_sick"),
        types.InlineKeyboardButton("❓ ТОП Вопросов молодых специалистов", callback_data="info_faq"),
        types.InlineKeyboardButton("📞 Контакты", callback_data="info_contacts"),
        types.InlineKeyboardButton("⚖️ Правовая база", callback_data="info_law"),
    )
    return markup


def get_back_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню", callback_data="info_back_to_menu"))
    return markup


# --- КОМАНДА СТАРТ ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)
    print(f"[START] {user_id}", flush=True)

    welcome_text = (
        "👋 Здравствуйте! Данный бот создан для сбора и оперативного решения "
        "проблемных вопросов молодых специалистов Наровлянского района.\n\n"
        "Вы можете:\n"
        "• отправить обращение — кнопка *⚠️ Сообщить о проблеме*;\n"
        "• открыть справочник — кнопка *ℹ️ Справочная информация*."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")


# --- СПРАВОЧНИК ---
@bot.message_handler(func=lambda message: message.text == "ℹ️ Справочная информация")
def send_info_menu(message):
    user_id = message.from_user.id
    user_data.pop(user_id, None)
    print(f"[INFO] {user_id}", flush=True)
    bot.send_message(
        message.chat.id,
        "📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
        reply_markup=get_info_menu(),
        parse_mode="Markdown",
    )


INFO_PAGES = {
    "docs": (
        "📋 *Документы при приёме на работу*\n\n"
        "*Основание:* ст. 26 Трудового кодекса Республики Беларусь, "
        "Указ Президента № 1 от 05.01.2024.\n\n"
        "*Обязательные документы:*\n"
        "✔️ Паспорт или ID-карта\n"
        "✔️ Трудовая книжка (при наличии)\n"
        "✔️ Диплом\n"
        "✔️ Свидетельство о направлении на работу\n"
        "✔️ Документы воинского учёта\n"
        "✔️ Медицинская справка\n"
        "✔️ Страховое свидетельство ФСЗН\n\n"
        "*Запрещено требовать:*\n"
        "▪️ Документы, не предусмотренные законодательством\n"
        "▪️ Характеристики с прежних мест работы\n"
        "▪️ Справки о жилищных условиях\n\n"
        "*Важно:* приём оформляется приказом, трудовой договор — "
        "в письменной форме (ст. 18 ТК РБ)."
    ),
    "boss": (
        "🤝 *Обязанности нанимателя при приёме*\n\n"
        "*Основание:* ст. 54, 55, 226 Трудового кодекса РБ.\n\n"
        "*Наниматель обязан:*\n"
        "✔️ Заключить трудовой договор в письменной форме\n"
        "✔️ Издать приказ о приёме на работу\n"
        "✔️ Ознакомить работника под подпись с условиями труда\n"
        "✔️ Ознакомить с коллективным договором и ПВТР\n"
        "✔️ Провести инструктаж по охране труда\n"
        "✔️ Организовать стажировку молодого специалиста\n"
        "✔️ Вести трудовую книжку\n"
        "✔️ Обеспечить условия для работы"
    ),
    "pension": (
        "🎓 *Распределение и пенсионный стаж*\n\n"
        "*Основание:* Кодекс об образовании РБ, Указ № 1 от 05.01.2024.\n\n"
        "*Сроки отработки:*\n"
        "▪️ После ВУЗа — 2 года\n"
        "▪️ После СУЗа — 1 год\n"
        "▪️ Целевое направление — по договору\n\n"
        "*Что входит в стаж:*\n"
        "✅ Очная учёба — в общий стаж\n"
        "✅ Работа по распределению — в страховой стаж (взносы ФСЗН)\n"
        "✅ Служба в армии — в срок отработки\n"
        "✅ Отпуск по уходу за ребёнком до 3 лет — в срок отработки\n\n"
        "*Освобождение от отработки* (ст. 83 Кодекса об образовании):\n"
        "▪️ По состоянию здоровья\n"
        "▪️ Переезд к супругу/супруге\n"
        "▪️ Ребёнок-инвалид\n"
        "▪️ Беременность или ребёнок до 3 лет"
    ),
    "test": (
        "🚫 *Кому не ставится испытательный срок*\n\n"
        "*Основание:* ст. 28 Трудового кодекса РБ.\n\n"
        "*Испытательный срок НЕ устанавливается:*\n"
        "▪️ Молодым специалистам по распределению (первое место работы)\n"
        "▪️ Молодым рабочим по направлению\n"
        "▪️ Лицам до 18 лет\n"
        "▪️ Беременным женщинам\n"
        "▪️ Женщинам с детьми до 3 лет\n"
        "▪️ При переводе к другому нанимателю\n"
        "▪️ При приёме на работу по конкурсу\n"
        "▪️ При срочном договоре до 2 месяцев\n"
        "▪️ Инвалидам по трудовой рекомендации\n\n"
        "*Максимальный срок:*\n"
        "▪️ До 3 месяцев — общее правило\n"
        "▪️ До 6 месяцев — для руководителей"
    ),
    "sick": (
        "🤒 *Расчёт больничного*\n\n"
        "*Основание:* Закон «О пособиях по временной нетрудоспособности», "
        "Постановление Совмина № 569, изменения от 01.07.2024.\n\n"
        "*Основные правила:*\n"
        "▪️ Первые 12 дней — 80% среднедневного заработка\n"
        "▪️ С 13-го дня — 100%\n"
        "▪️ Минимальный размер за месяц — 100% МЗП\n\n"
        "*100% с первого дня:*\n"
        "✅ Беременность и роды\n"
        "✅ Уход за ребёнком до 3 лет\n"
        "✅ Уход за больным ребёнком до 14 лет\n"
        "✅ Профзаболевание или травма на производстве\n"
        "✅ Инвалиды, участники боевых действий\n\n"
        "*Стаж:* взносы в ФСЗН должны быть уплачены за 6 месяцев до болезни."
    ),
    "faq": (
        "❓ *ТОП вопросов молодых специалистов*\n\n"
        "*1. Когда выходить на работу?*\n"
        "Как правило — с 1 августа.\n\n"
        "*2. Можно ли уволиться по собственному желанию?*\n"
        "До окончания отработки — только по уважительным причинам, "
        "перечисленным в Кодексе об образовании. Иначе — возмещение "
        "затрат на обучение.\n\n"
        "*3. Входит ли декрет в отработку?*\n"
        "Да, отпуск по уходу за ребёнком до 3 лет входит.\n\n"
        "*4. Входит ли армия в отработку?*\n"
        "Да, срочная служба включается.\n\n"
        "*5. Что делать, если нет работы по специальности?*\n"
        "Обратиться в управление по труду, занятости и соцзащите.\n\n"
        "*6. Кто платит за переезд?*\n"
        "Наниматель компенсирует расходы и выплачивает подъёмные.\n\n"
        "*7. Какие льготы?*\n"
        "▪️ Подъёмные в размере месячной зарплаты\n"
        "▪️ Компенсация переезда и провоза имущества\n"
        "▪️ Льготные кредиты на жильё\n"
        "▪️ Преимущество при распределении мест в общежитии"
    ),
    "contacts": (
        "📞 *Полезные контакты*\n\n"
        "*Управление по труду, занятости и соцзащите Наровлянского райисполкома*\n"
        "📍 г. Наровля, ул. Ленина, 1\n"
        "☎️ Уточните актуальный номер в райисполкоме.\n\n"
        "*Наровлянский районный исполнительный комитет*\n"
        "📍 г. Наровля\n\n"
        "*Профсоюзная организация*\n"
        "Обратитесь в первичную профсоюзную организацию по месту работы.\n\n"
        "*Правовая помощь:*\n"
        "▪️ Юридическая консультация района\n"
        "▪️ Бесплатная правовая помощь для отдельных категорий граждан\n\n"
        "*Экстренные службы:* 101, 102, 103"
    ),
    "law": (
        "⚖️ *Правовая база*\n\n"
        "📘 *Трудовой кодекс Республики Беларусь*\n"
        "▪️ ст. 18 — трудовой договор\n"
        "▪️ ст. 20 — запрет требовать работу не по договору\n"
        "▪️ ст. 26 — документы при приёме\n"
        "▪️ ст. 28 — испытательный срок\n"
        "▪️ ст. 54, 55 — обязанности нанимателя\n"
        "▪️ ст. 226 — инструктаж по охране труда\n\n"
        "📗 *Кодекс об образовании РБ*\n"
        "▪️ ст. 83 — освобождение от отработки\n\n"
        "📙 *Указ Президента № 1 от 05.01.2024*\n"
        "Правила приёма на работу.\n\n"
        "📕 *Постановление Минтруда № 74 от 23.08.2011*\n"
        "О стажировке молодых специалистов.\n\n"
        "📓 *Закон «О пособиях по временной нетрудоспособности»*\n"
        "и Постановление Совмина № 569."
    ),
}


@bot.callback_query_handler(func=lambda call: call.data.startswith("info_"))
def handle_info_menu_clicks(call):
    bot.answer_callback_query(call.id)
    page_key = call.data.replace("info_", "")

    if page_key == "back_to_menu":
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📚 *Памятка молодого специалиста*\n\nВыберите интересующую вас тему:",
                reply_markup=get_info_menu(),
                parse_mode="Markdown",
            )
        except Exception:
            send_info_menu(call.message)
    else:
        text_content = INFO_PAGES.get(page_key, "⚠️ Раздел находится в разработке.")
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text_content,
                reply_markup=get_back_menu(),
                parse_mode="Markdown",
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                text_content,
                reply_markup=get_back_menu(),
                parse_mode="Markdown",
            )


# --- СБОР ОБРАЩЕНИЙ ---
@bot.message_handler(func=lambda message: message.text == "⚠️ Сообщить о проблеме")
def report_issue_init(message):
    user_id = message.from_user.id
    user_data[user_id] = "waiting_for_issue"
    print(f"[REPORT] {user_id}", flush=True)
    bot.send_message(
        message.chat.id,
        "📝 Пожалуйста, подробно **опишите вашу проблему** одним сообщением. "
        "Можно приложить фото.\n\n"
        "Администрация района обязательно рассмотрит обращение.",
        parse_mode="Markdown",
    )


# --- ОБРАБОТКА ВВОДА ПОЛЬЗОВАТЕЛЯ ---
@bot.message_handler(func=lambda message: True, content_types=["text", "photo", "document"])
def handle_user_inputs(message):
    user_id = message.from_user.id
    current_state = user_data.get(user_id)
    print(f"[INPUT] {user_id} state={current_state}", flush=True)

    if current_state == "waiting_for_issue":
        try:
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(ADMIN_ID, f"☝️ Обращение от пользователя:\nID: `{user_id}`", parse_mode="Markdown")
            user_data.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                "✅ *Ваше обращение принято.*",
                reply_markup=get_main_menu(),
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"[ERR] Не удалось переслать админу: {e}", flush=True)
            bot.send_message(message.chat.id, "⚠️ Ошибка отправки. Попробуйте позже.")
    else:
        bot.send_message(
            message.chat.id,
            "Выберите действие из меню ниже.",
            reply_markup=get_main_menu(),
        )


# --- ЗАПУСК ---
if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()

    try:
        me = bot.get_me()
        print(f"[INIT] Бот: @{me.username} (id={me.id})", flush=True)

        wh = bot.get_webhook_info()
        if wh.url:
            print(f"[INIT] ⚠️ Вебхук: {wh.url} — удаляю", flush=True)
            bot.remove_webhook()
        else:
            print("[INIT] Вебхук не установлен — ок", flush=True)
    except Exception as e:
        print(f"[INIT] Ошибка проверки токена: {e}", flush=True)
        raise

    try:
        bot.set_my_commands([
            types.BotCommand("/start", "Запустить бота"),
            types.BotCommand("/help", "Помощь"),
        ])
    except Exception as e:
        print(f"[INIT] Ошибка меню команд: {e}", flush=True)

    print("[INIT] Запуск polling...", flush=True)
    bot.infinity_polling()
