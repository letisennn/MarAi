"""Bolag i detalj — kurs, vad Marc mäter just nu i klartext, och mönsterhistorik."""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from _data import (
    RULE_SV,
    feature_label,
    fmt_feature,
    interpret_feature,
    screener,
    security_corporate_actions,
    security_feature_history,
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
    # förvald: mest intressanta genuina småbolaget med data (screener sorterar på antal regler, sedan börsvärde)
    sc = screener()
    cand = sc[(sc["segment"] == "small") & sc["obs_date"].notna()]
    pre = str(cand.iloc[0]["name"]) if not cand.empty else names[0]
idx = names.index(pre) if pre in names else 0
pick = st.selectbox("Välj bolag", names, index=idx)
st.session_state["sel_security"] = pick
sid = int(secs.loc[secs["name"] == pick, "security_id"].iloc[0])

ov = security_overview(sid)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Land", ov.get("country") or "—")
c2.metric("Sektor", ov.get("sector") or "—")
c3.metric("Status", ov.get("status_sv") or "—")
last_close = ov.get("close_local")
c4.metric(
    "Senaste kurs (lokal)",
    f"{last_close:,.2f}".replace(",", " ") if last_close else "—",
)

bits = []
mc = ov.get("market_cap_sek")
if mc:
    bits.append(f"Börsvärde senast **{mc / 1e6:,.0f} MSEK**".replace(",", " "))
if ov.get("first_listed_date") is not None and pd.notna(ov.get("first_listed_date")):
    bits.append(f"noterad {ov['first_listed_date']}")
if ov.get("status_date") is not None and pd.notna(ov.get("status_date")):
    bits.append(f"{str(ov['status_sv']).lower()} {ov['status_date']}")
if ov.get("n_obs"):
    bits.append(f"{ov['n_obs']} observationer {ov['obs_lo']}–{ov['obs_hi']}")
if bits:
    st.caption("  ·  ".join(bits))

# ------------------------------------------------------------------ kursgraf
px_df = security_prices(sid)
if px_df.empty:
    st.info("Ingen kurshistorik för det här bolaget.")
    st.stop()

fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04
)
fig.add_trace(
    go.Scatter(
        x=px_df["session_date"], y=px_df["adj_close_sek"],
        name="Justerad kurs (SEK)", line=dict(width=1.5),
    ),
    row=1, col=1,
)
fig.add_trace(
    go.Scatter(
        x=px_df["session_date"], y=px_df["close_local"],
        name="Rå kurs (lokal)", line=dict(width=1, dash="dot"), opacity=0.45,
    ),
    row=1, col=1,
)
fig.add_trace(
    go.Bar(x=px_df["session_date"], y=px_df["volume"], name="Volym", marker_color="#9aa7b0"),
    row=2, col=1,
)
fig.update_layout(height=460, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
st.plotly_chart(fig, width="stretch")

# --------------------------------------------------- vad Marc mäter just nu
st.subheader("Vad Marc mäter just nu")
hist = pd.DataFrame()
obs_date, feats = security_features_latest(sid)
if not feats:
    st.info("Bolaget har inga observationer — det har aldrig varit i universumet under studieperioden.")
else:
    st.caption(f"Mätt vid senaste observationsveckan: **{pd.Timestamp(obs_date):%Y-%m-%d}**")
    order = [
        "ret_1m", "ret_3m", "ret_6m", "ret_12m", "dist_52w_high",
        "rvol_5_60", "rvol_20_200", "vol_expansion", "rv_20d", "rv_60d",
        "vol_accel", "breakout_20d",
    ]
    tbl = pd.DataFrame(
        [
            {
                "Mått": feature_label(name),
                "Värde": fmt_feature(name, feats[name]),
                "I klartext": interpret_feature(name, feats[name]),
            }
            for name in order
            if name in feats
        ]
    )
    st.dataframe(tbl, hide_index=True, width="stretch")

    # ------------------------------------------------ förregistrerade mönster
    st.subheader("Förregistrerade mönster")
    st.caption(
        "Att ett mönster \"lyser\" betyder bara att bolaget matchar villkoren. "
        "Det är **inte ett köpråd**, och mönstren är ännu inte bevisade bära "
        "information (särskilt inte på syntetisk data)."
    )
    hist = security_signal_history(sid)
    for rk, meta in RULE_SV.items():
        sub = hist[hist["rule"] == rk] if not hist.empty else pd.DataFrame()
        last = pd.to_datetime(sub["as_of_date"]).max() if not sub.empty else None
        fired_latest = bool(
            last is not None and obs_date is not None
            and pd.Timestamp(last) == pd.Timestamp(obs_date)
        )
        icon = "🟢" if fired_latest else ("🟡" if last is not None else "⚪")
        with st.container(border=True):
            st.markdown(f"{icon} **{rk} — {meta['titel']}**")
            st.caption(meta["villkor"])
            if last is not None:
                tail = " — lyser den här veckan" if fired_latest else ""
                st.caption(
                    f"Senaste träff {pd.Timestamp(last):%Y-%m-%d} · "
                    f"totalt {len(sub)} träffar för det här bolaget{tail}"
                )
            else:
                st.caption("Har aldrig lyst för det här bolaget.")

    # ----------------------------------------------- historiskt utfall
    if not hist.empty:
        st.subheader("När mönster lyst förr — och vad som hände sedan")
        st.caption(
            "Realiserad avkastning efter varje träff. Historik på syntetisk data "
            "— inte en prognos."
        )
        h = hist.copy()
        h["Datum"] = pd.to_datetime(h["as_of_date"]).dt.strftime("%Y-%m-%d")
        h["Avk. 20 dgr (%)"] = (h["ret_20d"] * 100).round(1)
        h["Avk. 90 dgr (%)"] = (h["ret_90d"] * 100).round(1)
        h = h.rename(columns={"rule": "Regel"})
        st.dataframe(
            h[["Datum", "Regel", "Avk. 20 dgr (%)", "Avk. 90 dgr (%)"]],
            hide_index=True,
            width="stretch",
            column_config={
                "Avk. 20 dgr (%)": st.column_config.NumberColumn(format="%+.1f"),
                "Avk. 90 dgr (%)": st.column_config.NumberColumn(format="%+.1f"),
            },
        )

# ------------------------------------------------ bolagshändelser / notering
cc1, cc2 = st.columns(2)
with cc1:
    st.caption("Bolagshändelser (splittar, utdelningar, avnotering)")
    ca = security_corporate_actions(sid)
    st.dataframe(
        ca.rename(
            columns={
                "action_type": "Typ", "ex_date": "X-datum", "ratio": "Kvot",
                "cash_amount": "Belopp", "currency": "Valuta", "source": "Källa",
            }
        ),
        hide_index=True,
        width="stretch",
    )
with cc2:
    st.caption("Noteringshistorik")
    lh = security_listing_history(sid)
    st.dataframe(
        lh.rename(
            columns={
                "status": "Status", "market_segment": "Lista",
                "valid_from": "Från", "valid_to": "Till", "reason": "Orsak",
            }
        ),
        hide_index=True,
        width="stretch",
    )

with st.expander("Alla mått vid alla observationsdatum (rådata)"):
    wide = security_feature_history(sid)
    if wide.empty:
        st.write("Inga observationer.")
    else:
        st.dataframe(wide, width="stretch")

with st.expander("Mätvärden vid varje mönsterträff (rådata)"):
    if not hist.empty:
        raw = hist.copy()
        raw["mätvärden"] = raw["feature_snapshot"].apply(
            lambda s: ", ".join(
                f"{k}={v}" for k, v in (json.loads(s) if s else {}).items() if v is not None
            )
        )
        st.dataframe(
            raw[["as_of_date", "rule", "mätvärden"]].rename(
                columns={"as_of_date": "Datum", "rule": "Regel", "mätvärden": "Mätvärden"}
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.write("Inga mönsterträffar.")
