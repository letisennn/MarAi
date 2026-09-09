"""Signal Lab — testa en enkel signal mot en target: signalgrupp vs kontrollgrupp,
träffgrad, medianavkastning, relativ lift och bootstrap-KI. Forskningsverktyget
bakom Noel AI."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import q, signal_lab

st.title("🧪 Signal Lab")
st.caption(
    "Välj en signal (feature + tröskel) och en target. Noel räknar hur ofta targeten "
    "inträffade i signalgruppen jämfört med kontrollgruppen (alla andra observationer). "
    "Rent beskrivande — säger inte 'statistiskt signifikant' om testet inte visar det."
)

FEATS = {
    "rvol_5_60": "Relativ volym (5d/60d)",
    "vol_accel": "Volymacceleration",
    "ret_1m": "Kursmomentum 1 mån",
    "ret_3m": "Kursmomentum 3 mån",
    "dist_52w_high": "Avstånd till årshögsta",
    "breakout_20d": "Ny 20-dagarshögsta (0/1)",
    "search_accel": "Attention-acceleration, sök (syntetisk)",
    "forum_accel": "Forum-acceleration (syntetisk)",
    "search_level_z": "Sök-nivå, z (syntetisk)",
}
TARGETS = {
    "up_10_5d": "+10 % inom 5 dagar",
    "up_25_20d": "+25 % inom 20 dagar",
    "up_50_30d": "+50 % inom 30 dagar",
    "up_50_60d": "+50 % inom 60 dagar",
    "up_50_90d": "+50 % inom 90 dagar",
    "up_100_180d": "+100 % inom 180 dagar",
}

c1, c2 = st.columns(2)
feat = c1.selectbox("Signal (feature)", list(FEATS), format_func=lambda k: FEATS[k])
op = c1.radio("Villkor", [">=", "<="], horizontal=True)
default_thr = {"rvol_5_60": 2.0, "vol_accel": 0.0, "ret_1m": 0.15, "ret_3m": 0.25,
               "dist_52w_high": -0.05, "breakout_20d": 1.0, "search_accel": 0.20,
               "forum_accel": 0.20, "search_level_z": 1.5}.get(feat, 0.0)
thr = c1.number_input("Tröskel", value=float(default_thr), step=0.05, format="%.2f")

target = c2.selectbox("Target", list(TARGETS), index=4, format_func=lambda k: TARGETS[k])
segment = c2.radio("Universum", ["small", "mid", "alla"], horizontal=True)
yrs = q("SELECT min(obs_date) lo, max(obs_date) hi FROM observation")
lo, hi = pd.to_datetime(yrs.iloc[0]["lo"]).date(), pd.to_datetime(yrs.iloc[0]["hi"]).date()
period = c2.date_input("Period", value=(lo, hi), min_value=lo, max_value=hi)
start = str(period[0]) if isinstance(period, tuple) and len(period) == 2 else None
end = str(period[1]) if isinstance(period, tuple) and len(period) == 2 else None

res = signal_lab(feat, op, thr, target, segment=segment, start=start, end=end)
if res.get("n_total", 0) == 0:
    st.warning("Inga observationer matchar. Prova ett annat urval eller period.")
    st.stop()

st.subheader("Resultat")
st.markdown(
    f"Signal: **{FEATS[feat]} {op} {thr:g}**  ·  Target: **{TARGETS[target]}**  ·  "
    f"Universum: **{segment}**"
)

n_sig = res["n_signal"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Observationer totalt", f"{res['n_total']:,}".replace(",", " "))
k2.metric("Signalgrupp", f"{n_sig:,}".replace(",", " "))
k3.metric("Träffgrad signal", f"{res['hit_rate'] * 100:.1f} %" if res["hit_rate"] is not None else "—")
k4.metric("Basnivå (alla)", f"{res['base_rate'] * 100:.1f} %")

k5, k6, k7 = st.columns(3)
k5.metric("Kontrollgrupp", f"{res['control_hit_rate'] * 100:.1f} %" if res["control_hit_rate"] is not None else "—")
k6.metric("Relativ lift", f"{res['lift']:.2f}×" if res["lift"] else "—")
if res["median_ret_signal"] is not None:
    k7.metric("Median-avkastning signal", f"{res['median_ret_signal'] * 100:+.1f} %")

ci = res.get("ci95_hit")
if ci:
    base = res["base_rate"]
    inside = ci[0] <= base <= ci[1]
    st.markdown(
        f"**95 %-KI för signalgruppens träffgrad:** {ci[0] * 100:.1f} – {ci[1] * 100:.1f} % "
        f"(bootstrap, 2000 dragningar)."
    )
    if n_sig < 30:
        st.warning(f"Bara {n_sig} observationer i signalgruppen — för få för en pålitlig slutsats.")
    elif inside:
        st.info("KI:t rymmer basnivån → **preliminärt samband, ej statistiskt säkerställt.**")
    elif ci[0] > base:
        st.success("Hela KI:t ligger över basnivån → signalgruppen träffar oftare än normalt "
                   "i det här urvalet. Behöver bekräftas out-of-sample.")
    else:
        st.info("Hela KI:t ligger under basnivån → signalen är förknippad med **lägre** träffgrad här.")
else:
    st.caption("För få observationer för bootstrap-KI.")

st.caption(
    "Detta är in-sample beskrivande statistik. Ett verkligt fynd kräver test på en "
    "avskild period (kronologisk out-of-sample) och korrektion för multipel testning."
)
