import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def render_reports_page(api_client):
    """Renderiza página de relatórios"""
    try:
        st.title("LineGuard - Relatórios")
        
        # Filtros em linha como nas outras páginas
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.empty()  # Mantém alinhamento
        
        with col2:
            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_a:
                days = st.selectbox(
                    "Período:",
                    options=[1, 3, 7, 15, 30],
                    format_func=lambda x: f"Últimos {x} dias",
                    index=0
                )
            with col_b:
                view_mode = st.selectbox(
                    "Visualização:",
                    options=["Por Hora", "Por Minuto"],
                    index=0
                )
            with col_c:
                if st.button("🔄 Atualizar", use_container_width=True):
                    st.rerun()
        
        # CSS para layout compacto
        st.markdown("""
            <style>
                /* Container principal */
                .main .block-container {
                    padding: 1rem 2rem !important;
                    max-width: 1200px !important;
                    margin: 0 auto !important;
                }
                
                /* Tabelas mais compactas */
                [data-testid="stDataFrame"] {
                    width: 400px !important;
                }
                
                /* Remover padding excessivo */
                [data-testid="stVerticalBlock"] > div {
                    padding-bottom: 0.5rem !important;
                }
                
                /* Divisores mais sutis */
                hr {
                    margin: 0.5rem 0 !important;
                }
                
                /* Info boxes mais compactos */
                .stAlert {
                    padding: 0.5rem !important;
                    margin: 0.5rem 0 !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Buscar e processar dados
        response = api_client.get_detections(days=days)
        
        if 'error' in response:
            st.error(f"❌ Erro ao buscar dados: {response['error']}")
            return
        
        detections = response.get('detections', [])
        total = response.get('total', 0)
        
        if total > 0:
            st.caption(f"📊 {total} detecções nos últimos {days} dias")
        
        # Organizar dados
        report_data = {}
        for detection in detections:
            line_id = detection.get('line_id', 'unknown')
            time_key = detection.get('minute' if view_mode == "Por Minuto" else 'hour')
            
            if not time_key:
                continue
            
            if line_id not in report_data:
                report_data[line_id] = {}
            if time_key not in report_data[line_id]:
                report_data[line_id][time_key] = {'people': {}, 'total': 0}
            
            for face in detection.get('detections', []):
                person = face.get('name', 'Desconhecido')
                if person not in report_data[line_id][time_key]['people']:
                    report_data[line_id][time_key]['people'][person] = 0
                report_data[line_id][time_key]['people'][person] += 1
                report_data[line_id][time_key]['total'] += 1
        
        # Renderizar relatório
        if not report_data:
            st.info("Nenhuma detecção encontrada no período")
            return
        
        # Criar tabs para cada linha
        tabs = st.tabs([f"📊 {line_id}" for line_id in sorted(report_data.keys())])
        
        for tab, line_id in zip(tabs, sorted(report_data.keys())):
            with tab:
                for time_key in sorted(report_data[line_id].keys(), reverse=True):
                    time_data = report_data[line_id][time_key]
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        if view_mode == "Por Minuto":
                            date, time = time_key.split()
                            st.markdown(f"""
                                #### 🕒 {time}
                                {date}  
                                Total: {time_data['total']}
                            """)
                        else:
                            date, hour = time_key.split()
                            st.markdown(f"""
                                #### 🕒 {hour}
                                {date}  
                                Total: {time_data['total']}
                            """)
                    
                    with col2:
                        if time_data['people']:
                            df = pd.DataFrame([
                                {'Nome': person, 'Detecções': count}
                                for person, count in time_data['people'].items()
                            ]).sort_values('Detecções', ascending=False)
                            
                            st.dataframe(
                                df,
                                column_config={
                                    "Nome": st.column_config.TextColumn("👤 Nome"),
                                    "Detecções": st.column_config.NumberColumn("📊")
                                },
                                hide_index=True
                            )
                    
                    st.markdown("---")
            
    except Exception as e:
        st.error(f"❌ Erro ao renderizar relatório: {str(e)}")
        st.exception(e) 