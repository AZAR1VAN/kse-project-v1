# Дослідження даних: Vadimkin Ukrainian Air-Raid Sirens Dataset

## Джерело та URL

- Репозиторій: https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset (ліцензія MIT, оновлюється щоденно).
- Використовуємо **волонтерські дані на рівні областей** (англомовний CSV), покриття з 2022-02-25, всі часи в **UTC**.

Підтверджені посилання для завантаження (гілка `main`):

- **Основний (волонтерський, англ.):**
  `https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/main/datasets/volunteer_data_en.csv`
- Офіційний (англ., для довідки/порівняння):
  `https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/main/datasets/official_data_en.csv`

У каталозі `datasets/` також існують україномовні варіанти (`volunteer_data_uk.csv`, `official_data_uk.csv`), але ми беремо англомовний волонтерський файл.

Завантаження перевірено через `curl -sL "<raw_url>" | head -5` — обидва файли віддаються коректно (HTTP 200, валідний CSV). Станом на 2026-06-25 у `volunteer_data_en.csv` ~101 969 рядків даних, діапазон дат: 2022-02-25 16:36:22+00:00 … 2026-06-25 00:10:21+00:00.

## Схема CSV (підтверджено)

### volunteer_data_en.csv (наш основний файл)

Точні назви колонок (header першого рядка):

```
region,started_at,finished_at,naive
```

| Колонка | Тип | Опис |
|---|---|---|
| `region` | рядок | Назва області/міста (англ. транслітерація), напр. `Kyivska oblast`, `Kyiv City`. |
| `started_at` | datetime з TZ | Час початку тривоги, формат `YYYY-MM-DD HH:MM:SS+00:00` (UTC). |
| `finished_at` | datetime з TZ | Час завершення тривоги, той самий формат (UTC). |
| `naive` | булеве (`True`/`False`) | `True`, якщо точного часу завершення не було, і `finished_at` обчислено як `started_at + 30 хвилин`. |

**Ключове правило (цитата з `datasets/README.md`):**
> "All times are in UTC." та
> "If there are no messages about the end of the sirens, you may see them with `naive=True` and `finished_at = started_at + 30 minutes`."

Тобто колонка `finished_at` **ніколи не порожня** у публікованому CSV — для невідомих завершень вона вже заповнена правилом +30 хв і позначена `naive=True`. Перевірено: 0 порожніх `finished_at`, 0 рядків де `finished_at < started_at`. Розподіл: `False` ≈ 96 946, `True` ≈ 5 023.

### official_data_en.csv (довідково)

Header:

```
oblast,raion,hromada,level,started_at,finished_at,source
```

- `oblast`, `raion`, `hromada` — адмінрівні (raion/hromada можуть бути порожні для тривог рівня області);
- `level` — `oblast` / `raion` / `hromada`;
- `source` — джерело (`official`);
- `started_at`, `finished_at` — час у форматі UTC, як вище.

## Приклад рядків

З `volunteer_data_en.csv` (header + перші рядки, без змін):

```
region,started_at,finished_at,naive
Kyiv City,2022-02-25 16:36:22+00:00,2022-02-25 17:06:22+00:00,True
Cherkaska oblast,2022-02-25 18:36:21+00:00,2022-02-25 19:32:11+00:00,False
Rivnenska oblast,2022-02-25 18:56:44+00:00,2022-02-25 19:26:44+00:00,True
Zaporizka oblast,2022-02-25 18:57:51+00:00,2022-02-25 19:27:51+00:00,True
Volynska oblast,2022-02-25 19:41:57+00:00,2022-02-26 04:01:55+00:00,False
```

Зауваження: рядок 1 (`Kyiv City`) має `naive=True` → тривалість рівно 30 хв (16:36:22 → 17:06:22). Рядок 5 (`Volynska oblast`) перетинає північ — кінець наступної доби; це слід враховувати при агрегації по днях.

### Формат назв регіонів (`region`)

25 унікальних значень, англійська транслітерація, прикметникова форма + слово `oblast`, окрім столиці (`Kyiv City`):

```
Cherkaska oblast, Chernihivska oblast, Chernivetska oblast, Dnipropetrovska oblast,
Donetska oblast, Ivano-Frankivska oblast, Kharkivska oblast, Khersonska oblast,
Khmelnytska oblast, Kirovohradska oblast, Kyiv City, Kyivska oblast,
Luhanska oblast, Lvivska oblast, Mykolaivska oblast, Odeska oblast,
Poltavska oblast, Rivnenska oblast, Sumska oblast, Ternopilska oblast,
Vinnytska oblast, Volynska oblast, Zakarpatska oblast, Zaporizka oblast,
Zhytomyrska oblast
```

Назви — чисті ASCII-рядки, без пробілів-роздільників всередині (кома в CSV не екранується спецсимволами). `Kyiv City` та `Kyivska oblast` — різні сутності.

## Препроцесинг (рецепт)

Лише `pandas` (без AGPL-залежностей), мінімально, без зайвих абстракцій.

```python
import pandas as pd

RAW_URL = ("https://raw.githubusercontent.com/Vadimkin/"
           "ukrainian-air-raid-sirens-dataset/main/datasets/volunteer_data_en.csv")

def load_alerts(source=RAW_URL):
    df = pd.read_csv(source)

    # 1. Парсинг дат як UTC-aware (формат уже містить +00:00)
    df["started_at"] = pd.to_datetime(df["started_at"], utc=True)
    df["finished_at"] = pd.to_datetime(df["finished_at"], utc=True)

    # 2. naive -> справжній bool
    df["naive"] = df["naive"].astype(bool)

    # 3. Відкидаємо невалідні рядки:
    #    - порожні started_at/finished_at (на практиці 0, але захищаємось)
    #    - finished_at < started_at
    df = df.dropna(subset=["region", "started_at", "finished_at"])
    df = df[df["finished_at"] >= df["started_at"]]

    # 4. Тривалість у хвилинах
    df["duration_min"] = (
        (df["finished_at"] - df["started_at"]).dt.total_seconds() / 60.0
    )

    # 5. Де-дуплікація точних повторів
    df = df.drop_duplicates(
        subset=["region", "started_at", "finished_at"]
    ).reset_index(drop=True)

    return df
```

Примітки:
- Часи лишаємо в UTC для агрегацій (за потреби UI може окремо конвертувати в Europe/Kyiv; для аналітичних рядів UTC достатньо і однозначно).
- `naive=True` рядки **не відкидаємо** — це валідні тривоги з оцінкою тривалості 30 хв; за бажання їх можна позначати/фільтрувати в UI.
- Очищення межі по даті (тривоги через північ) робимо лише там, де це потрібно для «тривалості на день»; для лічильників беремо дату `started_at`.

## Побудова часових рядів

Усе через `pandas`-групування над очищеним `df`. Похідні поля для групування:

```python
df["date"] = df["started_at"].dt.date              # день (за початком тривоги, UTC)
df["hour"] = df["started_at"].dt.hour              # година доби 0..23 (UTC)
df["weekday"] = df["started_at"].dt.day_name()     # день тижня (Monday..Sunday)
df["weekday_num"] = df["started_at"].dt.weekday    # 0=Mon .. 6=Sun (для сортування)
```

### 1. Кількість тривог на день
```python
count_per_day = (
    df.groupby("date").size()
      .rename("alert_count")
      .reset_index()
)
```

### 2. Кількість тривог за годиною доби (0–23)
```python
count_per_hour = (
    df.groupby("hour").size()
      .rename("alert_count")
      .reindex(range(24), fill_value=0)   # гарантуємо всі 24 години
      .reset_index()
)
```

### 3. Кількість тривог за днем тижня
```python
count_per_weekday = (
    df.groupby(["weekday_num", "weekday"]).size()
      .rename("alert_count")
      .reset_index()
      .sort_values("weekday_num")          # Mon..Sun
)
```

### 4. Кількість тривог за регіоном
```python
count_per_region = (
    df.groupby("region").size()
      .rename("alert_count")
      .reset_index()
      .sort_values("alert_count", ascending=False)
)
```

### 5. Сумарна тривалість на день (хвилини)
```python
duration_per_day = (
    df.groupby("date")["duration_min"].sum()
      .rename("total_duration_min")
      .reset_index()
)
```

Опційно (легко з тих самих групувань): «тривоги на день по регіону» через
`df.groupby(["date", "region"]).size()` для heatmap або порівняння областей.

### Технічні обмеження дотримано
- Лише `pandas`, без сторонніх AGPL-бібліотек.
- Без спекулятивних абстракцій: один `load_alerts()` + прямі `groupby` під кожен ряд.
- Усі агрегації детерміновані й однозначні (UTC, дата за `started_at`).
