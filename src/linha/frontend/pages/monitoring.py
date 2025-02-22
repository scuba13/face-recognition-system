import streamlit as st
import cv2
from datetime import datetime
import pandas as pd
import logging
from linha.frontend.api_client import APIClient
import time
from linha.config.settings import CAPTURE_INTERVAL

logger = logging.getLogger(__name__)

def render_monitoring_page(api_client):
    """Renderiza página de monitoramento"""
    st.title("Monitoramento do Sistema")
    
    # Botão de atualização
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.rerun()
    
    # Buscar dados
    status = api_client.get_capture_status()
    processor_status = api_client.get_processor_status()
    
    # Tabs para organizar o conteúdo
    tab1, tab2, tab3 = st.tabs(["Câmeras", "Processamento", "Detecções"])
    
    # Tab Câmeras
    with tab1:
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
                
                cols[4].markdown("**Taxa de Captura**")
                fps = camera.get('fps', 0)
                # Converter FPS para imagens por minuto (60 segundos / intervalo)
                images_per_minute = 60 / CAPTURE_INTERVAL if CAPTURE_INTERVAL > 0 else 0
                cols[4].metric(
                    "", 
                    f"{images_per_minute:.1f} img/min",
                    help=f"Intervalo entre capturas: {CAPTURE_INTERVAL}s"
                )
    
    # Tab Processamento
    with tab2:
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
    
    # Tab Detecções
    with tab3:
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