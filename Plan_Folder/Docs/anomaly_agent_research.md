# Дослідження: Агент аномалій / сплесків (Рівень 3)

> Виявлення аномальних діб (різкі сплески кількості тривог) у денному ряді.
> Стек: `numpy`/`pandas`, `scikit-learn` (BSD-3, не AGPL). Працює поверх залишків STL з Рівня 2.

## Метод

Два взаємодоповнювані підходи; основний — (A), опційний для крос-перевірки — (B).

**(A) Робастний z-score на залишках STL (median + MAD).**
Беремо `resid` зі STL-декомпозиції (Рівень 2) — це ряд уже без тренду й тижневої сезонності,
тож аномалія = незвично великий залишок. Класичні mean/std чутливі до самих сплесків,
тому використовуємо медіану та MAD (median absolute deviation):

```
mad = median(|resid - median(resid)|)
robust_z(t) = 0.6745 * (resid(t) - median(resid)) / mad
```

Константа `0.6745` приводить MAD до масштабу стандартного відхилення нормального розподілу.

**(B) IsolationForest на денних ознаках (sklearn).**
Багатовимірне виявлення викидів: модель ізолює аномальні дні за набором ознак
(кількість тривог, залишок STL, день тижня, тощо). Дає незалежний другий голос.

## Бібліотека/виклик

**(A) Робастний z-score:**

```python
import numpy as np
import pandas as pd

resid = stl_res.resid.dropna()           # із STL (Рівень 2)
med = resid.median()
mad = (resid - med).abs().median()
mad = mad if mad > 0 else 1e-9            # захист від ділення на нуль
robust_z = 0.6745 * (resid - med) / mad

THRESHOLD = 3.5                            # поріг (Iglewicz & Hoaglin)
# Тільки сплески (тривог більше за норму) -> однобічний поріг:
anomalies = robust_z[robust_z > THRESHOLD]
anomaly_dates = anomalies.index           # DatetimeIndex аномальних діб
```

**(B) IsolationForest:**

```python
from sklearn.ensemble import IsolationForest

feats = pd.DataFrame({
    "count":   series,
    "resid":   stl_res.resid,
    "dow":     series.index.dayofweek,
}).dropna()

iso = IsolationForest(contamination=0.02, random_state=42)
labels = iso.fit_predict(feats.values)        # -1 = аномалія, 1 = норма
scores = -iso.score_samples(feats.values)     # більший => аномальніший
iso_anomaly_dates = feats.index[labels == -1]
```

**Узгодження двох методів** (рекомендовано для UI): позначати дату як аномалію,
якщо її виявив метод (A); метод (B) — додаткова мітка `confirmed = date in iso_anomaly_dates`.

## Входи/виходи

**Входи:**
- `stl_res.resid` — залишки STL (Рівень 2), `pd.Series` денної частоти.
- `series` — вихідний денний ряд кількості тривог (для ознак IsolationForest і для звіту).

**Виходи:**
- `anomaly_dates` — `DatetimeIndex` дат-сплесків.
- Таблиця для UI: `DataFrame[date, count, resid, robust_z, severity, confirmed]`.
- `severity` (str) — категорія тяжкості (див. нижче).

## Параметри

| Параметр | Значення | Пояснення |
|---|---|---|
| `THRESHOLD` (robust z) | `3.5` | Стандартний поріг Iglewicz–Hoaglin для modified z-score. |
| напрямок | однобічний (`> THRESHOLD`) | Цікавлять саме сплески (зростання тривог), не «тихі» дні. |
| `contamination` | `0.02` | Очікувана частка аномалій (~2% днів); підбирати під дані. |
| `random_state` | `42` | Відтворюваність IsolationForest. |
| `n_estimators` | `100` (за замовч.) | Достатньо для денного ряду. |

**Вираження тяжкості (severity)** за величиною `robust_z`:

```python
def severity(z):
    if z >= 6.0:  return "критична"
    if z >= 4.5:  return "висока"
    return "помірна"            # 3.5 <= z < 4.5
```

(Альтернативно severity = `count / median(count)` — у скільки разів перевищено типову добу.)

## Критерій якості

1. **Узгодженість методів:** частка дат-сплесків з (A), підтверджених (B)
   (`confirmed=True`), має бути висока (бажано > 60%); сильні розбіжності -> переглянути
   `contambation`/`THRESHOLD`.
2. **Sanity на синтетиці:** вставити штучний пік (напр. ×5 від медіани) у тестовий ряд —
   він має потрапити в `anomaly_dates` з `severity` ≥ «висока».
3. **Стабільність частки:** при `THRESHOLD=3.5` частка аномалій має лишатися малою
   (одиниці % днів). Якщо позначено десятки % — поріг/декомпозиція невірні.
4. **Без «хибних сплесків» на пропусках:** дні, заповнені нулями (`fillna(0)`), не повинні
   масово позначатися як аномалії (перевірити, що нулі не дають великий додатний z).
