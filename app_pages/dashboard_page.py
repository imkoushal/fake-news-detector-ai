import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_dashboard_page(db):
    """Render the Dashboard tab with model health monitoring (Phase 6)."""
    if not db:
        st.warning("Database not available. Dashboard disabled.")
        return

    # ── Phase 6: Model Health Monitor ──
    st.subheader('🏥 Model Health Monitor')
    
    try:
        from model_monitor import ModelMonitor
        monitor = ModelMonitor()
        health = monitor.get_health_report(days=7)
        
        if health["status"] != "NO_DATA":
            # Health status banner
            status = health["status"]
            if status == "HEALTHY":
                st.success(f'✅ **Model Status: HEALTHY** — All metrics within normal ranges')
            elif status == "WARNING":
                st.warning(f'⚠️ **Model Status: WARNING** — Some metrics need attention')
            else:
                st.error(f'🔴 **Model Status: CRITICAL** — Immediate action required')
            
            metrics = health.get("metrics", {})
            
            # Key health metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric('Predictions (7d)', health.get("total_predictions", 0))
            with col2:
                st.metric('Avg Confidence', f"{metrics.get('avg_confidence', 0):.1f}%")
            with col3:
                fake_rate = metrics.get('fake_rate', 0)
                st.metric('Fake Rate', f"{fake_rate:.1%}")
            with col4:
                ood_rate = metrics.get('ood_rate', 0)
                delta_color = 'inverse' if ood_rate > 0.3 else 'normal'
                st.metric('OOD Rate', f"{ood_rate:.1%}", 
                         '⚠️ High' if ood_rate > 0.3 else '✓ Normal',
                         delta_color=delta_color)
            with col5:
                avg_rf = metrics.get('avg_red_flag_score', 0)
                st.metric('Avg Red Flags', f"{avg_rf:.2f}")
            
            # Confidence distribution
            conf_dist = health.get("confidence_distribution", {})
            if any(v > 0 for v in conf_dist.values()):
                st.subheader('📊 Confidence Distribution')
                df_conf = pd.DataFrame({
                    'Range': ['< 50%', '50-70%', '70-90%', '90-100%'],
                    'Count': [
                        conf_dist.get('low_0_50', 0),
                        conf_dist.get('medium_50_70', 0),
                        conf_dist.get('high_70_90', 0),
                        conf_dist.get('very_high_90_100', 0),
                    ]
                })
                fig_conf = px.bar(df_conf, x='Range', y='Count',
                                 color='Range',
                                 color_discrete_map={
                                     '< 50%': '#EF4444',
                                     '50-70%': '#F59E0B',
                                     '70-90%': '#3B82F6',
                                     '90-100%': '#10B981',
                                 },
                                 title='Prediction Confidence Buckets')
                fig_conf.update_layout(showlegend=False)
                st.plotly_chart(fig_conf, use_container_width=True)

            # Daily trend
            daily = health.get("daily_trend", [])
            if daily:
                st.subheader('📈 Daily Prediction Trend')
                df_daily = pd.DataFrame(daily)
                if not df_daily.empty:
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=df_daily['date'], y=df_daily['real'],
                        name='Real', mode='lines+markers',
                        line=dict(color='#10B981', width=2),
                        fill='tonexty' if 'fake' in df_daily.columns else None
                    ))
                    fig_trend.add_trace(go.Scatter(
                        x=df_daily['date'], y=df_daily['fake'],
                        name='Fake', mode='lines+markers',
                        line=dict(color='#EF4444', width=2)
                    ))
                    fig_trend.update_layout(
                        title='Daily Predictions by Verdict',
                        xaxis_title='Date', yaxis_title='Count',
                        template='plotly_dark'
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

                    # OOD trend
                    if df_daily['ood_count'].sum() > 0:
                        fig_ood = px.bar(df_daily, x='date', y='ood_count',
                                        title='Daily OOD Detections',
                                        color_discrete_sequence=['#F59E0B'])
                        st.plotly_chart(fig_ood, use_container_width=True)

            # Alerts
            alerts = health.get("alerts", [])
            if alerts:
                st.subheader('🚨 Active Alerts')
                for alert in alerts:
                    severity = alert.get("severity", "info")
                    msg = alert.get("message", "")
                    if severity == "critical":
                        st.error(f'🔴 **CRITICAL:** {msg}')
                    elif severity == "warning":
                        st.warning(f'🟡 **WARNING:** {msg}')
                    else:
                        st.info(f'✅ {msg}')
        else:
            st.info('No monitoring data yet. Analyze some articles to start tracking model health!')
    except ImportError:
        st.info('Model monitor not available. Install model_monitor.py to enable health tracking.')
    except Exception as e:
        st.info(f'Monitor unavailable: {e}')
    
    st.markdown('---')

    # ── Original Dashboard Content ──
    st.subheader('📊 Analysis History')
    stats = db.get_statistics()
    
    if stats['total'] > 0:
        # Top metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('Total Analyzed', stats['total'])
        with col2:
            st.metric('Avg Confidence', f"{stats['avg_confidence']:.1f}%")
        with col3:
            fake_count = stats['predictions'].get('FAKE', 0)
            fake_pct = (fake_count / stats['total']) * 100
            st.metric('Fake News Detected', f"{fake_count} ({fake_pct:.1f}%)")
        
        st.markdown('---')
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader('Real vs Fake Distribution')
            if stats['predictions']:
                df_pred = pd.DataFrame(list(stats['predictions'].items()), columns=['Label', 'Count'])
                fig = px.pie(df_pred, values='Count', names='Label', color='Label',
                             color_discrete_map={'REAL': '#00CC96', 'FAKE': '#EF553B'})
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader('Topic Distribution')
            if stats['categories']:
                df_cat = pd.DataFrame(list(stats['categories'].items()), columns=['Topic', 'Count'])
                fig = px.bar(df_cat, x='Topic', y='Count')
                st.plotly_chart(fig, use_container_width=True)
        
        # Trend Analysis
        st.subheader('📈 Activity Trend')
        history_all = db.get_history(limit=500)
        if not history_all.empty and 'timestamp' in history_all.columns:
            try:
                history_all['date'] = pd.to_datetime(history_all['timestamp']).dt.date
                daily_counts = history_all.groupby(['date', 'prediction']).size().reset_index(name='count')
                
                fig_trend = px.line(daily_counts, x='date', y='count', color='prediction',
                                  title='Daily Analysis Volume by Verdict',
                                  color_discrete_map={'REAL': '#00CC96', 'FAKE': '#EF553B'},
                                  markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)
            except Exception as e:
                st.info(f"Not enough data for trend analysis yet.")

        # Recent History Table
        st.subheader('📜 Recent Analyses')
        history_df = db.get_history(limit=50)
        if not history_df.empty:
            st.dataframe(
                history_df[['timestamp', 'prediction', 'confidence', 'category', 'article_preview']],
                use_container_width=True
            )
            
            # CSV Download
            csv = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Full History CSV",
                csv,
                "full_history.csv",
                "text/csv",
                key='download-history'
            )
        
        # Top Red Flags
        if stats['top_red_flags']:
            st.subheader('🚩 Top Suspicious Articles')
            for preview, score in stats['top_red_flags']:
                st.warning(f"**Score {score:.2f}**: {preview[:150]}...")

        # Evaluation Report Button
        st.markdown('---')
        st.subheader('📋 Evaluation Report')
        if st.button('📊 Generate Full Evaluation Report', use_container_width=True):
            try:
                from eval_report import generate_report, print_report
                report = generate_report()
                
                # Display key metrics
                perf = report.get("performance", {})
                ti = report.get("total_improvement", {})
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric('Accuracy', f"{perf.get('accuracy', 0):.2%}")
                with col2:
                    st.metric('F1 Score', f"{perf.get('f1_score', 0):.2%}")
                with col3:
                    st.metric('ROC-AUC', f"{perf.get('roc_auc', 0):.2%}")
                with col4:
                    st.metric('Total Improvement', f"+{ti.get('accuracy', 0):.2%}")
                
                # Trajectory
                traj = report.get("improvement_trajectory", [])
                if traj:
                    st.subheader('Phase-by-Phase Progress')
                    df_traj = pd.DataFrame(traj)
                    if 'version' in df_traj.columns:
                        fig_traj = go.Figure()
                        fig_traj.add_trace(go.Scatter(
                            x=df_traj['version'], y=df_traj['accuracy'],
                            name='Accuracy', mode='lines+markers',
                            line=dict(color='#10B981', width=3)
                        ))
                        fig_traj.add_trace(go.Scatter(
                            x=df_traj['version'], y=df_traj['f1'],
                            name='F1', mode='lines+markers',
                            line=dict(color='#3B82F6', width=3)
                        ))
                        fig_traj.update_layout(
                            title='Model Performance Over Phases',
                            yaxis_title='Score', xaxis_title='Version',
                            template='plotly_dark'
                        )
                        st.plotly_chart(fig_traj, use_container_width=True)
                
                # Download full report
                import json
                report_json = json.dumps(report, indent=2, default=str)
                st.download_button(
                    "📥 Download Full Report (JSON)",
                    report_json,
                    "eval_report.json",
                    "application/json",
                    key='download-report'
                )
            except Exception as e:
                st.error(f'Could not generate report: {e}')
                
    else:
        st.info('No analysis history yet. Analyze some articles to see statistics!')
