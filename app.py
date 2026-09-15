import os
import streamlit as st
import pandas as pd

from config import APP_NAME, DISCLAIMER
from engine import SetupInput, evaluate_setup
from journal import save_setup, get_trades, init_db
from market_data import get_all_timeframes, get_latest_price, MarketDataError
from technical import analyze_market, detect_live_signal
from macro import get_macro_events, assess_macro_risk
from news import get_official_headlines

st.set_page_config(page_title=f"{APP_NAME} V3", layout="wide")
init_db()

st.title(f"🎯 {APP_NAME} — V3")
st.caption("XAU/USD · Técnico + Macro · Calendario económico · Modo sniper")

with st.sidebar:
    st.header("Mercado")
    try:
        secret_key = st.secrets.get("TWELVE_DATA_API_KEY","")
    except Exception:
        secret_key = ""
    api_key = st.text_input(
        "Twelve Data API key",
        value=secret_key or os.getenv("TWELVE_DATA_API_KEY",""),
        type="password"
    )
    refresh = st.button("🔄 Actualizar análisis completo", use_container_width=True)
    st.caption("Técnico: Twelve Data · Macro: BLS + Federal Reserve")

tab_live, tab_macro, tab_news, tab_manual, tab_journal, tab_rules = st.tabs(
    ["Mercado","Macro","Noticias","Setup manual","Diario","Reglas"]
)

def load_macro():
    events = get_macro_events(days_ahead=30)
    return events, assess_macro_risk(events)

if refresh or "macro_state" not in st.session_state:
    events, risk = load_macro()
    st.session_state["macro_state"] = {"events":events,"risk":risk}

macro_state = st.session_state["macro_state"]
events = macro_state["events"]
macro_risk = macro_state["risk"]

with tab_live:
    st.subheader("Análisis XAU/USD")

    if macro_risk.blocked:
        st.error(f"🚫 MACRO BLOCK: {macro_risk.message}")
    elif macro_risk.level in ("HIGH","MEDIUM"):
        st.warning(f"⚠️ Riesgo macro {macro_risk.level}: {macro_risk.message}")
    else:
        st.success(f"📰 Riesgo macro: {macro_risk.level}")

    if macro_risk.nearest_event:
        e = macro_risk.nearest_event
        st.caption(f"Evento más cercano: {e.title} · {e.datetime_madrid.strftime('%d/%m %H:%M')} hora España")

    if not api_key:
        st.info("Falta la API key de Twelve Data para leer XAU/USD.")
    else:
        if refresh or "live_market" not in st.session_state:
            try:
                with st.spinner("Leyendo mercado..."):
                    candles = get_all_timeframes(api_key, outputsize=120)
                    analyses = analyze_market(candles)
                    latest = get_latest_price(candles)
                    signal,bias,bias_score,reasons = detect_live_signal(analyses)
                    st.session_state["live_market"] = {
                        "analyses":analyses, "latest":latest,
                        "signal":signal, "bias":bias, "reasons":reasons
                    }
            except (MarketDataError,ValueError) as exc:
                st.error(str(exc))

        live = st.session_state.get("live_market")
        if live:
            final_signal = live["signal"]
            reasons = list(live["reasons"])

            if macro_risk.blocked:
                final_signal = "NO TRADE"
                reasons.insert(0, f"Bloqueo macro: {macro_risk.message}")
            elif macro_risk.level in ("HIGH","MEDIUM") and final_signal != "WAIT":
                final_signal = "WAIT"
                reasons.insert(0, "El técnico da candidato, pero el contexto macro obliga a esperar.")

            a,b,c,d = st.columns(4)
            a.metric("XAU/USD", f"{live['latest']:.2f}")
            b.metric("Sesgo técnico", live["bias"])
            c.metric("Macro", macro_risk.level)
            d.metric("DECISIÓN", final_signal)

            rows = []
            for tf in ["M1","M5","M15","H1","H4"]:
                x = live["analyses"][tf]
                rows.append({
                    "TF":tf, "Tendencia":x.trend, "Estructura":x.structure,
                    "Sweep":x.sweep, "Momentum":x.momentum, "Cierre":x.last_close
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("### Lectura final")
            if final_signal == "NO TRADE":
                st.error("🚫 NO TRADE")
            elif final_signal == "WAIT":
                st.warning("⏳ WAIT")
            elif final_signal.startswith("BUY"):
                st.success("🟢 BUY CANDIDATE")
            else:
                st.error("🔴 SELL CANDIDATE")

            for r in reasons:
                st.write("•",r)

with tab_macro:
    st.subheader("Calendario macro relevante para oro")
    c1,c2 = st.columns(2)
    c1.metric("Riesgo actual",macro_risk.level)
    c2.metric("Trading bloqueado","SÍ" if macro_risk.blocked else "NO")
    st.write(macro_risk.message)

    if events:
        rows = []
        for e in events[:30]:
            rows.append({
                "Evento":e.title, "Impacto":e.impact,
                "España":e.datetime_madrid.strftime("%d/%m/%Y %H:%M"),
                "Nueva York":e.datetime_ny.strftime("%d/%m/%Y %H:%M"),
                "Fuente":e.source
            })
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    else:
        st.warning("No se pudieron cargar eventos oficiales.")

with tab_news:
    st.subheader("Noticias oficiales relevantes")
    if refresh or "official_news" not in st.session_state:
        st.session_state["official_news"] = get_official_headlines(15)

    headlines = st.session_state.get("official_news",[])
    if not headlines:
        st.warning("No se pudieron cargar titulares oficiales.")
    for h in headlines:
        st.markdown(f"**{h.title}**")
        st.caption(f"{h.source} · {h.published}")
        if h.link:
            st.link_button("Abrir fuente oficial",h.link)
        st.divider()

with tab_manual:
    st.subheader("Motor sniper manual")
    c1,c2 = st.columns(2)
    with c1:
        direction = st.selectbox("Dirección",["BUY","SELL"])
        entry = st.number_input("Entrada",min_value=0.0,value=3650.0,step=0.1,format="%.3f")
        stop_loss = st.number_input("Stop Loss",min_value=0.0,value=3640.0,step=0.1,format="%.3f")
        take_profit = st.number_input("Take Profit",min_value=0.0,value=3680.0,step=0.1,format="%.3f")
        notes = st.text_area("Notas")
    with c2:
        trend_aligned = st.checkbox("Tendencia alineada")
        liquidity_sweep = st.checkbox("Sweep de liquidez")
        structure_confirmation = st.checkbox("Confirmación estructural")
        valid_entry_zone = st.checkbox("Entrada en zona válida")
        high_impact_news_near = st.checkbox("⚠️ Noticia de alto impacto cercana")
        price_extended = st.checkbox("⚠️ Precio extendido / entrada perseguida")

    if st.button("Analizar setup manual",type="primary",use_container_width=True):
        try:
            result = evaluate_setup(SetupInput(
                direction,entry,stop_loss,take_profit,
                trend_aligned,liquidity_sweep,structure_confirmation,
                valid_entry_zone,high_impact_news_near,price_extended,notes
            ))
            a,b,c,d = st.columns(4)
            a.metric("Decisión",result.decision)
            b.metric("Score",result.score)
            c.metric("R:R",f"1:{result.rr}")
            d.metric("Calidad",result.quality)
            for x in result.reasons:
                st.write("•",x)
            if result.warnings:
                st.warning("\n".join(result.warnings))
            st.caption(DISCLAIMER)
            if st.button("Guardar setup"):
                save_setup(result,notes)
                st.success("Setup guardado.")
        except ValueError as exc:
            st.error(str(exc))

with tab_journal:
    st.subheader("Diario")
    columns,rows = get_trades()
    if rows:
        st.dataframe(pd.DataFrame(rows,columns=columns),use_container_width=True)
    else:
        st.info("Todavía no hay setups guardados.")

with tab_rules:
    st.subheader("Reglas V3")
    st.markdown("""
- Una operación por setup.
- No perseguir precio.
- R:R preferente ≥ 1:3.
- H1/H4 dan contexto; M5/M15 confirman.
- CPI, NFP, PPI, JOLTS y FOMC elevan el riesgo.
- FOMC tiene prioridad máxima.
- Una ventana macro bloqueada veta BUY/SELL.
- Riesgo macro medio/alto puede convertir candidato en WAIT.
- La V3 no abre operaciones automáticamente.
""")
