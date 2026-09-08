"""Bolag i detalj — en läsbar genomgång: sammanfattning, läget nu, mönster, kurs."""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from _data import (
    COUNTRY_SV,
    EVENT_SHORT,
    RULE_SV,
    feature_label,
    fmt_feature,
    interpret_feature,
    rule_outcome_stats,
    screener,
    security_corporate_actions,
    security_features_latest,
    security_list,
    security_listing_history,
    security_overview,
    security_prices,
    security_signal_history,
)

st.title("Bolag i detalj")

secs = security_list()
names = secs["name"].tolist()
pre = st.session_state.get("sel_security")
if pre not in names:
    sc = screener()
    cand = sc[(sc["segment"] == "small") & sc["obs_date"].notna()]
    pre = str(cand.iloc[0]["name"]) if not cand.empty else names[0]
pick = st.selectbox("Välj bolag", names, index=names.index(pre) if pre in names else 0)
st.session_state["sel_security"] = pick
sid = int(secs.loc[secs["name"] == pick, "security_id"].iloc[0])

ov = security_overview(sid)
obs_date, feats = security_features_latest(sid)
hist = security_signal_history(sid)

# senaste mönsterträff + lyser-nu
last_row = None
n_now = 0
if not hist.empty:
    hist = hist.assign(_d=pd.to_datetime(hist["as_of_date"]))
    last_row = hist.sort_values("_d").iloc[-1]
    if obs_date is not None:
        n_now = int((hist["_d"] == pd.Timestamp(obs_date)).sum())

# --------------------------------------------------------------- rubrikrad
cs = COUNTRY_SV.get(ov.get("country"), ov.get("country") or "—")
seg = None
if not feats:
    seg = None
else:
    sc_row = screener()
    m = sc_row[sc_row["name"] == pick]
    seg = (m["segment"].iloc[0] if not m.empty else None)
seg_word = {"small": "småbolag", "mid": "bolag som vuxit ur small cap"}.get(seg, "bolag")
mc = ov.get("market_cap_sek")
mc_txt = (
    f"{mc / 1e9:.1f} mdr SEK" if mc and mc >= 1e9
    else (f"{mc / 1e6:.0f} MSEK" if mc else "okänt börsvärde")
)
st.markdown(
    f"### {pick}\n"
    f"{ov.get('sector') or '—'} · {cs} · **{ov.get('status_sv') or '—'}** · "
    f"{seg_word}, börsvärde {mc_txt}"
)

# --------------------------------------------------------------- sammanfattning
def _summary() -> str:
    if not feats:
        return (
            f"{pick} har inte varit i universumet under studieperioden "
            f"(för litet, för lågt handlat, för kort historik, uppköpt eller i konkurs), "
            "så det finns inga mätningar att gå igenom. Kursgrafen längre ner visar ändå "
            "prishistoriken."
        )
    r3, r12 = feats.get("ret_3m"), feats.get("ret_12m")
    dist = feats.get("dist_52w_high")
    rv, rvol20, vexp = feats.get("rvol_5_60"), feats.get("rv_20d"), feats.get("vol_expansion")

    if r3 is not None and r12 is not None:
        if r3 > 0.15 and r12 > 0.15:
            trend = f"Kursen är i en tydlig uppåttrend ({r3:+.0%} på 3 månader, {r12:+.0%} på ett år)"
        elif r3 > 0 and r12 > 0:
            trend = f"Kursen är svagt uppåt ({r3:+.0%} på 3 månader, {r12:+.0%} på ett år)"
        elif r3 < 0 and r12 < 0:
            trend = f"Kursen är i en nedåttrend ({r3:+.0%} på 3 månader, {r12:+.0%} på ett år)"
        else:
            trend = f"Kursen saknar tydlig trend ({r3:+.0%} på 3 månader, {r12:+.0%} på ett år)"
    else:
        trend = "Trenden går inte att bedöma"

    pos = ""
    if dist is not None:
        if dist >= -0.05:
            pos = " och handlas vid sitt högsta på 52 veckor"
        elif dist >= -0.20:
            pos = f" och ligger {abs(dist):.0%} under årshögsta"
        else:
            pos = f" och ligger långt under årshögsta ({abs(dist):.0%})"

    if rv is None:
        vol = ""
    elif rv >= 2:
        vol = f"Handeln är kraftigt förhöjd ({rv:.1f}× det normala)"
    elif rv >= 1.3:
        vol = f"Handeln är något förhöjd ({rv:.1f}× det normala)"
    elif rv >= 0.8:
        vol = "Handeln ligger på normal nivå"
    else:
        vol = f"Handeln är låg ({rv:.1f}× det normala)"

    vlt = ""
    if rvol20 is not None:
        vlt = (
            " och kursen rör sig mycket" if rvol20 >= 0.5
            else " och kursen rör sig måttligt" if rvol20 >= 0.3
            else " och kursen är lugn"
        )
        if vexp is not None and vexp >= 1.3:
            vlt += ", med tilltagande svängningar"

    if n_now > 0:
        pat = f"**{n_now} av 3 förregistrerade mönster lyser den här veckan** (se nedan)."
    elif last_row is not None:
        titel = RULE_SV.get(last_row["rule"], {}).get("titel", last_row["rule"])
        pat = f'Inget mönster lyser just nu; senast var {last_row["_d"]:%Y-%m-%d} ("{titel}").'
    else:
        pat = "Inget av de tre förregistrerade mönstren har lyst för det här bolaget."

    s2 = (trend + pos + ". " + vol + vlt + ".").replace(" .", ".").strip()
    return s2 + "\n\n" + pat


st.markdown(_summary())

# --------------------------------------------------------------- läget just nu
if feats:
    st.subheader("Läget just nu")
    st.caption(
        f"Mätt vid senaste observationsveckan {pd.Timestamp(obs_date):%Y-%m-%d}. "
        "Rena mätningar — ingen värdering."
    )
    r3 = feats.get("ret_3m")
    r12 = feats.get("ret_12m")
    dist = feats.get("dist_52w_high")
    rv = feats.get("rvol_5_60")
    rvd = feats.get("rv_20d")
    vexp = feats.get("vol_expansion")

    def _word(val, bands):
        for lim, w in bands:
            if val is not None and val >= lim:
                return w
        return bands[-1][1]

    def _card(col, title, big, sub):
        with col, st.container(border=True):
            st.caption(title)
            st.markdown(f"#### {big}")
            st.caption(sub)

    c1, c2, c3, c4 = st.columns(4)
    _card(
        c1, "Trend",
        _word(r3, [(0.15, "Stark uppåt"), (0.0, "Svagt uppåt"), (-0.15, "Svagt nedåt"), (-99, "Nedåt")]),
        (f"kurs {r3:+.0%} / 3 mån" + (f" · {r12:+.0%} / år" if r12 is not None else ""))
        if r3 is not None else "för kort historik",
    )
    _card(
        c2, "Läge mot årshögsta",
        _word(dist, [(-0.05, "Vid toppen"), (-0.20, "Nära toppen"), (-99, "Långt under")]),
        f"{dist:+.0%} från årshögsta" if dist is not None else "–",
    )
    _card(
        c3, "Handel",
        _word(rv, [(2.0, "Kraftigt förhöjd"), (1.3, "Förhöjd"), (0.8, "Normal"), (-99, "Låg")]),
        f"{rv:.1f}× mot 60-dagssnittet" if rv is not None else "–",
    )
    _card(
        c4, "Rörlighet",
        _word(rvd, [(0.5, "Hög"), (0.3, "Måttlig"), (-99, "Lugn")]),
        (f"volatilitet {rvd:.0%}" + (" · ökar" if vexp is not None and vexp >= 1.3 else " · stabil"))
        if rvd is not None else "–",
    )

# --------------------------------------------------------------- mönster
st.subheader("Förregistrerade mönster")
st.warning(
    "Siffrorna nedan är **historiska frekvenser i hela panelen** — inte en prognos "
    "för det här bolaget. Mönstren är bestämda i förväg men **inte bevisade** bära "
    "information, och datan är syntetisk. Läs det som *vad systemet ser*, inte som köpråd."
)

stats_all = rule_outcome_stats()
for rk, meta in RULE_SV.items():
    sub = hist[hist["rule"] == rk] if not hist.empty else pd.DataFrame()
    last = pd.to_datetime(sub["as_of_date"]).max() if not sub.empty else None
    fires_now = bool(last is not None and obs_date is not None and pd.Timestamp(last) == pd.Timestamp(obs_date))

    with st.container(border=True):
        if fires_now:
            st.markdown(f"🟢 **Lyser nu** — {meta['titel']}")
        elif last is not None:
            st.markdown(f"🟡 Lyste senast {pd.Timestamp(last):%Y-%m-%d} — {meta['titel']}")
        else:
            st.markdown(f"⚪ Har aldrig lyst — {meta['titel']}")
        st.caption("Villkor: " + meta["villkor"])

        rs = stats_all[stats_all["rule"] == rk] if not stats_all.empty else pd.DataFrame()
        if rs.empty:
            st.caption("Ingen historik att utvärdera ännu.")
            continue
        n = int(rs["n"].iloc[0])
        if n < 20:
            st.caption(
                f"Bara {n} historiska träffar i panelen — för få för att säga något om utfallet."
            )
            continue

        row90 = rs[rs["horizon"] == "90d"]
        if not row90.empty:
            hit = float(row90["hit_rate"].iloc[0])
            base = float(row90["base_rate"].iloc[0])
            mmr = float(row90["med_max_ret"].iloc[0])
            mmd = float(row90["med_max_dd"].iloc[0])
            mult = hit / base if base else None
            if mult is None:
                comp = ""
            elif mult >= 1.25:
                comp = f" — ungefär {mult:.1f} gånger så ofta som normalt ({base:.0%})"
            elif mult <= 0.8:
                comp = f" — mer sällan än normalt ({base:.0%})"
            else:
                comp = f" — ungefär lika ofta som normalt ({base:.0%})"
            st.markdown(
                f"När mönstret lyst har en uppgång på **minst +50 % inom ~4 månader** "
                f"följt i **{hit:.0%}** av fallen{comp}."
            )
            st.markdown(
                f"Största rörelse inom ~4 månader efteråt (median i historiken): "
                f"upp **{mmr:+.0%}**, ned **{mmd:+.0%}**."
            )

        long_rows = []
        for _, r in rs.iterrows():
            lbl = EVENT_SHORT.get(r["horizon"], r["horizon"])
            long_rows.append({"x": lbl, "grp": "Efter signalen", "andel": r["hit_rate"]})
            long_rows.append({"x": lbl, "grp": "Normalt", "andel": r["base_rate"]})
        cdf = pd.DataFrame(long_rows)
        fig = px.bar(
            cdf, x="x", y="andel", color="grp", barmode="group",
            color_discrete_map={"Efter signalen": "#2f6fed", "Normalt": "#b7bec9"},
            labels={"andel": "andel av fallen", "x": "", "grp": ""},
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(height=290, margin=dict(l=0, r=0, t=6, b=0), legend=dict(orientation="h"))
        st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------- kurs
st.subheader("Kurshistorik")
px_df = security_prices(sid)
if px_df.empty:
    st.info("Ingen kurshistorik för det här bolaget.")
else:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04
    )
    fig.add_trace(
        go.Scatter(x=px_df["session_date"], y=px_df["adj_close_sek"],
                   name="Justerad kurs (SEK)", line=dict(width=1.5)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=px_df["session_date"], y=px_df["close_local"],
                   name="Rå kurs (lokal)", line=dict(width=1, dash="dot"), opacity=0.4),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=px_df["session_date"], y=px_df["volume"], name="Volym", marker_color="#9aa7b0"),
        row=2, col=1,
    )
    fig.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Justerad kurs = räknad bakåt för splittar och utdelningar, så trenden går att "
        "jämföra över tid. Rå kurs = vad som faktiskt handlades."
    )

# --------------------------------------------------------------- rådata (dolt)
with st.expander("Alla mätvärden vid senaste veckan"):
    if not feats:
        st.write("Inga mätningar.")
    else:
        order = [
            "ret_1w", "ret_1m", "ret_3m", "ret_6m", "ret_12m", "dist_52w_high",
            "breakout_20d", "rvol_5_60", "rvol_20_200", "vol_accel", "vol_trend_60d",
            "rv_20d", "rv_60d", "vol_expansion", "gap_freq_20d", "amihud_20d",
            "log_mktcap", "log_price_local",
        ]
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Mått": feature_label(k),
                        "Värde": fmt_feature(k, feats[k]),
                        "I klartext": interpret_feature(k, feats[k]),
                    }
                    for k in order if k in feats
                ]
            ),
            hide_index=True,
            width="stretch",
        )

with st.expander("Mätvärden vid varje mönsterträff"):
    if hist.empty:
        st.write("Inga mönsterträffar.")
    else:
        raw = hist.copy()
        raw["Datum"] = raw["_d"].dt.strftime("%Y-%m-%d")
        raw["Avk. 20 dgr (%)"] = (raw["ret_20d"] * 100).round(1)
        raw["Avk. 90 dgr (%)"] = (raw["ret_90d"] * 100).round(1)
        raw["Mätvärden"] = raw["feature_snapshot"].apply(
            lambda s: ", ".join(
                f"{k}={v}" for k, v in (json.loads(s) if s else {}).items() if v is not None
            )
        )
        st.dataframe(
            raw[["Datum", "rule", "Avk. 20 dgr (%)", "Avk. 90 dgr (%)", "Mätvärden"]]
            .rename(columns={"rule": "Mönster"}),
            hide_index=True,
            width="stretch",
        )

with st.expander("Bolagshändelser och noteringshistorik"):
    st.caption("Splittar, utdelningar, avnotering")
    st.dataframe(
        security_corporate_actions(sid).rename(
            columns={
                "action_type": "Typ", "ex_date": "X-datum", "ratio": "Kvot",
                "cash_amount": "Belopp", "currency": "Valuta", "source": "Källa",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption("Noteringshistorik")
    st.dataframe(
        security_listing_history(sid).rename(
            columns={
                "status": "Status", "market_segment": "Lista",
                "valid_from": "Från", "valid_to": "Till", "reason": "Orsak",
            }
        ),
        hide_index=True,
        width="stretch",
    )
