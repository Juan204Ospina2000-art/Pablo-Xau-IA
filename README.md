# Pablo XAU AI — V2

IA personal especializada en XAU/USD.

## Novedades V2
- Conexión con Twelve Data para XAU/USD.
- Velas automáticas M1, M5, M15, H1 y H4.
- Tendencia mediante EMA20/EMA50.
- Estructura simplificada HH/HL, LH/LL o rango.
- Detector básico de sweep de máximos/mínimos.
- Momentum de vela.
- Sesgo multi-timeframe ponderado.
- Señal técnica: BUY CANDIDATE, SELL CANDIDATE o WAIT.
- Conserva motor sniper manual y diario.

## Importante
V2 NO abre operaciones.
V2 NO incluye todavía noticias ni calendario económico.
El detector técnico es una primera versión heurística que deberá validarse
mediante backtesting antes de interpretar su score como ventaja estadística.

## Paso 1 — Obtener API key
Crea una cuenta personal en Twelve Data y copia tu API key.

## Paso 2 — Ejecutar
```bash
pip install -r requirements.txt
streamlit run app.py
```

Pega tu clave en la barra lateral de la app.

También puedes guardarla como variable de entorno:
```bash
TWELVE_DATA_API_KEY=tu_clave
```

## Datos
Proveedor configurado: Twelve Data
Símbolo: XAU/USD
Timeframes: 1min, 5min, 15min, 1h, 4h

## Próximo paso
V3:
- calendario económico;
- noticias de alto impacto;
- bloqueo automático alrededor de CPI, NFP, FOMC, etc.;
- contexto macro de oro.

Uso educativo. No garantiza resultados.
