# Дослідження: Агент патернів і кластеризації (Рівень 5)

> Кластеризація регіонів за профілем тривог + аналіз патерну за годинами доби.
> Стек: `scikit-learn` (BSD-3, не AGPL), `pandas`/`numpy`.

## Метод

**(A) Кластеризація регіонів (KMeans).**
Кожен регіон описуємо вектором ознак його «профілю тривог» і групуємо схожі регіони
методом KMeans. Так виявляємо групи на кшталт «прифронтові з постійними тривогами»,
«нічні», «рідкісні тилові» тощо.

Ознаки на регіон:
- `mean_daily` — середня кількість тривог за добу;
- розподіл за годиною доби — 24 ознаки (частка тривог у кожній годині 0..23, сума = 1);
- розподіл за днем тижня — 7 ознак (частка тривог по днях тижня, сума = 1).

Усього 1 + 24 + 7 = 32 ознаки. Обов'язкова **стандартизація** (`StandardScaler`),
бо `mean_daily` і частки в різних масштабах.

**(B) Патерн за годинами доби.**
Окремо (для всіх регіонів і для кожного) рахуємо погодинний розподіл і визначаємо
**пікові години** (напр. top-3 години з найбільшою часткою тривог).

## Бібліотека/виклик

**Побудова ознак (із сирого датасету Vadimkin, timestamp у UTC):**

```python
import pandas as pd
import numpy as np

# events: DataFrame з колонками ['region', 'start_ts'] (datetime, UTC) — момент початку тривоги
events["hour"] = events["start_ts"].dt.hour
events["dow"]  = events["start_ts"].dt.dayofweek

# Розподіл за годиною доби (частки), pivot region x 24:
hour_dist = (events.pivot_table(index="region", columns="hour", values="start_ts",
                                aggfunc="count", fill_value=0))
hour_dist = hour_dist.div(hour_dist.sum(axis=1), axis=0)        # нормуємо в частки

dow_dist = (events.pivot_table(index="region", columns="dow", values="start_ts",
                               aggfunc="count", fill_value=0))
dow_dist = dow_dist.div(dow_dist.sum(axis=1), axis=0)

n_days = (events["start_ts"].max() - events["start_ts"].min()).days or 1
mean_daily = events.groupby("region").size() / n_days

features = pd.concat([mean_daily.rename("mean_daily"), hour_dist, dow_dist], axis=1).fillna(0)
```

**Стандартизація + KMeans:**

```python
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

X = StandardScaler().fit_transform(features.values)

# Вибір k за silhouette (перебір малого діапазону):
best_k, best_s = None, -1
for k in range(2, 6):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    s = silhouette_score(X, km.labels_)
    if s > best_s:
        best_k, best_s = k, s

km = KMeans(n_clusters=best_k, n_init=10, random_state=42).fit(X)
features["cluster"] = km.labels_
```

**Пікові години (по всіх регіонах або по кластеру):**

```python
overall_hour = events.groupby("hour").size()
overall_hour = overall_hour / overall_hour.sum()
peak_hours = overall_hour.sort_values(ascending=False).head(3).index.tolist()  # top-3 години
```

## Входи/виходи

**Входи:**
- `events` — `DataFrame[region, start_ts]` (UTC) — окремі тривоги з датасету Vadimkin.

**Виходи:**
- `features` з колонкою `cluster` — мітка кластера для кожного регіону.
- `best_k` — обрана кількість кластерів.
- Опис кожного кластера: середній профіль (`features.groupby("cluster").mean()`),
  список регіонів, пікові години та піковий день тижня кластера.
- `peak_hours` — глобальні пікові години.

## Параметри

| Параметр | Значення | Пояснення |
|---|---|---|
| `n_clusters` (k) | `2..5`, обрати за silhouette (зазв. 3–4) | Невелика кількість зрозумілих груп. |
| `n_init` | `10` | Кілька стартів -> стабільніший результат. |
| `random_state` | `42` | Відтворюваність. |
| Scaler | `StandardScaler` | Привести ознаки до z-масштабу (обов'язково). |
| `peak_hours` | top-3 | Кількість пікових годин для звіту. |

## Опис кластерів

Для кожного кластера у звіт/UI:
1. **Розмір** — кількість регіонів.
2. **Інтенсивність** — середній `mean_daily` (висока/середня/низька).
3. **Часовий профіль** — пікові години (`argmax` по 24 ознаках) -> «нічний/денний/рівномірний».
4. **Тижневий профіль** — піковий день тижня (`argmax` по 7 ознаках).
5. **Репрезентативні регіони** — найближчі до центроїда (`km.cluster_centers_`).

## Критерій якості

1. **Silhouette score** обраного `k` має бути позитивним і помітним
   (> 0.25 — прийнятно, > 0.5 — добре). Якщо для всіх k силует ≈0 — кластери нечіткі,
   зменшити набір ознак або зафіксувати k=3 із застереженням.
2. **Збалансованість:** жоден кластер не має бути порожнім чи містити лише 1 регіон
   (інакше зменшити k).
3. **Інтерпретованість:** центроїди мають давати різні часові/тижневі профілі
   (профілі кластерів помітно відрізняються — перевірити `features.groupby("cluster").mean()`).
4. **Sanity годин:** сума погодинних часток кожного регіону = 1 (`hour_dist.sum(axis=1) ≈ 1`).
