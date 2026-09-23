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
from _data import latest_prices_all, market_radar, security_list, tradable_securities, trade_snapshot
from _guide import paper_guide
from _notes import notes_popover
from _style import big_number, pnl_color

owner = st.session_state.get("paper_owner", _paper.DEFAULT_OWNER)
owner_label = owner.capitalize()

st.title(f"💼 Paperhandel — {owner_label}")
paper_guide()
st.caption(
    "Fejkade pengar, riktiga kurser (senaste stängning). Helt separat databas — "
    "påverkar aldrig forskningsdatan eller Discovery Score. Inte en rekommendation."
)
st.caption(
    f"👤 Du handlar just nu som **{owner_label}**. Jonas och Hugo har separata "
    "konton och startkapital — byt person i sidopanelen om det är fel."
)


def _pnl_color(v) -> str:
    if isinstance(v, float) and pd.isna(v):
        return pnl_color(None)
    return pnl_color(v)


def _style_pnl(v) -> str:
    return f"color: {_pnl_color(v)}; font-weight: 600"


def _colored_metric(label: str, kr_value, pct_value) -> None:
    color = _pnl_color(kr_value)
    kr_txt = "–" if kr_value is None or pd.isna(kr_value) else f"{kr_value:+,.0f} kr".replace(",", " ")
    pct_txt = None if pct_value is None or pd.isna(pct_value) else f"{pct_value * 100:+.1f} %"
    big_number(label, kr_txt, color, sub=pct_txt)


names = security_list().set_index("security_id")["name"].to_dict()
prices = latest_prices_all()
acct = _paper.summary(owner, prices)
all_trades = _paper.trades(owner)

_msg = st.session_state.pop("_toast_msg", None)
if _msg:
    st.toast(_msg, icon="✅")

# ------------------------------------------------------------------- header
c1, c2, c3, c4 = st.columns(4)
c1.metric("Totalt värde", f"{acct['total_value']:,.0f} kr".replace(",", " "))
c2.metric("Kassa", f"{acct['cash']:,.0f} kr".replace(",", " "))
c3.metric("Positioner (marknadsvärde)", f"{acct['positions_value']:,.0f} kr".replace(",", " "))
with c4:
    _colored_metric("Totalt resultat", acct["total_pnl"], acct["total_pnl_pct"])
if acct["n_trades"] == 0:
    st.info(f"Inga affärer än. Startkapital: {acct['starting_capital']:,.0f} kr.".replace(",", " "))

st.divider()

# ------------------------------------------------------------------- köp
st.subheader("Köp")
prefill = st.session_state.pop("paper_prefill", None)

# Alla noterade bolag med en aktuell kurs — inte bara radarns universum. Bolag
# som Climeon har fallit ur universumet (för tunn handel) men har en riktig
# kurs och ska gå att handla på papper. Radarns bolag ligger först, rankade på
# Uppbyggnadspoäng; resten alfabetiskt. Väljaren går att skriva i för att söka.
tradable = tradable_securities()
radar = market_radar(segment="alla")
radar_info: dict[int, tuple] = {}
in_radar_order: list[int] = []
if not radar.empty:
    ranked = radar.sort_values("Uppbyggnad", ascending=False, na_position="last")
    for _, r in ranked.iterrows():
        radar_info[int(r["security_id"])] = (r["Uppbyggnad"], r["Fas"])
        in_radar_order.append(int(r["security_id"]))

tradable_ids = set(tradable["security_id"].astype(int))
options = [s for s in in_radar_order if s in tradable_ids]
seen = set(options)
options += [int(s) for s in tradable["security_id"] if int(s) not in seen]

if not options:
    st.warning("Inga bolag med aktuell kurs att välja bland — är kursdatan hämtad?")
else:

    def _fmt(sid: int) -> str:
        nm = names.get(sid, str(sid))
        if sid in radar_info:
            u, fas = radar_info[sid]
            u_txt = f"{u:.0f}" if pd.notna(u) else "–"
            return f"{nm} — Uppbyggnad {u_txt} · {fas}"
        return f"{nm} — utanför radarn"

    default_idx = options.index(prefill) if prefill in options else 0
    bc1, bc2 = st.columns([3, 2])
    sid = bc1.selectbox(
        "Bolag (skriv för att söka)", options, index=default_idx, format_func=_fmt,
        key="paper_buy_pick",
    )
    if sid not in radar_info:
        bc1.caption(
            "ℹ️ Utanför Noels universum (för tunn handel eller för liten) — riktig kurs, "
            "men ingen analys. Kursen kan vara trögare och spreaden större än för radarns bolag."
        )
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
        buy_n = st.session_state.get("buy_n", 0)
        buy_note = st.text_area(
            "📝 Varför köper du?", key=f"buy_note_{buy_n}", height=90,
            placeholder="T.ex. volymen stiger medan kursen är lugn, Starkt setup — mål +8 %, stop −8 %, ~3 veckor",
        )
        st.caption("Noel sparar också automatiskt läget vid köpet: fas, volym, slutsats och nyckeltal.")
        if st.button("Köp", type="primary", disabled=(shares <= 0 or cost > acct["cash"])):
            _paper.buy(owner, sid, shares, price, note=buy_note, snapshot=trade_snapshot(sid))
            st.session_state["buy_n"] = buy_n + 1
            st.session_state["_toast_msg"] = f"Köpte {shares} st {names.get(sid, sid)} för {cost:,.0f} kr".replace(",", " ")
            st.cache_data.clear()
            st.rerun()

st.divider()

# ------------------------------------------------------------------- positioner
st.subheader("Innehav")


def _col(v: float | None, txt: str) -> str:
    return f"<span style='color:{_pnl_color(v)};font-weight:600'>{txt}</span>"


def _kr(v) -> str:
    return f"{v:,.0f} kr".replace(",", " ")


pos = acct["positions"]
if pos.empty:
    st.caption("Inga öppna innehav.")
else:
    widths = [3, 1, 1.4, 1.4, 1.8, 1.8, 1.4, 0.8]
    heads = ["Bolag", "Antal", "Snittkurs", "Kurs nu", "Marknadsvärde", "Resultat (kr)", "Resultat (%)", ""]
    for c, h in zip(st.columns(widths), heads, strict=True):
        c.caption(h)
    for _, r in pos.iterrows():
        sid_r = int(r["security_id"])
        pnl_pct = r["unrealized_pnl"] / (r["shares"] * r["avg_cost"]) if r["avg_cost"] else None
        cs = st.columns(widths, vertical_alignment="center")
        cs[0].markdown(f"**{names.get(sid_r, sid_r)}**")
        cs[1].write(f"{r['shares']:.0f}")
        cs[2].write(f"{r['avg_cost']:.2f}")
        cs[3].write(f"{r['price_now']:.2f}")
        cs[4].write(_kr(r["market_value"]))
        cs[5].markdown(_col(r["unrealized_pnl"], f"{r['unrealized_pnl']:+,.0f} kr".replace(",", " ")), unsafe_allow_html=True)
        cs[6].markdown(_col(pnl_pct, "–" if pnl_pct is None else f"{pnl_pct:+.1%}"), unsafe_allow_html=True)
        with cs[7]:
            mine = all_trades[all_trades["security_id"] == sid_r].to_dict("records")
            notes_popover(owner, mine, f"{names.get(sid_r, sid_r)} — alla dina affärer", f"p{sid_r}")

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
        sell_n = st.session_state.get("sell_n", 0)
        sell_note = st.text_area(
            "📝 Varför säljer du?", key=f"sell_note_{sell_n}", height=70,
            placeholder="T.ex. målet nått, ogiltigt-villkoret inträffade, tiden ute…",
        )
        if st.button("Sälj"):
            _paper.sell(owner, hold_sid, n_sell, sell_price, note=sell_note, snapshot=trade_snapshot(hold_sid))
            st.session_state["sell_n"] = sell_n + 1
            st.session_state["_toast_msg"] = f"Sålde {n_sell} st {names.get(hold_sid, hold_sid)} för {proceeds:,.0f} kr".replace(",", " ")
            st.cache_data.clear()
            st.rerun()

st.divider()

# ------------------------------------------------------------------- historik
st.subheader("Historik")
th = all_trades
if th.empty:
    st.caption("Inga affärer registrerade.")
else:
    disp = _paper.trades_with_pnl(th)
    disp["Bolag"] = disp["security_id"].map(names)
    disp["Sida"] = disp["side"].map({"buy": "Köp", "sell": "Sälj"})
    disp["Belopp (kr)"] = disp["shares"] * disp["price_sek"]

    recent = disp.sort_values(["trade_date", "created_at", "trade_id"], ascending=False).head(25)
    hw = [1.3, 0.9, 3, 1, 1.2, 1.6, 1.6, 1.3, 0.8]
    for c, h in zip(st.columns(hw), ["Datum", "Sida", "Bolag", "Antal", "Kurs", "Belopp", "Resultat (kr)", "Resultat (%)", ""], strict=True):
        c.caption(h)
    for _, r in recent.iterrows():
        cs = st.columns(hw, vertical_alignment="center")
        cs[0].write(str(r["trade_date"])[:10])
        cs[1].write(r["Sida"])
        cs[2].markdown(f"**{r['Bolag']}**")
        cs[3].write(f"{r['shares']:.0f}")
        cs[4].write(f"{r['price_sek']:.2f}")
        cs[5].write(_kr(r["Belopp (kr)"]))
        rp, rpp = r.get("realized_pnl"), r.get("realized_pnl_pct")
        has_r = rp is not None and not pd.isna(rp)
        cs[6].markdown(_col(rp if has_r else None, f"{rp:+,.0f} kr".replace(",", " ") if has_r else "–"), unsafe_allow_html=True)
        cs[7].markdown(_col(rpp if has_r else None, f"{rpp:+.1%}" if has_r else "–"), unsafe_allow_html=True)
        with cs[8]:
            one = all_trades[all_trades["trade_id"] == r["trade_id"]].to_dict("records")
            notes_popover(owner, one, f"{r['Bolag']} — {r['Sida'].lower()} {str(r['trade_date'])[:10]}", f"h{int(r['trade_id'])}")
    if len(disp) > 25:
        st.caption(f"Visar de 25 senaste av {len(disp)} affärer — hela historiken finns i tabellen nedan.")

    if acct["realized_pnl"]:
        rtxt = f"{acct['realized_pnl']:+,.0f} kr".replace(",", " ")
        st.markdown(
            f"Realiserad vinst/förlust från stängda positioner: {_col(acct['realized_pnl'], rtxt)}",
            unsafe_allow_html=True,
        )

    with st.expander("Hela historiken som tabell"):
        tbl = disp.rename(columns={
            "trade_date": "Datum", "shares": "Antal", "price_sek": "Kurs",
            "realized_pnl": "Resultat (kr)", "realized_pnl_pct": "Resultat (%)", "note": "Notering",
        })
        cols = ["Datum", "Sida", "Bolag", "Antal", "Kurs", "Belopp (kr)", "Resultat (kr)", "Resultat (%)", "Notering"]
        styler = (
            tbl[cols].sort_values("Datum", ascending=False)
            .style.format({
                "Antal": "{:.0f}".format,
                "Kurs": "{:.2f}".format,
                "Belopp (kr)": lambda v: f"{v:,.0f} kr".replace(",", " "),
                "Resultat (kr)": lambda v: "–" if pd.isna(v) else f"{v:+,.0f} kr".replace(",", " "),
                "Resultat (%)": lambda v: "–" if pd.isna(v) else f"{v:+.1%}",
            })
            .map(_style_pnl, subset=["Resultat (kr)", "Resultat (%)"])
        )
        st.dataframe(styler, hide_index=True, width="stretch")

st.divider()
with st.expander(f"Nollställ {owner_label}s konto"):
    st.warning(
        f"Rör **bara {owner_label}s** eget konto — {('Hugos' if owner == 'jonas' else 'Jonas')} "
        "affärer och kapital påverkas aldrig av det här (separata konton sedan 2026-09-19).",
        icon="🔒",
    )
    st.caption(f"Tar bort alla {owner_label}s affärer och startar om från ett nytt startkapital.")
    new_cap = st.number_input("Nytt startkapital (kr)", min_value=1000.0, value=100_000.0, step=1000.0)
    confirm = st.checkbox(f"Jag vill verkligen nollställa {owner_label}s konto — alla {owner_label}s affärer försvinner.")
    if st.button(f"Nollställ {owner_label}s konto", disabled=not confirm):
        _paper.reset(owner, new_cap)
        st.cache_data.clear()
        st.success(f"{owner_label}s konto nollställt.")
        st.rerun()
