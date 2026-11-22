"""Одноразовый скрипт: отправляет в Telegram утреннюю сводку или напоминание об уроке.
Запускается по расписанию в GitHub Actions. Ничего устанавливать не нужно."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
CRON = os.environ.get("SCHEDULE_CRON", "")      # пусто = ручной запуск (тест)
DRY_RUN = os.environ.get("DRY_RUN") == "1"

TZ = timezone(timedelta(hours=7))                # Красноярск, UTC+7
LAT, LON = 53.89, 92.68
REMIND_MIN, REMIND_MAX = 10, 15                  # напоминаем за 10–15 минут до урока

T = {1: "08:00", 2: "08:50", 3: "09:50", 4: "10:50", 5: "11:50",
     6: "12:40", 7: "13:30", 8: "14:20", 9: "15:10"}

# 0 = понедельник ... 4 = пятница. (время начала, предмет)
SCHEDULE = {
    0: [(T[1], "РОВ"), (T[2], "Алгебра"), (T[3], "Русский язык"),
        (T[4], "Физика"), (T[5], "Алгебра (углубл.)"), (T[6], "Химия"),
        (T[7], "Английский язык"), (T[8], "Физическая культура")],
    1: [(T[1], "Геометрия"), (T[2], "Геометрия (углубл.)"), (T[3], "Русский язык"),
        (T[4], "История"), (T[5], "ОБЗР"), (T[6], "Английский язык"),
        (T[7], "География"), (T[8], "Информатика (ф)")],
    2: [(T[1], "Алгебра"), (T[2], "Русский язык"), (T[3], "Информатика"),
        (T[4], "Литература"), (T[5], "Труд (технология)"), (T[6], "Физика"),
        (T[7], "Биология")],
    3: [(T[1], "Россия — мои горизонты / Математика (ф)"), (T[2], "Геометрия"),
        (T[3], "Русский язык (ОГЭ) (ф)"), (T[4], "Химия"), (T[5], "Литература"),
        (T[6], "Английский язык"), (T[7], "Вероятность и статистика"),
        (T[8], "Физическая культура")],
    4: [(T[1], "Алгебра"), (T[2], "Физика"), (T[3], "История"),
        (T[4], "Биология"), (T[5], "Обществознание"), (T[6], "Литература"),
        (T[7], "География")],
}
DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def send(text):
    if DRY_RUN:
        print(text)
        return
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=20).read()


def day_text(day):
    lessons = SCHEDULE.get(day, [])
    if not lessons:
        return f"{DAYS[day]}: уроков нет 🎉"
    lines = [f"{DAYS[day]}:"]
    for i, (start, name) in enumerate(lessons, 1):
        lines.append(f"{i}. {start} — {name}")
    return "\n".join(lines)


def advice(tmin, tmax, rain, wind):
    t = (tmin + tmax) / 2
    if t < -20:
        s = "Очень сильный мороз: пуховик, шапка, шарф, варежки, тёплая обувь, закрой лицо."
    elif t < -10:
        s = "Сильный мороз: пуховик, шапка, шарф, перчатки, тёплая обувь."
    elif t < 0:
        s = "Мороз: зимняя куртка, шапка, перчатки."
    elif t < 8:
        s = "Холодно: тёплая куртка, шапка или капюшон."
    elif t < 15:
        s = "Прохладно: лёгкая куртка или толстовка."
    elif t < 22:
        s = "Комфортно: футболка и лёгкая кофта на вечер."
    else:
        s = "Жарко: лёгкая одежда, вода и головной убор."
    if rain >= 50:
        s += " ☔ Возьми зонт."
    if wind >= 30:
        s += " 💨 Сильный ветер — лучше что-то непродуваемое."
    return s


def weather_text():
    try:
        q = urllib.parse.urlencode({
            "latitude": LAT, "longitude": LON, "timezone": "auto", "forecast_days": 1,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
        })
        with urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?" + q, timeout=20) as r:
            d = json.load(r)["daily"]
        tmin, tmax = d["temperature_2m_min"][0], d["temperature_2m_max"][0]
        rain, wind = d["precipitation_probability_max"][0], d["wind_speed_10m_max"][0]
        return (f"🌡 {tmin:.0f}…{tmax:.0f}°C, осадки {rain}%, ветер до {wind:.0f} км/ч\n"
                f"👕 {advice(tmin, tmax, rain, wind)}")
    except Exception:
        return "Не получилось узнать погоду 😕"


def morning(now):
    send(f"Доброе утро! ☀️\n\n{day_text(now.weekday())}\n\n{weather_text()}")


def remind(now):
    for start, name in SCHEDULE.get(now.weekday(), []):
        h, m = map(int, start.split(":"))
        lesson = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta = (lesson - now).total_seconds() / 60
        if REMIND_MIN < delta <= REMIND_MAX:
            send(f"⏰ Скоро урок: {name} (в {start})")


if __name__ == "__main__":
    now = datetime.now(TZ)
    if CRON.startswith("*/5"):
        remind(now)
    else:
        morning(now)
