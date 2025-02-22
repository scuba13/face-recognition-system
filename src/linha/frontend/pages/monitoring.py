import streamlit as st
import cv2
from datetime import datetime
import pandas as pd
import logging
from linha.frontend.api_client import APIClient
import time

logger = logging.getLogger(__name__)

def render_monitoring_page(api_client):
    """Renderiza página de monitoramento"""
    
    st.title("Monitoramento do Sistema")
    
    # Tabs fixas
    tab1, tab2, tab3 = st.tabs(["Câmeras", "Processamento", "Detecções"])
    
    # Criar containers FORA do loop
    with tab1:
        cameras_container = st.empty()
    
    with tab2:
        processor_container = st.empty()
    
    with tab3:
        detections_container = st.empty()
    
    # Intervalo de atualização
    update_interval = st.sidebar.slider("Intervalo (segundos)", 1, 10, 2)
    
    try:
        while True:
            # Atualizar conteúdo das câmeras
            with cameras_container.container():
                status = api_client.get_capture_status()
                if 'error' in status:
                    st.error(f"❌ {status['error']}")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Sistema", "✅ Online" if status['system_running'] else "❌ Offline")
                    with col2:
                        st.metric("Câmeras", "✅ OK" if status['cameras_configured'] else "❌ Erro")
                    with col3:
                        st.metric("Captura", "✅ Ativa" if status['is_capturing'] else "❌ Parada")
                    
                    cameras = status.get('cameras', {})
                    for camera_id, camera in cameras.items():
                        st.markdown("---")
                        line_id = camera_id.split('_usb_')[0]
                        st.subheader(f"Linha: {line_id}")
                        
                        cols = st.columns(5)
                        cols[0].markdown("**Câmera**")
                        cols[0].write(camera['name'])
                        
                        cols[1].markdown("**Status**")
                        cols[1].success("✅ Configurada") if camera['is_configured'] else cols[1].error("❌ Erro")
                        
                        cols[2].markdown("**Captura**")
                        cols[2].success("✅ OK") if camera['can_capture'] else cols[2].error("❌ Erro")
                        
                        cols[3].markdown("**Última Imagem**")
                        last_capture = camera.get('last_image_time')
                        if last_capture:
                            now = datetime.now()
                            last_time = datetime.fromisoformat(last_capture)
                            diff = now - last_time
                            if diff.total_seconds() < 60:
                                cols[3].success(f"✅ {diff.seconds}s atrás")
                            else:
                                cols[3].warning(f"⚠️ {diff.seconds//60}min atrás")
                        else:
                            cols[3].write("🕒 Aguardando...")
                        
                        cols[4].markdown("**FPS**")
                        cols[4].metric("", f"{camera.get('fps', 0):.1f}")
            
            # Limpar e atualizar conteúdo do processamento
            processor_container.empty()
            with processor_container.container():
                processor_status = api_client.get_processor_status()
                if 'error' in processor_status:
                    st.error(f"❌ {processor_status['error']}")
                else:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Lotes Pendentes", processor_status.get('pending_batches', 0))
                    with col2:
                        st.metric("Em Processamento", processor_status.get('processing_batches', 0))
                    with col3:
                        st.metric("Processados", processor_status.get('completed_batches', 0))
            
            # Limpar e atualizar conteúdo das detecções
            detections_container.empty()
            with detections_container.container():
                st.subheader("Últimas Detecções")
                
                # Filtros com keys únicas
                col1, col2 = st.columns(2)
                with col1:
                    selected_line = st.selectbox(
                        "Linha de Produção",
                        options=["Todas"] + list(cameras.keys()),
                        key=f"detections_line_select_{int(time.time())}"
                    )
                with col2:
                    days = st.number_input(
                        "Últimos dias", 
                        min_value=1, 
                        value=7,
                        key=f"days_input_{int(time.time())}"
                    )
                    
                # Buscar detecções
                detections = processor_status.get('recent_detections', [])
                
                if not detections:
                    st.info("Nenhuma detecção encontrada")
                else:
                    # Criar dataframe
                    data = []
                    for det in detections:
                        # Filtrar por linha se selecionada
                        if selected_line != "Todas" and det.get('line_id') != selected_line:
                            continue
                            
                        # Verificar se tem detecções
                        if 'detections' in det and det['detections']:
                            for person in det['detections']:
                                data.append({
                                    "Data/Hora": datetime.fromisoformat(det['timestamp']).strftime("%d/%m/%Y %H:%M"),
                                    "Linha": det.get('line_id', 'N/A'),
                                    "Câmera": det.get('camera_id', 'N/A'),
                                    "Funcionário": person.get('name', 'Desconhecido'),
                                    "Confiança": f"{person.get('confidence', 0):.1%}"
                                })
                    
                    if data:
                        df = pd.DataFrame(data)
                        st.dataframe(df, hide_index=True)
                        
                        # Estatísticas
                        st.markdown("---")
                        st.subheader("Estatísticas")
                        
                        col1, col2 = st.columns(2)
                        
                        # Total por linha
                        with col1:
                            by_line = df["Linha"].value_counts()
                            st.bar_chart(by_line)
                            st.write("Detecções por Linha")
                        
                        # Total por funcionário
                        with col2:
                            by_employee = df["Funcionário"].value_counts().head(10)
                            st.bar_chart(by_employee)
                            st.write("Top 10 Funcionários")
                    else:
                        st.info("Nenhuma detecção encontrada para os filtros selecionados")
            
            time.sleep(update_interval)
            
    except Exception as e:
        st.error(f"Erro no monitoramento: {str(e)}") 