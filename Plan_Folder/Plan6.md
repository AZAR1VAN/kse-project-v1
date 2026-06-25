# Plan 6 — Test & verify (R6)

1. Запустити `pytest -q`. → *verify:* усе зелене; інакше — виправити модулі R2–R4.
2. `playwright-skill` setup: `cd <skill_dir> && npm run setup` (Chromium). → *verify:* setup успішний.
3. Запустити Streamlit у фоні; авто-детект dev-сервера хелпером скіла. → *verify:* знайдено URL.
4. Playwright-скрипт `/tmp/airalerts-shots.js`: для кожного шляху (`/`, кожна сторінка) — `page.goto`, `waitForSelector` графіка/canvas, `page.screenshot`, перевірка тексту сторінки на «Traceback»/«Error». → *verify:* 7 PNG створено, прапорців помилок немає.
5. Переглянути скріншоти (Read PNG); зафіксувати дефекти; виправити; повторити крок 4 до досягнення цілі. → *verify:* фінальні скріншоти чисті.
6. `graphify .` (one-off) для індексації при потребі навігації. → *verify:* `graphify-out/` створено (ігнориться git).
