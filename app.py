import os
import streamlit as st
import pandas as pd

from config import APP_NAME, SYMBOL, DISCLAIMER
from engine import SetupInput, evaluate_setup
from journal import save_setup, get_trades, init_db
from market_data import get_all_timeframes, get_latest_price, MarketDataError
from technical import analyze_market, derive_bias, detect_live_signal

st.set_page_config(page_title=f"{APP_NAME} V2", layout="wide")
init_db()

st.title(f"🎯 {APP_NAME} — V2")
st.caption("XAU/USD · Datos externos · Análisis multi-timeframe · Modo sniper")

with st.sidebar:
    st.header("Conexión de mercado")
    default_key = os.getenv("TWELVE_DATA_API_KEY", "")
    api_key = st.text_input(
        "Twelve Data API key",
        value=default_key,
        type="password",
        help="La clave se usa para consultar tus datos. No la compartas públicamente."
    )
    st.caption("Símbolo del feed: XAU/USD")
    refresh = st.button("🔄 Actualizar mercado", use_container_width=True)

tab_live, tab_manual, tab_journal, tab_rules = st.tabs(
    ["Mercado en vivo", "Setup manual", "Diario", "Reglas"]
)

with tab_live:
    st.subheader("Análisis automático")

    if not api_key:
        st.info(
            "Añade tu API key de Twelve Data en la barra lateral. "
            "Después pulsa «Actualizar mercado»."
        )
    else:
        if refresh or "live_market" not in st.session_state:
            try:
                with st.spinner("Leyendo XAU/USD..."):
                    candles_by_tf = get_all_timeframes(api_key, outputsize=120)
                    analyses = analyze_market(candles_by_tf)
                    latest = get_latest_price(candles_by_tf)
                    signal, bias, bias_score, reasons = detect_live_signal(analyses)
                    st.session_state["live_market"] = {
                        "candles": candles_by_tf,
                        "analyses": analyses,
                        "latest": latest,
                        "signal": signal,
                        "bias": bias,
                        "bias_score": bias_score,
                        "reasons": reasons,
                    }
            except (MarketDataError, ValueError) as exc:
                st.error(str(exc))

        live = st.session_state.get("live_market")
        if live:
            a, b, c = st.columns(3)
            a.metric("XAU/USD", f"{live['latest']:.2f}")
            b.metric("Sesgo", live["bias"])
            c.metric("Detector", live["signal"])

            st.caption(
                "El precio mostrado es el cierre de la última vela M1 recibida; "
                "no es todavía un feed tick-by-tick."
            )

            rows = []
            order = ["M1", "M5", "M15", "H1", "H4"]
            for tf in order:
                x = live["analyses"][tf]
                rows.append({
                    "TF": tf,
                    "Tendencia": x.trend,
                    "Estructura": x.structure,
                    "Sweep": x.sweep,
                    "Momentum": x.momentum,
                    "Cierre": x.last_close,
                    "Máx. reciente": x.recent_high,
                    "Mín. reciente": x.recent_low,
                })

            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("### Lectura de la IA")
            if live["signal"] == "WAIT":
                st.warning("WAIT — no hay una entrada sniper completa todavía.")
            elif live["signal"].startswith("BUY"):
                st.success("BUY CANDIDATE — candidato técnico, todavía requiere plan de entrada/SL/TP.")
            else:
                st.error("SELL CANDIDATE — candidato técnico, todavía requiere plan de entrada/SL/TP.")

            for reason in live["reasons"]:
                st.write("•", reason)

            st.caption(
                "V2 identifica contexto técnico. No ejecuta órdenes y todavía "
                "no incorpora noticias/calendario; eso llegará en V3."
            )

with tab_manual:
    st.subheader("Motor sniper manual")

    c1, c2 = st.columns(2)
    with c1:
        direction = st.selectbox("Dirección", ["BUY", "SELL"])
        entry = st.number_input("Entrada", min_value=0.0, value=3650.0, step=0.1, format="%.3f")
        stop_loss = st.number_input("Stop Loss", min_value=0.0, value=3640.0, step=0.1, format="%.3f")
        take_profit = st.number_input("Take Profit", min_value=0.0, value=3680.0, step=0.1, format="%.3f")
        notes = st.text_area("Notas")

    with c2:
        trend_aligned = st.checkbox("Tendencia alineada")
        liquidity_sweep = st.checkbox("Sweep de liquidez")
        structure_confirmation = st.checkbox("Confirmación estructural")
        valid_entry_zone = st.checkbox("Entrada en zona válida")
        high_impact_news_near = st.checkbox("⚠️ Noticia de alto impacto cercana")
        price_extended = st.checkbox("⚠️ Precio extendido / entrada perseguida")

    if st.button("Analizar setup manual", type="primary", use_container_width=True):
        try:
            setup = SetupInput(
                direction=direction,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trend_aligned=trend_aligned,
                liquidity_sweep=liquidity_sweep,
                structure_confirmation=structure_confirmation,
                valid_entry_zone=valid_entry_zone,
                high_impact_news_near=high_impact_news_near,
                price_extended=price_extended,
                notes=notes,
            )
            result = evaluate_setup(setup)

            a, b, c, d = st.columns(4)
            a.metric("Decisión", result.decision)
            b.metric("Score", result.score)
            c.metric("R:R", f"1:{result.rr}")
            d.metric("Calidad", result.quality)

            for x in result.reasons:
                st.write("•", x)
            if result.warnings:
                st.warning("\n".join(result.warnings))
            st.caption(DISCLAIMER)

            if st.button("Guardar setup"):
                save_setup(result, notes)
                st.success("Setup guardado.")
        except ValueError as exc:
            st.error(str(exc))

with tab_journal:
    st.subheader("Diario")
    columns, rows = get_trades()
    if rows:
        df = pd.DataFrame(rows, columns=columns)
        st.dataframe(df, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Setups", len(df))
        c2.metric("R:R medio", round(df["rr"].mean(), 2))
        c3.metric("Score medio", round(df["score"].mean(), 2))
    else:
        st.info("Todavía no hay setups guardados.")

with tab_rules:
    st.subheader("Reglas actuales")
    st.markdown("""
- Una operación por setup.
- No perseguir precio.
- Stop Loss técnico.
- Preferencia por R:R ≥ 1:3.
- H1/H4 aportan contexto; M5/M15 deben confirmar.
- Sweep y estructura pesan más que una simple dirección de vela.
- Si faltan confluencias: WAIT.
- Sin ejecución automática de órdenes.
- El score es calidad interna, no probabilidad garantizada.
""")
