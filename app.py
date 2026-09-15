import os
from datetime import datetime
import streamlit as st
import pandas as pd

from config import APP_NAME, DISCLAIMER
from engine import SetupInput, evaluate_setup
from journal import save_setup, get_trades, init_db, update_outcome, journal_stats
from market_data import get_all_timeframes, get_latest_price, MarketDataError
from technical import analyze_market, detect_live_signal
from macro import get_macro_events, assess_macro_risk, NY
from news import get_official_headlines
from analytics import analyze_all_advanced, session_context, confluence_score
from planner import build_trade_plan
from global_news import fetch_global_gold_news, aggregate_news_bias
from backtest import quick_trend_backtest

st.set_page_config(page_title=f"{APP_NAME} V4", layout="wide")
init_db()

st.title(f"🎯 {APP_NAME} — V4 PRO")
st.caption("XAU/USD · Técnico + Macro + Noticias globales + Plan operativo + Estadística")

with st.sidebar:
    st.header("Configuración")
    try:
        secret_key=st.secrets.get("TWELVE_DATA_API_KEY","")
    except Exception:
        secret_key=""
    api_key=st.text_input("Twelve Data API key", value=secret_key or os.getenv("TWELVE_DATA_API_KEY",""), type="password")
    balance=st.number_input("Capital para cálculo de riesgo", min_value=0.0, value=1000.0, step=100.0)
    risk_pct=st.number_input("Riesgo por operación (%)", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
    contract_size=st.number_input("Contract size XAUUSD", min_value=1.0, value=100.0, step=1.0,
                                  help="Valor típico: 100 oz por lote, pero CONFÍRMALO con tu broker.")
    refresh=st.button("🔄 Actualizar todo", use_container_width=True)
    st.caption("El lotaje es una estimación; verifica contract size, divisa y especificaciones del broker.")

tabs=st.tabs(["Centro de mando","Macro","Noticias globales","Plan & Riesgo","Backtest","Diario","Manual","Reglas"])

def load_macro():
    ev=get_macro_events(days_ahead=30)
    return ev, assess_macro_risk(ev)

if refresh or "macro_state" not in st.session_state:
    ev,risk=load_macro()
    st.session_state["macro_state"]={"events":ev,"risk":risk}

events=st.session_state["macro_state"]["events"]
macro_risk=st.session_state["macro_state"]["risk"]

if refresh or "global_news" not in st.session_state:
    st.session_state["global_news"]=fetch_global_gold_news(25,"6h")
global_news=st.session_state.get("global_news",[])
global_bias=aggregate_news_bias(global_news)

if api_key and (refresh or "market_bundle" not in st.session_state):
    try:
        with st.spinner("Leyendo XAU/USD y calculando contexto..."):
            candles=get_all_timeframes(api_key,outputsize=300)
            basic=analyze_market(candles)
            advanced=analyze_all_advanced(candles)
            latest=get_latest_price(candles)
            signal,bias,bias_score,reasons=detect_live_signal(basic)
            score,score_reasons=confluence_score(basic,advanced,macro_risk,global_bias)
            st.session_state["market_bundle"]={
                "candles":candles,"basic":basic,"advanced":advanced,"latest":latest,
                "signal":signal,"bias":bias,"reasons":reasons,
                "score":score,"score_reasons":score_reasons,
            }
    except (MarketDataError,ValueError) as exc:
        st.error(str(exc))

bundle=st.session_state.get("market_bundle")

with tabs[0]:
    st.subheader("Centro de mando")
    session_name,session_note=session_context(datetime.now(NY))
    if not bundle:
        st.info("Introduce tu API key y pulsa «Actualizar todo».")
    else:
        final=bundle["signal"]
        if macro_risk.blocked:
            final="NO TRADE"
        elif macro_risk.level == "HIGH" and final not in ("WAIT","NO TRADE"):
            final="WAIT"

        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("XAU/USD",f"{bundle['latest']:.2f}")
        c2.metric("Sesgo",bundle["bias"])
        c3.metric("Score calidad",f"{bundle['score']}/100")
        c4.metric("Macro",macro_risk.level)
        c5.metric("DECISIÓN",final)

        if bundle["score"]>=68 and ("READY" in final):
            st.success("🚨 A+ SETUP — candidato operativo con confluencia alta.")
        elif "READY" in final:
            st.success("✅ ENTRY READY — hay candidato operativo. Revisar Plan & Riesgo.")
        elif "WATCH" in final:
            st.warning("👀 WATCH — setup naciendo. Esperar gatillo/retest sin perderlo de vista.")
        elif final=="NO TRADE":
            st.error("🚫 NO TRADE — filtro de riesgo activo.")
        elif final=="WAIT":
            st.warning("⏳ WAIT — falta confirmación suficiente.")

        st.markdown(f"**Sesión:** {session_name} — {session_note}")

        rows=[]
        for tf in ["M1","M5","M15","H1","H4"]:
            b=bundle["basic"][tf]; a=bundle["advanced"][tf]
            rows.append({
                "TF":tf,"Tendencia":b.trend,"Estructura":b.structure,"Sweep":b.sweep,
                "Régimen":a.regime,"Volatilidad":a.volatility,"ATR":a.atr,"Cierre":b.last_close
            })
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        st.markdown("#### Por qué tiene ese score")
        for r in bundle["score_reasons"]:
            st.write("•",r)
        st.caption("El score mide calidad interna, NO probabilidad estadística de ganar.")

with tabs[1]:
    st.subheader("Macro")
    a,b=st.columns(2)
    a.metric("Riesgo macro",macro_risk.level)
    b.metric("Bloqueo","SÍ" if macro_risk.blocked else "NO")
    st.write(macro_risk.message)
    if events:
        df=pd.DataFrame([{
            "Evento":e.title,"Impacto":e.impact,
            "España":e.datetime_madrid.strftime("%d/%m/%Y %H:%M"),
            "NY":e.datetime_ny.strftime("%d/%m/%Y %H:%M"),"Fuente":e.source
        } for e in events[:30]])
        st.dataframe(df,use_container_width=True,hide_index=True)

    st.markdown("#### Fuentes oficiales")
    if refresh or "official_news" not in st.session_state:
        st.session_state["official_news"]=get_official_headlines(10)
    for h in st.session_state.get("official_news",[])[:8]:
        st.markdown(f"**{h.title}**")
        st.caption(f"{h.source} · {h.published}")

with tabs[2]:
    st.subheader("Noticias globales — GDELT")
    label={3:"MUY FAVORABLE ORO",2:"FAVORABLE ORO",0:"NEUTRAL",-2:"DESFAVORABLE ORO",-3:"MUY DESFAVORABLE ORO"}.get(global_bias,"NEUTRAL")
    st.metric("Sesgo heurístico de titulares",label)
    st.caption("Clasificación por palabras clave: sirve como contexto, no como señal autónoma.")
    if global_news:
        for h in global_news[:20]:
            icon="🟢" if h.gold_bias>0 else "🔴" if h.gold_bias<0 else "⚪"
            st.markdown(f"{icon} **{h.title}**")
            st.caption(f"{h.domain} · {h.sourcecountry} · {h.seendate} · {h.explanation}")
            if h.url: st.link_button("Abrir noticia",h.url)
            st.divider()
    else:
        st.warning("GDELT no devolvió noticias ahora mismo.")

with tabs[3]:
    st.subheader("Plan automático & Riesgo")
    if not bundle:
        st.info("Primero actualiza el mercado.")
    else:
        candidate=bundle["signal"]
        if candidate.startswith("BUY") and ("READY" in candidate or "WATCH" in candidate):
            direction="BUY"
        elif candidate.startswith("SELL") and ("READY" in candidate or "WATCH" in candidate):
            direction="SELL"
        else:
            direction=None

        if not direction:
            st.warning("No hay candidato técnico válido. La IA no fabricará entrada.")
        elif "WATCH" in candidate:
            st.warning("👀 Hay setup en formación. El plan se muestra para preparar la zona, pero aún falta gatillo de entrada.")
        else:
            plan=build_trade_plan(
                direction,bundle["latest"],bundle["basic"]["M5"],bundle["advanced"]["M5"],
                balance=balance,risk_pct=risk_pct,contract_size=contract_size
            )
            if macro_risk.blocked:
                st.error("Plan calculado solo como referencia: MACRO BLOQUEA la operación.")
            c1,c2,c3=st.columns(3)
            c1.metric("Dirección",plan.direction)
            c2.metric("Riesgo precio",plan.risk_distance)
            c3.metric("Lotaje estimado",plan.lots_estimate if plan.lots_estimate is not None else "N/D")
            st.code(f"""ZONA ENTRADA: {plan.entry_low} — {plan.entry_high}
SL: {plan.stop_loss}
TP1: {plan.tp1}   (1:2)
TP2: {plan.tp2}   (1:3)
TP3: {plan.tp3}   (1:5)

Riesgo monetario objetivo: {plan.risk_amount if plan.risk_amount is not None else 'N/D'}
Lotaje estimado: {plan.lots_estimate if plan.lots_estimate is not None else 'N/D'}
""",language="text")
            st.warning(plan.note)

with tabs[4]:
    st.subheader("Backtest rápido de referencia")
    if not bundle:
        st.info("Actualiza mercado primero.")
    else:
        result=quick_trend_backtest(bundle["candles"]["M5"],rr=3.0)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Trades",result.trades)
        c2.metric("Win rate",f"{result.win_rate}%")
        c3.metric("Net R",result.net_r)
        c4.metric("Expectancy",f"{result.expectancy_r} R")
        st.write("Wins:",result.wins,"· Losses:",result.losses,"· Peor racha:",result.max_losing_streak)
        st.info(result.note)
        if result.trades<30:
            st.warning("Muestra pequeña: no sacar conclusiones estadísticas todavía.")

with tabs[5]:
    st.subheader("Diario & Estadística")
    columns,rows=get_trades()
    stats=journal_stats()
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Cerradas",stats["closed"])
    c2.metric("Win rate",f'{stats["win_rate"]}%')
    c3.metric("Net R",stats["net_r"])
    c4.metric("Expectancy",f'{stats["expectancy_r"]} R')

    if rows:
        df=pd.DataFrame(rows,columns=columns)
        st.dataframe(df,use_container_width=True)
        csv=df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar backup CSV",csv,"pablo_xau_journal.csv","text/csv")

        st.markdown("#### Marcar resultado")
        ids=df["id"].tolist()
        trade_id=st.selectbox("Trade ID",ids)
        outcome=st.selectbox("Resultado",["WIN","LOSS","BE"])
        default_r=3.0 if outcome=="WIN" else -1.0 if outcome=="LOSS" else 0.0
        pnl_r=st.number_input("Resultado en R",value=float(default_r),step=0.25)
        if st.button("Guardar resultado"):
            update_outcome(int(trade_id),outcome,float(pnl_r))
            st.success("Resultado actualizado. Recarga para ver estadísticas.")
    else:
        st.info("Todavía no hay operaciones guardadas.")
    st.caption("Importante: el almacenamiento local de Streamlit Cloud no debe considerarse permanente. Descarga backups.")

with tabs[6]:
    st.subheader("Setup manual")
    c1,c2=st.columns(2)
    with c1:
        direction=st.selectbox("Dirección",["BUY","SELL"])
        entry=st.number_input("Entrada",min_value=0.0,value=3650.0,step=0.1)
        stop_loss=st.number_input("SL",min_value=0.0,value=3640.0,step=0.1)
        take_profit=st.number_input("TP",min_value=0.0,value=3680.0,step=0.1)
        notes=st.text_area("Notas")
    with c2:
        trend_aligned=st.checkbox("Tendencia alineada")
        liquidity_sweep=st.checkbox("Sweep")
        structure_confirmation=st.checkbox("Confirmación estructural")
        valid_entry_zone=st.checkbox("Zona válida")
        high_impact_news_near=st.checkbox("Noticia alto impacto cerca")
        price_extended=st.checkbox("Precio extendido")
    if st.button("Analizar manual",type="primary",use_container_width=True):
        try:
            setup=SetupInput(direction,entry,stop_loss,take_profit,trend_aligned,liquidity_sweep,structure_confirmation,valid_entry_zone,high_impact_news_near,price_extended,notes)
            result=evaluate_setup(setup)
            st.write(result)
            if st.button("Guardar en diario"):
                save_setup(result,notes); st.success("Guardado.")
        except ValueError as exc:
            st.error(str(exc))

with tabs[7]:
    st.subheader("Reglas V4 PRO")
    st.markdown("""
- Una operación por setup.
- No perseguir precio.
- H1/H4 contexto; M15/M5 confirmación.
- Sweep + estructura pesan más que una vela aislada.
- Macro puede vetar cualquier señal técnica.
- Noticias globales solo modifican contexto; nunca generan trade por sí solas.
- El plan automático solo aparece si existe candidato técnico.
- R:R preferente ≥ 1:3.
- Score ≥ 68 + señal READY = alerta A+, no garantía.
- Backtest rápido = baseline de investigación, no validación definitiva.
- No ejecución automática todavía.
""")
