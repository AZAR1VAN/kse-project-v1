# Дослідження: Агент прогнозування (Рівень 4)

> Прогноз кількості тривог на наступні N днів по регіону.
> Стек: `prophet` (MIT, не AGPL). Fallback: seasonal-naive на `pandas`/`numpy`.

## Метод

Прогнозування денного ряду кількості тривог за допомогою **Prophet** — адитивної моделі
`y(t) = trend(t) + weekly(t) + holidays(t) + noise`. Prophet добре працює «з коробки» на
денних рядах із тижневою сезонністю, стійкий до пропусків і викидів, видає інтервал довіри.

Для нашого ряду вмикаємо тижневу сезонність (`weekly_seasonality=True`), вимикаємо денну
(немає внутрішньодобових точок) і річну лишаємо авто/вимкненою (даних з 2022 достатньо для
річної, але для стабільності й швидкості — опційно).

**Fallback (seasonal-naive)** на випадок, якщо `prophet` недоступний у середовищі:
прогноз на день `t` = значення того ж дня тижня минулого тижня (`y(t-7)`). Простий,
без залежностей, з очевидним базлайном для порівняння.

## Бібліотека/виклик

**Prophet:**

```python
import pandas as pd
from prophet import Prophet

# df: колонки 'ds' (дата) та 'y' (кількість тривог за добу)
df = series.rename_axis("ds").reset_index(name="y")   # series -> DataFrame[ds, y]

m = Prophet(
    weekly_seasonality=True,
    daily_seasonality=False,
    yearly_seasonality=False,        # увімкнути, якщо потрібен річний патерн
    interval_width=0.80,             # 80% інтервал довіри
)
m.fit(df)

N = 14                                # горизонт прогнозу, днів
future = m.make_future_dataframe(periods=N, freq="D")
forecast = m.predict(future)

# Останні N рядків — власне прогноз:
result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(N)
result["yhat"] = result["yhat"].clip(lower=0)          # кількість не може бути < 0
result["yhat_lower"] = result["yhat_lower"].clip(lower=0)
```

**Fallback (seasonal-naive, period=7):**

```python
def seasonal_naive_forecast(series, N, period=7):
    last = series.iloc[-period:].values            # останній тиждень
    idx = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=N, freq="D")
    yhat = [last[i % period] for i in range(N)]
    return pd.DataFrame({"ds": idx, "yhat": yhat})
```

## Входи/виходи

**Входи:**
- `series` — денний `pd.Series` кількості тривог (один регіон), `DatetimeIndex`.
- `N` — горизонт прогнозу (за замовч. 14 днів).

**Виходи:**
- `result` — `DataFrame[ds, yhat, yhat_lower, yhat_upper]` на N майбутніх днів:
  `yhat` — точковий прогноз, `yhat_lower`/`yhat_upper` — межі інтервалу довіри (для стрічки на Plotly).
- (fallback) `DataFrame[ds, yhat]` без інтервалу.

## Параметри

| Параметр | Значення | Пояснення |
|---|---|---|
| `weekly_seasonality` | `True` | Тижневий патерн тривог. |
| `daily_seasonality` | `False` | Немає внутрішньодобових точок у денному ряді. |
| `yearly_seasonality` | `False` (опц. `True`) | Увімкнути за потреби річної динаміки; даних з 2022-02-25 достатньо. |
| `interval_width` | `0.80` | Ширина інтервалу довіри (80%). |
| `N` | `14` | Горизонт прогнозу. |
| `freq` | `"D"` | Денна частота `make_future_dataframe`. |
| seasonal-naive `period` | `7` | Сезонний лаг fallback-методу. |

Перед навчанням: гарантувати суцільну денну частоту (`series.asfreq("D").fillna(0)`),
бо Prophet ігнорує пропуски, але base-rate занижується без явних нулів.

## Критерій якості

**Бектест на останніх 14 днях (rolling holdout) + MAE.**

```python
from sklearn.metrics import mean_absolute_error

H = 14
train, test = series.iloc[:-H], series.iloc[-H:]

# Навчити модель на train, спрогнозувати H днів, порівняти з test
# (Prophet: fit(train) -> make_future_dataframe(periods=H) -> predict; беремо tail(H).yhat)
mae = mean_absolute_error(test.values, yhat_test.values)
```

1. **MAE прогнозу** на 14-денному holdout — основна метрика; звітувати в UI.
2. **Перевага над базлайном:** `MAE(Prophet) < MAE(seasonal_naive)` на тому ж holdout —
   інакше використати fallback як основну модель (Prophet не дає виграшу на цьому ряді).
3. **Покриття інтервалу:** частка фактичних значень test, що потрапили в
   `[yhat_lower, yhat_upper]`, має бути близькою до `interval_width` (≈80%).
4. **Невід'ємність:** усі `yhat`/`yhat_lower` після `clip(lower=0)` ≥ 0.
