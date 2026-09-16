"""Paperhandel — fejkat startkapital (100 000 kr), riktiga kurser.

Ett eget litet konto, helt separat från forskningsdatabasen. Köp/sälj är
manuella beslut ni själva tar — Noel väljer ingenting automatiskt och det här
är inte en rekommendation, bara ett sätt att öva på och följa upp de bolag
radarn/signalerna lyfter fram."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import _paper
from _data import latest_prices_all, market_radar, security_list

st.title("💼 Paperhandel")
st.caption(
    "Fejkade pengar, riktiga kurser (senaste stängning). Helt separat databas — "
    "påverkar aldrig forskningsdatan eller Discovery Score. Inte en rekommendation."
)

names = security_list().set_index("security_id")["name"].to_dict()
prices = latest_prices_all()
acct = _paper.summary(prices)

# ------------------------------------------------------------------- header
c1, c2, c3, c4 = st.columns(4)
c1.metric("Totalt värde", f"{acct['total_value']:,.0f} kr".replace(",", " "))
c2.metric("Kassa", f"{acct['cash']:,.0f} kr".replace(",", " "))
c3.metric("Positioner (marknadsvärde)", f"{acct['positions_value']:,.0f} kr".replace(",", " "))
pnl = acct["total_pnl"]
pnl_pct = acct["total_pnl_pct"]
c4.metric(
    "Totalt resultat",
    f"{pnl:+,.0f} kr".replace(",", " "),
    f"{pnl_pct * 100:+.1f} %" if pnl_pct is not None else None,
)
if acct["n_trades"] == 0:
    st.info(f"Inga affärer än. Startkapital: {acct['starting_capital']:,.0f} kr.".replace(",", " "))

st.divider()

# ------------------------------------------------------------------- köp
st.subheader("Köp")
radar = market_radar(segment="alla")
prefill = st.session_state.pop("paper_prefill", None)

if radar.empty:
    st.warning("Ingen radardata att välja bolag från.")
else:
    radar = radar.sort_values("Discovery", ascending=False, na_position="last").reset_index(drop=True)
    options = radar["security_id"].tolist()

    def _fmt(sid: int) -> str:
        row = radar[radar["security_id"] == sid].iloc[0]
        sc = row["Discovery"]
        sc_txt = f"{sc:.0f}" if pd.notna(sc) else "–"
        return f"{row['Bolag']} — Discovery {sc_txt} · {row['Fas']}"

    default_idx = options.index(prefill) if prefill in options else 0
    bc1, bc2 = st.columns([3, 2])
    sid = bc1.selectbox("Bolag", options, index=default_idx, format_func=_fmt)
    price = prices.get(sid)

    if price is None:
        bc2.warning("Inget pris tillgängligt för det här bolaget.")
    else:
        amount = bc2.number_input(
            "Belopp att investera (kr)", min_value=0.0,
            max_value=float(max(acct["cash"], 0.0)), value=min(5000.0, max(acct["cash"], 0.0)),
            step=500.0,
        )
        shares = math.floor(amount / price) if price > 0 else 0
        cost = shares * price
        st.caption(
            f"Kurs nu: {price:,.2f} kr · {shares} hela aktier för {cost:,.0f} kr "
            f"(kvar i kassan efteråt: {acct['cash'] - cost:,.0f} kr)".replace(",", " ")
        )
        if st.button("Köp", type="primary", disabled=(shares <= 0 or cost > acct["cash"])):
            _paper.buy(sid, shares, price)
            st.success(f"Köpte {shares} st {names.get(sid, sid)} för {cost:,.0f} kr.".replace(",", " "))
            st.cache_data.clear()
            st.rerun()

st.divider()

# ------------------------------------------------------------------- positioner
st.subheader("Positioner")
pos = acct["positions"]
if pos.empty:
    st.caption("Inga öppna positioner.")
else:
    disp = pos.copy()
    disp["Bolag"] = disp["security_id"].map(names)
    disp["Oreal. P&L (%)"] = (disp["unrealized_pnl"] / (disp["shares"] * disp["avg_cost"])) * 100
    disp = disp.rename(columns={
        "shares": "Antal", "avg_cost": "Snittkurs", "price_now": "Kurs nu",
        "market_value": "Marknadsvärde", "unrealized_pnl": "Oreal. P&L (kr)",
    })
    st.dataframe(
        disp[["Bolag", "Antal", "Snittkurs", "Kurs nu", "Marknadsvärde",
              "Oreal. P&L (kr)", "Oreal. P&L (%)"]],
        hide_index=True, width="stretch",
        column_config={
            "Snittkurs": st.column_config.NumberColumn(format="%.2f"),
            "Kurs nu": st.column_config.NumberColumn(format="%.2f"),
            "Marknadsvärde": st.column_config.NumberColumn(format="%.0f"),
            "Oreal. P&L (kr)": st.column_config.NumberColumn(format="%+.0f"),
            "Oreal. P&L (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )

    st.markdown("**Sälj**")
    sc1, sc2 = st.columns([3, 2])
    held_options = pos["security_id"].tolist()
    hold_sid = sc1.selectbox(
        "Bolag att sälja", held_options,
        format_func=lambda s: names.get(s, s), key="sell_pick",
    )
    max_shares = float(pos[pos["security_id"] == hold_sid]["shares"].iloc[0])
    sell_price = prices.get(hold_sid)
    n_sell = sc2.number_input("Antal att sälja", min_value=1, max_value=int(max_shares),
                              value=int(max_shares), step=1)
    if sell_price is None:
        st.warning("Inget aktuellt pris för det här bolaget — kan inte sälja.")
    else:
        proceeds = n_sell * sell_price
        st.caption(f"Säljer {n_sell} st @ {sell_price:,.2f} kr = {proceeds:,.0f} kr.".replace(",", " "))
        if st.button("Sälj"):
            _paper.sell(hold_sid, n_sell, sell_price)
            st.success(f"Sålde {n_sell} st {names.get(hold_sid, hold_sid)} för {proceeds:,.0f} kr.".replace(",", " "))
            st.cache_data.clear()
            st.rerun()

st.divider()

# ------------------------------------------------------------------- historik
st.subheader("Historik")
th = _paper.trades()
if th.empty:
    st.caption("Inga affärer registrerade.")
else:
    disp = th.copy()
    disp["Bolag"] = disp["security_id"].map(names)
    disp["Sida"] = disp["side"].map({"buy": "Köp", "sell": "Sälj"})
    disp["Belopp (kr)"] = disp["shares"] * disp["price_sek"]
    disp = disp.rename(columns={"trade_date": "Datum", "shares": "Antal", "price_sek": "Kurs"})
    st.dataframe(
        disp[["Datum", "Sida", "Bolag", "Antal", "Kurs", "Belopp (kr)"]]
        .sort_values("Datum", ascending=False),
        hide_index=True, width="stretch",
        column_config={
            "Kurs": st.column_config.NumberColumn(format="%.2f"),
            "Belopp (kr)": st.column_config.NumberColumn(format="%.0f"),
        },
    )
    if acct["realized_pnl"]:
        st.caption(f"Realiserad vinst/förlust från stängda positioner: {acct['realized_pnl']:+,.0f} kr".replace(",", " "))

st.divider()
with st.expander("Nollställ kontot"):
    st.caption("Tar bort alla affärer och startar om från ett nytt startkapital.")
    new_cap = st.number_input("Nytt startkapital (kr)", min_value=1000.0, value=100_000.0, step=1000.0)
    confirm = st.checkbox("Jag vill verkligen nollställa — alla affärer försvinner.")
    if st.button("Nollställ", disabled=not confirm):
        _paper.reset(new_cap)
        st.cache_data.clear()
        st.success("Kontot nollställt.")
        st.rerun()
