# ============================================================
# ROS 2.0 PATCH — tre interventi
# ============================================================
# Come usare:
#   1. Sostituisci la funzione compute_rotation_score_series
#      con compute_rotation_score_series_v2 (Intervento 1)
#   2. Aggiungi le funzioni compute_vol_confirmation e
#      compute_ros_adjusted (Interventi 2 e 3)
#   3. Sostituisci il contenuto di "with tab4:" con il
#      blocco TAB 4 qui sotto
#   4. Mantieni invariato il resto del file
# ============================================================


# ============================================================
# INTERVENTO 1 — Nuova compute_rotation_score_series
#   - Aggiunge peso 1W (5gg) come leading edge
#   - Unifica la logica con la versione scalar (erano diverse)
#   - Pesi: 1W=15% 1M=25% 3M=35% 6M=25%
# ============================================================

WEIGHTS_V2 = {"1W": 0.15, "1M": 0.25, "3M": 0.35, "6M": 0.25}

def compute_rotation_score_series_v2(prices):
    """
    ROS 2.0 — momentum relativo multi-timeframe con leading edge 1W.

    Differenze vs v1:
    - aggiunge 1W (5gg) con peso 0.15 per catturare rotazioni emergenti
    - pesi non uniformi: 1W=15% 1M=25% 3M=35% 6M=25%
    - logica identica alla versione scalar del tab4 (erano disallineate)
    """
    ret_1w  = prices.pct_change(5,   fill_method=None)
    ret_1m  = prices.pct_change(21,  fill_method=None)
    ret_3m  = prices.pct_change(63,  fill_method=None)
    ret_6m  = prices.pct_change(126, fill_method=None)

    # Rendimento relativo vs SPY
    rar_1w = ret_1w.sub(ret_1w[BENCHMARK], axis=0)
    rar_1m = ret_1m.sub(ret_1m[BENCHMARK], axis=0)
    rar_3m = ret_3m.sub(ret_3m[BENCHMARK], axis=0)
    rar_6m = ret_6m.sub(ret_6m[BENCHMARK], axis=0)

    # Media pesata
    rar_weighted = (
        rar_1w * WEIGHTS_V2["1W"] +
        rar_1m * WEIGHTS_V2["1M"] +
        rar_3m * WEIGHTS_V2["3M"] +
        rar_6m * WEIGHTS_V2["6M"]
    )

    cyc  = rar_weighted[CYCLICAL].mean(axis=1)
    def_ = rar_weighted[DEFENSIVE].mean(axis=1)

    rotation_score_v2 = (cyc - def_) * 100
    return rotation_score_v2.dropna()


# ============================================================
# INTERVENTO 2 — Soglia adattiva rolling
#   - rolling std a 252gg invece di std sull'intera storia
#   - in laterale: soglia si restringe → meno falsi segnali
#   - in trend: soglia si allarga → segnali più significativi
# ============================================================

def compute_adaptive_threshold(series, window=252, multiplier=0.75):
    """
    Soglia adattiva basata su rolling std.
    Restituisce una Series allineata all'indice di input.
    Per il display usa il valore corrente (ultimo punto).
    """
    rolling_std = series.rolling(window=window, min_periods=63).std()
    return (rolling_std * multiplier).dropna()


# ============================================================
# INTERVENTO 3 — Vol Confirmation Layer
#   - aggrega i vol_plain già calcolati per ciclici e difensivi
#   - produce un vol_multiplier [0.5, 1.0] che scala il ROS
#   - non richiede nuovi dati: usa vol_plain già disponibile
# ============================================================

VOL_SCORE_MAP = {
    "[B+M+] ACCUMULO":   +1.0,
    "[B+M-] INVERSIONE": +0.3,
    "[B~ M~] INDECISO":   0.0,
    "[B-M+] ESAURIM.":   -0.3,
    "[B-M-] DISTRIBUZ":  -1.0,
}

def compute_vol_confirmation(vol_plain_dict, cyclicals, defensives):
    """
    Vol Confirmation Score: media vol ciclici − media vol difensivi.
    Range teorico: [-2, +2]
    Positivo  → volume conferma risk-on
    Negativo  → volume contraddiice il ROS (segnale dimezzato)
    """
    cyc_scores = [
        VOL_SCORE_MAP.get(vol_plain_dict.get(t, "[B~ M~] INDECISO"), 0.0)
        for t in cyclicals
    ]
    def_scores = [
        VOL_SCORE_MAP.get(vol_plain_dict.get(t, "[B~ M~] INDECISO"), 0.0)
        for t in defensives
    ]
    cyc_mean = float(np.mean(cyc_scores)) if cyc_scores else 0.0
    def_mean = float(np.mean(def_scores)) if def_scores else 0.0
    return round(cyc_mean - def_mean, 3)


def compute_vol_multiplier(vol_confirmation):
    """
    Traduce il Vol Confirmation Score in un moltiplicatore scalare.
    vol_confirmation >= +0.5  → segnale pieno  (1.0)
    vol_confirmation [0, 0.5) → segnale parziale (0.75)
    vol_confirmation < 0      → segnale dimezzato (0.5)
    """
    if vol_confirmation >= 0.5:
        return 1.0
    elif vol_confirmation >= 0.0:
        return 0.75
    else:
        return 0.5


# ============================================================
# TAB 4 — ROTAZIONE SETTORIALE v2
# Sostituisce integralmente il blocco "with tab4:"
# ============================================================

# Incolla questo blocco al posto dell'intero "with tab4:"

with tab4:

    CYCLICALS  = ["XLK","XLY","XLF","XLI","XLE","XLB"]
    DEFENSIVES = ["XLP","XLV","XLU","XLRE"]

    # ── CALCOLO ROS v1 (vecchio) ────────────────────────────────────
    rar_focus_v1 = rsr_df[["1M","3M","6M"]].mean(axis=1)
    cyc_score_v1 = rar_focus_v1.loc[CYCLICALS]
    def_score_v1 = rar_focus_v1.loc[DEFENSIVES]
    rotation_score_v1 = cyc_score_v1.mean() - def_score_v1.mean()

    # ── CALCOLO ROS v2 (Intervento 1 — pesi + 1W) ──────────────────
    rar_1w  = rsr_df["1W"]
    rar_1m  = rsr_df["1M"]
    rar_3m  = rsr_df["3M"]
    rar_6m  = rsr_df["6M"]

    rar_weighted_scalar = (
        rar_1w * WEIGHTS_V2["1W"] +
        rar_1m * WEIGHTS_V2["1M"] +
        rar_3m * WEIGHTS_V2["3M"] +
        rar_6m * WEIGHTS_V2["6M"]
    )
    cyc_score_v2 = rar_weighted_scalar.loc[CYCLICALS].mean()
    def_score_v2 = rar_weighted_scalar.loc[DEFENSIVES].mean()
    rotation_score_v2_scalar = cyc_score_v2 - def_score_v2

    # ── INTERVENTO 3 — Vol Confirmation ────────────────────────────
    vol_conf   = compute_vol_confirmation(vol_plain, CYCLICALS, DEFENSIVES)
    vol_mult   = compute_vol_multiplier(vol_conf)
    rotation_score_adjusted = rotation_score_v2_scalar * vol_mult

    # ── LABEL REGIME (su ROS adjusted) ─────────────────────────────
    if rotation_score_adjusted > 1.5:
        regime  = "🟢 ROTATION: RISK ON"
        bg      = "#003300"
        comment = "Ciclici dominanti — volume confermato" if vol_mult == 1.0 else "Ciclici dominanti — volume parziale"
    elif rotation_score_adjusted < -1.5:
        regime  = "🔴 ROTATION: RISK OFF"
        bg      = "#330000"
        comment = "Difensivi dominanti su timeframe medio"
    else:
        regime  = "🟡 ROTATION: NEUTRAL"
        bg      = "#333300"
        comment = "Equilibrio ciclici/difensivi"

    # ── VOL CONFIRMATION label ──────────────────────────────────────
    if vol_conf >= 0.5:
        vol_conf_label = "✅ VOLUME CONFERMA"
        vol_conf_color = "#00ff55"
    elif vol_conf >= 0.0:
        vol_conf_label = "⚠️ VOLUME PARZIALE"
        vol_conf_color = "#ffaa00"
    else:
        vol_conf_label = "❌ VOLUME CONTRADDICE"
        vol_conf_color = "#ff4422"

    # ── HEADER BOX ─────────────────────────────────────────────────
    col_box1, col_box2, col_box3 = st.columns(3)

    with col_box1:
        st.markdown(f"""
        <div style="background:{bg};padding:16px 24px;border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:4px;">ROS Adjusted</div>
            <div style="font-size:1.6em;font-weight:bold;">{regime}</div>
            <div style="font-size:1.0em;margin-top:4px;color:#aaa;">{rotation_score_adjusted:.2f}</div>
            <div style="font-size:0.78em;color:#666;margin-top:4px;">{comment}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_box2:
        delta_v1_v2 = rotation_score_v2_scalar - rotation_score_v1
        delta_color = "#00ff55" if delta_v1_v2 >= 0 else "#ff4422"
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;
                    border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:4px;">Confronto v1 → v2</div>
            <div style="font-size:0.88em;color:#aaa;">
                v1 (33/33/33): <b style="color:#dddddd">{rotation_score_v1:.2f}</b>
            </div>
            <div style="font-size:0.88em;color:#aaa;margin-top:4px;">
                v2 (15/25/35/25): <b style="color:#dddddd">{rotation_score_v2_scalar:.2f}</b>
            </div>
            <div style="font-size:0.88em;color:#aaa;margin-top:4px;">
                adjusted (×{vol_mult}): <b style="color:#ff9900">{rotation_score_adjusted:.2f}</b>
            </div>
            <div style="font-size:0.80em;margin-top:6px;color:{delta_color};">
                Δ v1→v2: {delta_v1_v2:+.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_box3:
        st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid #222;padding:16px 24px;
                    border-radius:12px;text-align:center;">
            <div style="font-size:0.72em;color:#888;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:4px;">Vol Confirmation</div>
            <div style="font-size:1.1em;font-weight:bold;color:{vol_conf_color};margin-top:4px;">
                {vol_conf_label}
            </div>
            <div style="font-size:0.88em;color:#aaa;margin-top:6px;">
                Score: <b style="color:{vol_conf_color}">{vol_conf:+.2f}</b>
                &nbsp;·&nbsp; Mult: <b style="color:#ff9900">×{vol_mult}</b>
            </div>
            <div style="font-size:0.75em;color:#555;margin-top:6px;">
                Ciclici vol − Difensivi vol
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

    # ── SERIE STORICHE ──────────────────────────────────────────────
    rotation_series_v1 = compute_rotation_score_series(prices)         # vecchia
    rotation_series_v2 = compute_rotation_score_series_v2(prices)      # nuova

    # Soglia adattiva (Intervento 2) sulla serie v2
    adaptive_threshold_series = compute_adaptive_threshold(rotation_series_v2)

    # ── TIMEFRAME SELECTOR ──────────────────────────────────────────
    tf_rot = st.radio(
        "Storico grafico",
        ["1A", "2A", "3A", "5A", "Max"],
        index=0, horizontal=True,
        key="tf_rotation"
    )
    _tf_rot_days = {"1A": 365, "2A": 730, "3A": 1095, "5A": 1825, "Max": 99999}

    def slice_series(s, days):
        if s.empty:
            return s
        cutoff = s.index.max() - pd.Timedelta(days=days)
        return s[s.index >= cutoff]

    days_sel        = _tf_rot_days[tf_rot]
    plot_v1         = slice_series(rotation_series_v1, days_sel)
    plot_v2         = slice_series(rotation_series_v2, days_sel)
    plot_adaptive   = slice_series(adaptive_threshold_series, days_sel)

    # Soglia fissa v1 (per confronto)
    _rs_std_v1    = float(rotation_series_v1.std()) if len(rotation_series_v1) > 5 else 5.0
    _threshold_v1 = round(_rs_std_v1 * 0.75, 2)

    # Soglia adattiva corrente (ultimo valore)
    _threshold_v2_now = float(adaptive_threshold_series.iloc[-1]) if not adaptive_threshold_series.empty else _threshold_v1

    # ── GRAFICI CONFRONTO ───────────────────────────────────────────
    st.markdown(
        '<div style="color:#555;font-size:0.78em;letter-spacing:0.06em;'
        'text-transform:uppercase;margin-bottom:6px;">'
        '◀ ROS v1 (originale) &nbsp;·&nbsp; ROS v2 (adjusted) ▶'
        '</div>',
        unsafe_allow_html=True
    )

    col_g1, col_g2 = st.columns(2)

    # ── Grafico sinistro: ROS v1 con soglia fissa ───────────────────
    with col_g1:
        fig_v1 = go.Figure()
        fig_v1.add_trace(go.Scatter(
            x=plot_v1.index, y=plot_v1,
            mode="lines",
            line=dict(color="#888888", width=1.5),
            name="ROS v1",
            fill='tozeroy',
            fillcolor='rgba(100,100,100,0.15)'
        ))
        fig_v1.add_hline(
            y=_threshold_v1,
            line_dash="dot", line_color="#00AA00",
            annotation_text=f"Risk On +{_threshold_v1:.1f} (fissa)",
            annotation_position="right",
            annotation_font=dict(size=9, color="#00AA00")
        )
        fig_v1.add_hline(y=0.0, line_dash="solid", line_color="#444444")
        fig_v1.add_hline(
            y=-_threshold_v1,
            line_dash="dot", line_color="#AA0000",
            annotation_text=f"Risk Off -{_threshold_v1:.1f} (fissa)",
            annotation_position="right",
            annotation_font=dict(size=9, color="#AA0000")
        )
        fig_v1.update_layout(
            height=300,
            margin=dict(l=40, r=80, t=30, b=40),
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            font_color="white",
            showlegend=False,
            title=dict(
                text="ROS v1 — pesi flat 33/33/33 · soglia fissa",
                font=dict(size=10, color="#666"),
                x=0, xanchor="left"
            ),
            yaxis=dict(gridcolor="#1a1a1a", title=""),
            xaxis=dict(gridcolor="#1a1a1a")
        )
        st.plotly_chart(fig_v1, use_container_width=True)

    # ── Grafico destro: ROS v2 adjusted con soglia adattiva ─────────
    with col_g2:
        fig_v2 = go.Figure()

        # Banda soglia adattiva (area tra +threshold e -threshold)
        if not plot_adaptive.empty:
            common_idx = plot_v2.index.intersection(plot_adaptive.index)
            if len(common_idx) > 0:
                adap_aligned = plot_adaptive.reindex(common_idx).fillna(method="ffill")
                fig_v2.add_trace(go.Scatter(
                    x=common_idx,
                    y=adap_aligned,
                    mode="lines",
                    line=dict(color="#00AA00", width=1, dash="dot"),
                    name="Soglia adattiva +",
                    showlegend=False,
                    opacity=0.6
                ))
                fig_v2.add_trace(go.Scatter(
                    x=common_idx,
                    y=-adap_aligned,
                    mode="lines",
                    line=dict(color="#AA0000", width=1, dash="dot"),
                    name="Soglia adattiva -",
                    fill='tonexty',
                    fillcolor='rgba(80,80,80,0.08)',
                    showlegend=False,
                    opacity=0.6
                ))

        fig_v2.add_trace(go.Scatter(
            x=plot_v2.index, y=plot_v2,
            mode="lines",
            line=dict(color="#DDDDDD", width=2),
            name="ROS v2",
            fill='tozeroy',
            fillcolor='rgba(120,120,120,0.15)'
        ))

        # Marker sul punto corrente con vol_multiplier
        if not plot_v2.empty:
            last_date = plot_v2.index[-1]
            last_val  = float(plot_v2.iloc[-1])
            adj_val   = last_val * vol_mult
            marker_color = "#00ff55" if vol_mult == 1.0 else "#ffaa00" if vol_mult == 0.75 else "#ff4422"
            fig_v2.add_trace(go.Scatter(
                x=[last_date],
                y=[adj_val],
                mode="markers",
                marker=dict(size=10, color=marker_color, symbol="diamond",
                            line=dict(color="white", width=1.5)),
                name=f"Adjusted (×{vol_mult})",
                hovertemplate=f"ROS adjusted: {adj_val:.2f}<extra></extra>"
            ))

        fig_v2.add_hline(y=0.0, line_dash="solid", line_color="#444444")

        # Annotazioni soglia adattiva corrente
        fig_v2.add_annotation(
            x=plot_v2.index[-1] if not plot_v2.empty else 0,
            y=_threshold_v2_now,
            text=f"Risk On +{_threshold_v2_now:.1f} (adattiva)",
            showarrow=False,
            font=dict(size=9, color="#00AA00"),
            xanchor="right", yanchor="bottom"
        )
        fig_v2.add_annotation(
            x=plot_v2.index[-1] if not plot_v2.empty else 0,
            y=-_threshold_v2_now,
            text=f"Risk Off -{_threshold_v2_now:.1f} (adattiva)",
            showarrow=False,
            font=dict(size=9, color="#AA0000"),
            xanchor="right", yanchor="top"
        )

        fig_v2.update_layout(
            height=300,
            margin=dict(l=40, r=80, t=30, b=40),
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            font_color="white",
            showlegend=False,
            title=dict(
                text=f"ROS v2 — pesi 15/25/35/25 · soglia adattiva · ◆ = adj ×{vol_mult}",
                font=dict(size=10, color="#666"),
                x=0, xanchor="left"
            ),
            yaxis=dict(gridcolor="#1a1a1a", title=""),
            xaxis=dict(gridcolor="#1a1a1a")
        )
        st.plotly_chart(fig_v2, use_container_width=True)

    # ── LEGENDA INTERVENTI ──────────────────────────────────────────
    st.markdown("""
    <div style="background:#080808;border:1px solid #1a1a1a;border-radius:8px;
                padding:12px 20px;margin-top:4px;font-size:0.80em;color:#666;
                display:flex;gap:28px;flex-wrap:wrap;">
        <span>
            <b style="color:#ff9900">Intervento 1</b> —
            peso 1W=15% aggiunto come leading edge · pesi: 1W·1M·3M·6M = 15·25·35·25
        </span>
        <span>
            <b style="color:#ff9900">Intervento 2</b> —
            soglia adattiva rolling(252) × 0.75 invece di std sull'intera storia
        </span>
        <span>
            <b style="color:#ff9900">Intervento 3</b> —
            Vol multiplier ×{vol_mult} da VWDS settoriali · score: {vol_conf:+.2f}
        </span>
    </div>
    """.format(vol_mult=vol_mult, vol_conf=vol_conf), unsafe_allow_html=True)

    # ── DETTAGLIO VOL CONFIRMATION ──────────────────────────────────
    with st.expander("🔬 Dettaglio Vol Confirmation per settore", expanded=False):

        vol_detail_rows = []
        for t in CYCLICALS + DEFENSIVES:
            plain = vol_plain.get(t, "[B~ M~] INDECISO")
            score = VOL_SCORE_MAP.get(plain, 0.0)
            vol_detail_rows.append({
                "Ticker":  t,
                "Tipo":    "Ciclico" if t in CYCLICALS else "Difensivo",
                "Vol Signal": plain,
                "Score":   score,
            })

        vd_df = pd.DataFrame(vol_detail_rows)

        def style_vol_score(val):
            if val > 0.5:   return "color:#00ff55;font-weight:bold"
            if val > 0:     return "color:#88cc88"
            if val < -0.5:  return "color:#ff4422;font-weight:bold"
            if val < 0:     return "color:#cc6644"
            return "color:#666"

        def style_tipo(val):
            if val == "Ciclico":   return "color:#ffaa00"
            return "color:#44aaff"

        st.dataframe(
            vd_df.style
                .map(style_vol_score, subset=["Score"])
                .map(style_tipo,      subset=["Tipo"]),
            use_container_width=True,
            hide_index=True,
        )

        # Riepilogo numerico
        cyc_avg = np.mean([VOL_SCORE_MAP.get(vol_plain.get(t,"[B~ M~] INDECISO"), 0.0) for t in CYCLICALS])
        def_avg = np.mean([VOL_SCORE_MAP.get(vol_plain.get(t,"[B~ M~] INDECISO"), 0.0) for t in DEFENSIVES])

        st.markdown(
            f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:6px;'
            f'padding:8px 16px;margin-top:6px;font-size:0.82em;color:#888;'
            f'display:flex;gap:28px;flex-wrap:wrap;">'
            f'<span>Media ciclici: <b style="color:#ffaa00">{cyc_avg:+.2f}</b></span>'
            f'<span>Media difensivi: <b style="color:#44aaff">{def_avg:+.2f}</b></span>'
            f'<span>Vol confirmation: <b style="color:{vol_conf_color}">{vol_conf:+.2f}</b></span>'
            f'<span>Multiplier applicato: <b style="color:#ff9900">×{vol_mult}</b></span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── EPISODI RISK OFF (invariato, su serie v2) ───────────────────
    with st.expander("🔬 Episodi Risk Off — analisi storica", expanded=False):

        confirm_sel = st.radio(
            "Giorni conferma anti-whipsaw",
            [2, 3, 5],
            index=1, horizontal=True,
            key="rs_confirm_days",
            help="Numero di giorni consecutivi sotto soglia necessari per confermare un episodio"
        )

        # Usa la serie v2 e la soglia adattiva corrente per gli episodi
        episodes = compute_risk_off_episodes(
            rotation_series_v2, _threshold_v2_now, confirm_days=confirm_sel
        )

        if not episodes:
            st.info("Nessun episodio Risk Off identificato con i parametri correnti.")
        else:
            st.markdown(
                f'<div style="color:#555;font-size:0.78em;margin-bottom:8px;">'
                f'Soglia adattiva corrente: RS &lt; <b style="color:#AA0000">-{_threshold_v2_now:.1f}</b> · '
                f'Conferma: <b>{confirm_sel}</b> giorni consecutivi · '
                f'Episodi identificati: <b style="color:#ff9900">{len(episodes)}</b>'
                f'</div>',
                unsafe_allow_html=True
            )

            rows_ep = []
            for i, ep in enumerate(episodes, 1):
                stato   = "🔴 APERTO" if ep["open"] else "✅ chiuso"
                end_str = "in corso"  if ep["open"] else ep["end"].strftime("%d/%m/%Y")
                rows_ep.append({
                    "#":           i,
                    "Inizio":      ep["start"].strftime("%d/%m/%Y"),
                    "Confermato":  ep["confirmed"].strftime("%d/%m/%Y"),
                    "Fine":        end_str,
                    "Durata (gg)": ep["duration"],
                    "RS minimo":   ep["rs_min"],
                    "Data minimo": ep["rs_min_date"].strftime("%d/%m/%Y"),
                    "Stato":       stato,
                })

            ep_df = pd.DataFrame(rows_ep)

            def style_ep(row):
                if "APERTO" in str(row["Stato"]):
                    return ["background-color:#1a0000; color:#ff4422"] * len(row)
                return ["color:#aaaaaa"] * len(row)

            def style_rs_min(val):
                try:
                    v = float(val)
                    if v < -7: return "color:#ff4422;font-weight:bold"
                    if v < -5: return "color:#ffaa00;font-weight:bold"
                    return "color:#888888"
                except Exception:
                    return ""

            st.dataframe(
                ep_df.style
                    .apply(style_ep, axis=1)
                    .map(style_rs_min, subset=["RS minimo"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Durata (gg)": st.column_config.NumberColumn("Durata (gg)", format="%d"),
                    "RS minimo":   st.column_config.NumberColumn("RS minimo",   format="%.2f"),
                }
            )

            closed = [e for e in episodes if not e["open"]]
            if closed:
                durate = [e["duration"] for e in closed]
                minimi = [e["rs_min"]   for e in closed]
                st.markdown(
                    f'<div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;'
                    f'padding:10px 20px;margin-top:8px;font-size:0.82em;color:#888;'
                    f'display:flex;gap:28px;flex-wrap:wrap;">'
                    f'<span>Episodi chiusi: <b style="color:#ff9900">{len(closed)}</b></span>'
                    f'<span>Durata media: <b style="color:#ff9900">{int(sum(durate)/len(durate))} gg</b></span>'
                    f'<span>Durata max: <b style="color:#ff9900">{max(durate)} gg</b></span>'
                    f'<span>RS minimo storico: <b style="color:#ff4422">{min(minimi):.2f}</b></span>'
                    f'<span>RS minimo medio: <b style="color:#ffaa00">{sum(minimi)/len(minimi):.2f}</b></span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── SPIEGAZIONE ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#0d0d0d;padding:25px;border-radius:10px;
                font-size:1.0em;line-height:1.7;margin-top:8px;">
    <h3 style="color:#ff9900;margin-top:0;">📊 ROS 2.0 — Tre Interventi</h3>

    <b style="color:#ff9900">Intervento 1 — Leading Edge 1W</b><br>
    Aggiunto timeframe settimanale con peso 15% per catturare rotazioni emergenti
    prima che si consolidino nel mensile. Pesi: 1W=15% · 1M=25% · 3M=35% · 6M=25%.<br><br>

    <b style="color:#ff9900">Intervento 2 — Soglia Adattiva</b><br>
    La soglia Risk On/Off è ora calcolata su rolling std 252 giorni × 0.75.
    In mercati laterali (bassa dispersione) la soglia si restringe → meno falsi segnali.
    In mercati direzionali si allarga → segnali più significativi.
    Soglia corrente: <b style="color:#ff9900">±{_threshold_v2_now:.2f}</b>
    vs soglia fissa v1: <b style="color:#888">±{_threshold_v1:.2f}</b><br><br>

    <b style="color:#ff9900">Intervento 3 — Vol Confirmation</b><br>
    Aggrega i VWDS già calcolati per ciclici e difensivi in un Vol Confirmation Score
    ({vol_conf:+.2f}). Quando il volume contraddice il momentum relativo, il segnale
    viene scalato: ×1.0 (confermato) · ×0.75 (parziale) · ×0.5 (contradditorio).<br>
    Score corrente: <b style="color:{vol_conf_color}">{vol_conf_label}</b> → multiplier ×{vol_mult}

    <h3 style="color:#ff9900;margin-top:20px;">🎯 Situazione Attuale</h3>
    <div style="background:#1a1a1a;padding:15px;border-radius:8px;">
        ROS v1: <b>{rotation_score_v1:.2f}</b> →
        ROS v2: <b>{rotation_score_v2_scalar:.2f}</b> →
        ROS adjusted: <b style="color:#ff9900">{rotation_score_adjusted:.2f}</b>
        ({comment})
    </div>
    </div>
    """, unsafe_allow_html=True)
