"""OLX service-ad filter: freelancer offers are skipped, real vacancies kept."""
from app.sources.olx import _is_service_ad

SERVICE_ADS = [
    "Створення веб сайтів, підтримка та реклама | Створення сайту на WordPress а також OpenCart",
    "Лендинг на WordPress от 2 дней под рекламу | Заявки сразу в Telegram",
    "Розробка сайтів | OpenCart | WordPress | Google Ads",
    "Верстка сайта. Интеграция на WordPress.",
    "Создание сайтов на WordPress , программист , заказать сайт под ключ",
    "Створення та доопрацювання сайтів будь-якої складності / WordPress, OpenCart, Next.js",
    "WordPress сайт під ключ. Продаючий дизайн + SEO",
    "Розробка, доопрацювання та технічна підтримка сайтів — Bitrix, WordPress, Yii2, Laravel",
    "Веб-розробка : Інтернет-магазини, WordPress, OpenCart | Програміст на годину",
    "Створення, верстка сайту WordPress",
    "WordPress Вінниця: сайти під ключ, ремонт і підтримка",
    "Розробка сайтів 1-3 дні, WordPress, Хорошоп, Tilda, Weblium",
    "Готовый сайт для приватної медичної клініки (WordPress) — Повноцінний проект під ключ",
]

REAL_JOBS = [
    "Middle/Senior Full-Stack Python Engineer (Django)",
    "Нужен разработчик чат-ботов на Питоне",
    "AI-тестировщик / AI-ассистент",
    "Технічний спеціаліст проектної команди (WordPress / OpenCart)",
    "WordPress розробник у веб-студію",
    "Верстальник (Front-end developer)",
    "Потрібен програміст на годину для великого проєкту",
    "Шукаємо розробника інтернет-магазину",
]


def test_service_ads_filtered():
    for title in SERVICE_ADS:
        assert _is_service_ad(title), f"should be filtered: {title}"


def test_real_jobs_kept():
    for title in REAL_JOBS:
        assert not _is_service_ad(title), f"should be kept: {title}"
