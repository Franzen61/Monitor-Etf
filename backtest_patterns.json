{
  "metadata": {
    "titolo": "Backtest Rotation Score — Episodi Risk Off",
    "versione": "1.0",
    "aggiornato": "2026-03-15",
    "autore": "Franco",
    "note": "Dataset costruito su serie storica 2021-2026. Soglia Risk Off dinamica (~-3.5). Conferma anti-whipsaw: 5 giorni consecutivi. Performance SPY calcolata da bottom SPY (non bottom RS)."
  },

  "definizioni": {
    "rs_min": "Valore minimo del Rotation Score durante l'episodio",
    "durata_gg": "Giorni totali sotto soglia Risk Off (da inizio a fine episodio)",
    "delta_rs_spy_gg": "Giorni tra bottom RS e bottom SPY. Positivo = RS tocca il fondo prima di SPY (RS lagging su SPY)",
    "spy_perf_20": "Variazione % SPY nei 20 giorni lavorativi successivi al bottom SPY",
    "spy_perf_40": "Variazione % SPY nei 40 giorni lavorativi successivi al bottom SPY",
    "qualita_top_successivo": "VERO se RSI_ciclici - RSI_difensivi > +5 al top successivo. TECNICO se spread < +5 o negativo"
  },

  "pattern": {
    "A": {
      "nome": "Capitolazione vera",
      "condizioni": {
        "vix": "> 30",
        "move": "> 140",
        "rs_min": "< -8",
        "ief_shy": "< 15"
      },
      "descrizione": "Stress simultaneo su equity e bond. Capitolazione completa. Bottom definitivo del ciclo.",
      "payoff_atteso": "Forte — massimo potere predittivo"
    },
    "B": {
      "nome": "Rotazione silenziosa",
      "condizioni": {
        "vix": "< 20",
        "move": "60-130",
        "rs_min": "< -6",
        "ief_shy": "qualsiasi"
      },
      "descrizione": "Nessuno stress su equity. I ciclici vendono silenziosamente. Possibile bear market in sviluppo — verificare contesto macro prima di entrare.",
      "payoff_atteso": "Variabile — positivo se correzione tattica, negativo se bear market strutturale"
    },
    "C": {
      "nome": "Shock tecnico",
      "condizioni": {
        "vix": "< 15",
        "move": "< 120",
        "rs_min": "< -8",
        "causa": "esogena identificabile"
      },
      "descrizione": "Sell-off tecnico localizzato con causa esogena identificabile (es. carry trade). Non fondamentale. Recupero rapido e violento.",
      "payoff_atteso": "Positivo a +40gg — recupero rapido ma episodio RS può durare a lungo per inerzia"
    },
    "D": {
      "nome": "Stress macro diffuso",
      "condizioni": {
        "vix": "> 30",
        "move": "120-135",
        "rs_min": "> -8",
        "ief_shy": "< 13"
      },
      "descrizione": "Stress elevato su equity ma bond non in zona estrema. Curva già compressa. Simile ad A ma meno intenso. Rimbalzo presente ma struttura debole.",
      "payoff_atteso": "Moderatamente positivo — orizzonte 40gg preferibile a 20gg"
    }
  },

  "regola_qualita_top": {
    "descrizione": "Distingue top VERI (cambio regime) da top TECNICI (rimbalzo)",
    "top_vero": "RSI_ciclici - RSI_difensivi > +5 al top del RS",
    "top_tecnico": "RSI_difensivi > RSI_ciclici oppure spread < +5",
    "implicazione": "Un top TECNICO non conferma cambio di regime — alta probabilità di nuovo episodio Risk Off entro 60 giorni"
  },

  "regola_operativa": {
    "segnale_positivo": "RS < -5 con VIX > 20 → attendi conferma bottom RS → entry ciclici o SPY con orizzonte 40 giorni lavorativi",
    "segnale_negativo": "RS < -5 con VIX < 20 e nessuna causa esogena → non entrare — probabile bear market in sviluppo con ulteriore leg down",
    "payoff_medio_casi_positivi": "+8.7% a +40gg (4 episodi su 5)",
    "nota_timing": "Il bottom RS arriva IN MEDIA 33 giorni PRIMA del bottom SPY. Non usare il bottom RS come segnale di ingresso su SPY — usarlo come segnale di ingresso su ciclici."
  },

  "episodi": [
    {
      "id": 1,
      "pattern": "B",
      "rs_inizio": "2021-08-17",
      "rs_confermato": "2021-08-23",
      "rs_fine": "2021-09-21",
      "rs_bottom_date": "2021-08-20",
      "rs_min": -6.46,
      "durata_gg": 35,
      "spy_bottom_date": "2021-09-21",
      "spy_swing_date": "2021-10-04",
      "delta_rs_spy_gg": 32,
      "spy_perf_20": 3.92,
      "spy_perf_40": 8.22,
      "esito": "positivo",
      "indicatori": {
        "vix": 22.5,
        "move": 67.58,
        "ief_shy": 30.77,
        "rsi_spy": 45.13,
        "rsi_ciclici": 38.71,
        "rsi_difensivi": 61.87,
        "spread_cic_dif": -23.16
      },
      "top_successivo": {
        "data": "2021-10-18",
        "rs_valore": null,
        "rsi_ciclici": 64.64,
        "rsi_difensivi": 45.87,
        "spread": 18.77,
        "qualita": "VERO"
      },
      "note": "Rotazione silenziosa estiva. MOVE bassissimo (67) — nessuno stress obbligazionario. Nonostante Pattern B ha dato esito positivo perché non era bear market strutturale."
    },
    {
      "id": 2,
      "pattern": "B",
      "rs_inizio": "2022-04-06",
      "rs_confermato": "2022-04-12",
      "rs_fine": "2022-06-01",
      "rs_bottom_date": "2022-04-26",
      "rs_min": -8.68,
      "durata_gg": 56,
      "spy_bottom_date": "2022-05-19",
      "spy_swing_date": "2022-05-19",
      "delta_rs_spy_gg": 23,
      "spy_perf_20": -5.86,
      "spy_perf_40": -2.97,
      "esito": "negativo",
      "indicatori": {
        "vix": 16.31,
        "move": 129.27,
        "ief_shy": 20.39,
        "rsi_spy": 45.13,
        "rsi_ciclici": 41.37,
        "rsi_difensivi": 49.70,
        "spread_cic_dif": -8.33
      },
      "top_successivo": {
        "data": "2022-10-24",
        "rs_valore": null,
        "rsi_ciclici": 54.00,
        "rsi_difensivi": 50.14,
        "spread": 3.86,
        "qualita": "TECNICO"
      },
      "note": "UNICO CASO NEGATIVO. Bear market strutturale in sviluppo — Fed stringe aggressivamente. VIX=16 nonostante RS a -8.68 segnalava mercato non in panico ma in de-risking ordinato. Il bottom SPY vero arrivò a ottobre 2022 (ep.3). NON entrare con VIX < 20 senza causa esogena identificabile."
    },
    {
      "id": 3,
      "pattern": "A",
      "rs_inizio": "2022-06-23",
      "rs_confermato": "2022-06-29",
      "rs_fine": "2022-08-02",
      "rs_bottom_date": "2022-07-06",
      "rs_min": -8.69,
      "durata_gg": 40,
      "spy_bottom_date": "2022-06-22",
      "spy_swing_date": "2022-06-22",
      "delta_rs_spy_gg": -14,
      "spy_perf_20": 5.44,
      "spy_perf_40": 13.96,
      "esito": "positivo_forte",
      "indicatori": {
        "vix": 33.52,
        "move": 151.14,
        "ief_shy": 20.67,
        "rsi_spy": 45.59,
        "rsi_ciclici": 42.23,
        "rsi_difensivi": 53.24,
        "spread_cic_dif": -11.01
      },
      "top_successivo": {
        "data": "2022-10-24",
        "rs_valore": null,
        "rsi_ciclici": 54.00,
        "rsi_difensivi": 50.14,
        "spread": 3.86,
        "qualita": "TECNICO"
      },
      "note": "CAPITOLAZIONE VERA. Unico episodio con RS LEADING su SPY (-14gg). MOVE=151 — stress obbligazionario estremo. Bottom definitivo del bear market 2022. Miglior payoff del dataset (+13.96% a 40gg). Top successivo tecnico — cambio regime non ancora consolidato."
    },
    {
      "id": 4,
      "pattern": "C",
      "rs_inizio": "2024-08-01",
      "rs_confermato": "2024-08-07",
      "rs_fine": "2024-10-10",
      "rs_bottom_date": "2024-08-06",
      "rs_min": -8.29,
      "durata_gg": 70,
      "spy_bottom_date": "2024-10-03",
      "spy_swing_date": "2024-10-03",
      "delta_rs_spy_gg": 58,
      "spy_perf_20": 0.14,
      "spy_perf_40": 6.12,
      "esito": "positivo_lento",
      "indicatori": {
        "vix": 13.88,
        "move": 112.69,
        "ief_shy": 14.36,
        "rsi_spy": 33.55,
        "rsi_ciclici": 34.02,
        "rsi_difensivi": 51.08,
        "spread_cic_dif": -17.06
      },
      "top_successivo": {
        "data": "2025-02-04",
        "rs_valore": 7.05,
        "rsi_ciclici": 38.02,
        "rsi_difensivi": 56.76,
        "spread": -18.74,
        "qualita": "TECNICO"
      },
      "note": "SHOCK TECNICO carry trade yen. VIX=13.88 minimo del dataset. RS bottom ad agosto ma SPY bottom a ottobre (+58gg delta) — doppio minimo SPY. Episodio più lungo (70gg) per inerzia del RS. Top successivo TECNICO con spread negativo (-18.74) — rimbalzo senza cambio di regime confermato."
    },
    {
      "id": 5,
      "pattern": "D",
      "rs_inizio": "2025-04-10",
      "rs_confermato": "2025-04-16",
      "rs_fine": "2025-05-07",
      "rs_bottom_date": "2025-04-21",
      "rs_min": -7.54,
      "durata_gg": 27,
      "spy_bottom_date": "2025-05-10",
      "spy_swing_date": "2025-04-08",
      "delta_rs_spy_gg": 19,
      "spy_perf_20": 2.77,
      "spy_perf_40": 6.46,
      "esito": "positivo",
      "indicatori": {
        "vix": 33.82,
        "move": 128.56,
        "ief_shy": 11.93,
        "rsi_spy": 38.65,
        "rsi_ciclici": 38.51,
        "rsi_difensivi": 41.25,
        "spread_cic_dif": -2.74
      },
      "top_successivo": {
        "data": "2025-07-08",
        "rs_valore": null,
        "rsi_ciclici": 68.28,
        "rsi_difensivi": 50.52,
        "spread": 17.76,
        "qualita": "VERO"
      },
      "note": "Liberation Day dazi. VIX=33.82 ma MOVE=129 — stress equity elevato, bond meno estremo del 2022. IEF-SHY=11.93 minimo storico — curva strutturalmente compressa. Spread CIC-DIF quasi neutro (-2.74) — sell-off indiscriminato. Top successivo VERO (lug 2025) — primo cambio di regime confermato post-episodio."
    }
  ],

  "statistiche_aggregate": {
    "episodi_totali": 5,
    "episodi_positivi": 4,
    "episodi_negativi": 1,
    "win_rate": "80%",
    "spy_perf_20_media_tutti": 1.28,
    "spy_perf_40_media_tutti": 6.36,
    "spy_perf_20_media_positivi": 3.07,
    "spy_perf_40_media_positivi": 8.69,
    "durata_media_gg": 45.6,
    "durata_max_gg": 70,
    "rs_min_storico": -8.69,
    "rs_min_medio": -7.93,
    "delta_rs_spy_medio_gg": 24,
    "nota_timing": "In media il RS tocca il fondo 24 giorni prima del bottom SPY. Usare il bottom RS come segnale su ciclici, non su SPY."
  }
}
