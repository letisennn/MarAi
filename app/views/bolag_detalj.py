"""Bolag i detalj — börjar med en färdig slutsats i klartext. Siffror och grafer
ligger under, för den som vill kontrollera. Ingen rådata överst."""

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
    verdict,
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
vd = verdict(sid)

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

# =============================================================== SLUTSATS
with st.container(border=True):
    st.markdown(f"## {vd['ikon']} {vd['kategori']}")
    st.markdown(f"**{vd['slutsats']}**")

    if vd["darfor"]:
        st.markdown("**Därför:**")
        st.markdown("\n".join(f"- {x}" for x in vd["darfor"]))
    if vd["emot"]:
        st.markdown("**Det här talar emot:**")
        st.markdown("\n".join(f"- {x}" for x in vd["emot"]))
    if vd["nyckeltal"]:
        st.info(vd["nyckeltal"])

    as_of = pd.Timestamp(vd["as_of"]) if vd.get("as_of") is not None else None
    foot = "Preliminär, ovaliderad bedömning — trösklar och regelvikter är handsatta. "
    if as_of is not None:
        foot += f"Mätt {as_of:%Y-%m-%d}. "
    foot += "Beskriver nuläget mot historisk frekvens — inte en prognos."
    st.caption(foot)

# --------------------------------------------------------------- marc-signal (kompakt)
if assess.get("has_feats"):
    score, band = assess["score"], assess["band"]
    up, dn = assess.get("upside"), assess.get("downside")
    with st.container(border=True):
        c1, c2 = st.columns([3, 4])
        with c1:
            st.caption("Marc-signal (preliminär, ovaliderade vikter)")
            st.markdown(f"### {score:.0f} / 100 — {band}")
            st.progress(min(max(score / 100, 0.0), 1.0))
        with c2:
            st.caption(f"Historiskt rörelsespann inom ~4 mån — {assess['range_basis']}")
            if up is not None and dn is not None:
                st.markdown(f"### {up:+.0%} &nbsp;/&nbsp; {dn:+.0%}")
                st.caption("median möjlig upp / ned för bolag i det här läget — beskrivande, inte prognos")

# =============================================================== bakgrund (utfällbart)
with st.expander("Vad som ligger bakom slutsatsen — delpoäng och mätvärden"):
    if assess.get("has_feats"):
        st.markdown("**Delpoäng** (varje del jämförd med övriga bolag i universumet just nu, 0–100)")
        for c in assess["components"]:
            st.markdown(f"**{c['label']}**  ·  {c['score']:.0f} / 100  ·  vikt {c['weight']:.0%}")
            st.progress(min(max(c["score"] / 100, 0.0), 1.0))
            st.caption(c["detail"])
        st.divider()

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
        st.markdown(f"**Läget just nu, i klartext** (mätt {pd.Timestamp(obs_date):%Y-%m-%d})")
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

    if feats and has_attention():
        st.divider()
        st.markdown("**Uppmärksamhet — sök, forum, nyheter**")
        at = security_attention(sid)
        if not at.empty and "Sökintresse" in at.columns:
            st.caption("Sökintresse över tid (0–100, ungefär som Google Trends)")
            st.line_chart(at.set_index("session_date")[["Sökintresse"]], height=200)
            counts = [c for c in ["Foruminlägg/vecka", "Nyhetsrubriker/vecka"] if c in at.columns]
            if counts:
                st.caption("Foruminlägg och nyhetsrubriker per vecka")
                st.line_chart(at.set_index("session_date")[counts], height=160)
        st.caption(
            "Syntetisk attention-data — inte riktig Google Trends / forum ännu, och "
            "**inte** konstruerad att leda kursen."
        )

# =============================================================== mönster
st.subheader("Förregistrerade mönster")
st.caption(
    "Ett mönster som lyser = bolaget matchar villkoren just den veckan. Siffrorna är "
    "historiska frekvenser i hela panelen — beskrivande, inte en prognos. Mönstren är inte bevisade."
)

stats_all = rule_outcome_stats()
for rk, meta in RULE_SV.items():
    sub = hist[hist["rule"] == rk] if not hist.empty else pd.DataFrame()
    last = sub["_d"].max() if not sub.empty else None
    fires_now = bool(last is not None and obs_date is not None and last == pd.Timestamp(obs_date))

    with st.container(border=True):
        if fires_now:
            st.markdown(f"**🔆 Lyser nu** — {meta['titel']}")
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
        "Justerad kurs = räknad bakåt för splittar och utdelningar. Rå kurs = vad som "
        "faktiskt handlades. Data: Yahoo Finance, dagsupplösning."
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
