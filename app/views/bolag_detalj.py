"""Bolag i detalj — en läsbar bedömning: poäng, uppskattat spann, varför, läget nu."""

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
    has_attention,
    interpret_feature,
    pct_vs_normal,
    rule_outcome_stats,
    screener,
    security_attention,
    security_corporate_actions,
    security_feature_history,
    security_features_latest,
    security_list,
    security_listing_history,
    security_overview,
    security_prices,
    security_signal_history,
    stock_assessment,
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
if not hist.empty:
    hist = hist.assign(_d=pd.to_datetime(hist["as_of_date"]))
assess = stock_assessment(sid)
fhist = security_feature_history(sid)

# --------------------------------------------------------------- rubrikrad
cs = COUNTRY_SV.get(ov.get("country"), ov.get("country") or "—")
sc_all = screener()
m = sc_all[sc_all["name"] == pick]
seg = m["segment"].iloc[0] if not m.empty else None
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

# --------------------------------------------------------------- bedömning
if assess.get("has_feats"):
    st.subheader("Bedömning")
    score = assess["score"]
    band = assess["band"]
    up = assess.get("upside")
    dn = assess.get("downside")

    b1, b2 = st.columns([3, 4])
    with b1, st.container(border=True):
        st.caption("Marc-signal (preliminär)")
        st.markdown(f"## {score:.0f} / 100 — {band}")
        st.progress(min(max(score / 100, 0.0), 1.0))
        st.caption("Ovaliderade vikter. Se **Varför** nedan.")
    with b2, st.container(border=True):
        st.caption(f"Historiskt rörelsespann inom ~4 månader — {assess['range_basis']}")
        if up is not None and dn is not None:
            u1, u2 = st.columns(2)
            u1.markdown(f"### {up:+.0%}")
            u1.caption("möjlig uppgång (median)")
            u2.markdown(f"### {dn:+.0%}")
            u2.caption("möjlig nedgång (median)")
        st.caption("Beskrivande historik, **inte en prognos**. Syntetisk data.")

# --------------------------------------------------------------- sammanfattning
def _summary() -> str:
    if not feats:
        return (
            f"{pick} har inte varit i universumet under studieperioden "
            "(för litet, för lågt handlat, för kort historik, uppköpt eller i konkurs), "
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

    vol = "" if rv is None else f"Handeln är {pct_vs_normal(rv)}"
    vlt = ""
    if rvol20 is not None:
        vlt = (
            " och kursen rör sig mycket" if rvol20 >= 0.5
            else " och kursen rör sig måttligt" if rvol20 >= 0.3
            else " och kursen är lugn"
        )
        if vexp is not None and vexp >= 1.3:
            vlt += ", med tilltagande svängningar"

    n_now = 0
    if not hist.empty and obs_date is not None:
        n_now = int((hist["_d"] == pd.Timestamp(obs_date)).sum())
    if n_now > 0:
        pat = f"**{n_now} av 3 förregistrerade mönster lyser den här veckan** (se nedan)."
    elif not hist.empty:
        lr = hist.sort_values("_d").iloc[-1]
        titel = RULE_SV.get(lr["rule"], {}).get("titel", lr["rule"])
        pat = f'Inget mönster lyser just nu; senast var {lr["_d"]:%Y-%m-%d} ("{titel}").'
    else:
        pat = "Inget av de tre förregistrerade mönstren har lyst för det här bolaget."

    s2 = (trend + pos + ". " + vol + vlt + ".").replace(" .", ".").strip()
    return s2 + "\n\n" + pat


st.markdown(_summary())

# --------------------------------------------------------------- varför
if assess.get("has_feats"):
    st.subheader("Varför den poängen?")
    st.caption(
        "Poängen väger fem delar. Varje del jämförs med de andra bolagen i "
        "universumet just nu (0 = svagast, 100 = starkast). Vikterna är handsatta "
        "och ovaliderade."
    )
    for c in assess["components"]:
        st.markdown(f"**{c['label']}**  ·  {c['score']:.0f} / 100  ·  vikt {c['weight']:.0%}")
        st.progress(min(max(c["score"] / 100, 0.0), 1.0))
        st.caption(c["detail"])

# --------------------------------------------------------------- läget just nu
def _own_ctx(name: str, value) -> str:
    if fhist.empty or name not in fhist.columns or value is None:
        return ""
    s = pd.to_numeric(fhist[name], errors="coerce").dropna().tail(52)
    if len(s) < 10:
        return ""
    pct = float((s < value).mean())
    if pct >= 0.92:
        return "det högsta på ett år"
    if pct <= 0.08:
        return "det lägsta på ett år"
    return f"högre än {round(pct * 10)} av 10 veckor det senaste året"


if feats:
    st.subheader("Läget just nu, i klartext")
    st.caption(f"Mätt {pd.Timestamp(obs_date):%Y-%m-%d}. Rena mätningar — ingen värdering.")

    lines = [
        ("Kursutveckling 1 månad", "ret_1m", lambda v: f"{v:+.0%}", True),
        ("Kursutveckling 3 månader", "ret_3m", lambda v: f"{v:+.0%}", True),
        ("Kursutveckling 12 månader", "ret_12m", lambda v: f"{v:+.0%}", True),
        ("Läge mot årshögsta", "dist_52w_high", lambda v: f"{v:+.0%} (0 % = vid toppen)", True),
        ("Handelsvolym mot normalt", "rvol_5_60", pct_vs_normal, False),
        ("Handeln ökar eller minskar", "vol_accel",
         lambda v: "ökar" if v > 0 else "minskar" if v < 0 else "oförändrad", False),
        ("Svängningar (volatilitet, årstakt)", "rv_20d", lambda v: f"{v:.0%}", True),
        ("Ny 20-dagarshögsta den här veckan", "breakout_20d",
         lambda v: "ja" if v and v >= 0.5 else "nej", False),
    ]
    for label, key, fmt, ctx_ok in lines:
        if key not in feats or feats[key] is None:
            continue
        ctx = _own_ctx(key, feats[key]) if ctx_ok else ""
        tail = f"  —  *{ctx}*" if ctx else ""
        st.markdown(f"**{label}:** {fmt(feats[key])}{tail}")

# --------------------------------------------------------------- uppmärksamhet
if feats and has_attention():
    st.subheader("Uppmärksamhet — sök, forum, nyheter")
    at = security_attention(sid)
    if not at.empty and "Sökintresse" in at.columns:
        st.caption("Sökintresse över tid (0–100, ungefär som Google Trends)")
        st.line_chart(at.set_index("session_date")[["Sökintresse"]], height=220)
        counts = [c for c in ["Foruminlägg/vecka", "Nyhetsrubriker/vecka"] if c in at.columns]
        if counts:
            st.caption("Foruminlägg och nyhetsrubriker per vecka")
            st.line_chart(at.set_index("session_date")[counts], height=180)

    def _lvl(z) -> str:
        if z is None:
            return "okänt"
        if z >= 1.5:
            return "mycket högt för bolaget"
        if z >= 0.5:
            return "högre än normalt"
        if z <= -0.5:
            return "lägre än normalt"
        return "på normal nivå"

    def _dir(a) -> str:
        if a is None:
            return ""
        if a >= 0.15:
            return f", och har ökat senaste månaden ({a:+.0%})"
        if a <= -0.15:
            return f", och har minskat senaste månaden ({a:+.0%})"
        return ", ungefär oförändrat senaste månaden"

    slz, sacc = feats.get("search_level_z"), feats.get("search_accel")
    fbz, facc = feats.get("forum_buzz_z"), feats.get("forum_accel")
    nrz = feats.get("news_rate_z")
    if slz is not None:
        st.markdown(f"**Sökintresse just nu:** {_lvl(slz)}{_dir(sacc)}")
    if fbz is not None:
        st.markdown(f"**Forumaktivitet just nu:** {_lvl(fbz)}{_dir(facc)}")
    if nrz is not None:
        st.markdown(f"**Nyhetsflöde just nu:** {_lvl(nrz)}")
    st.caption(
        "Syntetisk attention-data — inte riktig Google Trends / forum ännu, och "
        "**inte** konstruerad att leda kursen. Informationsvärdet mäts i E1 när "
        "riktig data kopplats in."
    )

# --------------------------------------------------------------- mönster
st.subheader("Förregistrerade mönster")
st.info(
    "Ett mönster som lyser betyder att bolaget matchar villkoren. Siffrorna är "
    "**historiska frekvenser i hela panelen** — inte en prognos, och mönstren är "
    "inte bevisade. Datan är syntetisk."
)

stats_all = rule_outcome_stats()
for rk, meta in RULE_SV.items():
    sub = hist[hist["rule"] == rk] if not hist.empty else pd.DataFrame()
    last = sub["_d"].max() if not sub.empty else None
    fires_now = bool(last is not None and obs_date is not None and last == pd.Timestamp(obs_date))

    with st.container(border=True):
        if fires_now:
            st.markdown(f"**Lyser nu** — {meta['titel']}")
        elif last is not None:
            st.markdown(f"Lyste senast {last:%Y-%m-%d} — {meta['titel']}")
        else:
            st.markdown(f"Har aldrig lyst — {meta['titel']}")
        st.caption("Villkor: " + meta["villkor"])

        rs = stats_all[stats_all["rule"] == rk] if not stats_all.empty else pd.DataFrame()
        if rs.empty:
            st.caption("Ingen historik att utvärdera ännu.")
            continue
        n = int(rs["n"].iloc[0])
        if n < 20:
            st.caption(f"Bara {n} historiska träffar i panelen — för få för att säga något om utfallet.")
            continue

        row90 = rs[rs["horizon"] == "90d"]
        if not row90.empty:
            hit = float(row90["hit_rate"].iloc[0])
            base = float(row90["base_rate"].iloc[0])
            mmr = float(row90["med_max_ret"].iloc[0])
            mmd = float(row90["med_max_dd"].iloc[0])
            mult = hit / base if base else None
            comp = (
                f" — ungefär {mult:.1f} gånger så ofta som normalt ({base:.0%})" if mult and mult >= 1.25
                else f" — mer sällan än normalt ({base:.0%})" if mult and mult <= 0.8
                else f" — ungefär lika ofta som normalt ({base:.0%})" if mult
                else ""
            )
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
        fig = px.bar(
            pd.DataFrame(long_rows), x="x", y="andel", color="grp", barmode="group",
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
        "Justerad kurs = räknad bakåt för splittar och utdelningar, så trenden går "
        "att jämföra över tid. Rå kurs = vad som faktiskt handlades."
    )

# --------------------------------------------------------------- referens (dolt)
with st.expander("Alla mätvärden vid senaste veckan (referens)"):
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
                    {"Mått": feature_label(k), "Värde": fmt_feature(k, feats[k]),
                     "I klartext": interpret_feature(k, feats[k])}
                    for k in order if k in feats
                ]
            ),
            hide_index=True,
            width="stretch",
        )

with st.expander("Mätvärden vid varje mönsterträff (referens)"):
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
            columns={"action_type": "Typ", "ex_date": "X-datum", "ratio": "Kvot",
                     "cash_amount": "Belopp", "currency": "Valuta", "source": "Källa"}
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption("Noteringshistorik")
    st.dataframe(
        security_listing_history(sid).rename(
            columns={"status": "Status", "market_segment": "Lista",
                     "valid_from": "Från", "valid_to": "Till", "reason": "Orsak"}
        ),
        hide_index=True,
        width="stretch",
    )
