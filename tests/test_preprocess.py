import pandas as pd

from airalerts.data import preprocess as pp


def _synthetic():
    return pd.DataFrame(
        {
            "region": ["Kyiv City", "Kyiv City", "Lvivska oblast"],
            "started_at": ["2022-03-01 10:00:00+00:00", "2022-03-03 22:30:00+00:00", "2022-03-01 05:00:00+00:00"],
            "finished_at": ["2022-03-01 10:45:00+00:00", None, "2022-03-01 05:20:00+00:00"],
            "naive": [False, True, False],
        }
    )


def test_clean_fills_missing_end_with_30min():
    df = pp.clean(_synthetic())
    assert df["started_at"].isna().sum() == 0
    assert (df["duration_min"] >= 0).all()
    # рядок з відсутнім кінцем → рівно 30 хв
    row = df[df["region"] == "Kyiv City"].sort_values("started_at").iloc[1]
    assert abs(row["duration_min"] - 30.0) < 1e-6


def test_daily_counts_continuous_and_zero_filled():
    df = pp.clean(_synthetic())
    dc = pp.daily_counts(df, "Kyiv City")
    # 2022-03-01 .. 2022-03-03 = 3 дні, безперервно, з нулем 02-го
    assert len(dc) == 3
    assert (dc.index.to_series().diff().dropna() == pd.Timedelta(days=1)).all()
    assert int(dc.sum()) == 2
    assert int(dc.iloc[1]) == 0


def test_profiles_and_regions():
    df = pp.clean(_synthetic())
    assert pp.regions(df) == ["Kyiv City", "Lvivska oblast"]
    assert len(pp.hourly_profile(df)) == 24
    assert len(pp.weekday_profile(df)) == 7
    assert pp.hour_weekday_matrix(df).shape == (7, 24)
