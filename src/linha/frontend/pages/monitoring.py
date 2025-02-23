import streamlit as st
import cv2
from datetime import datetime
import pandas as pd
import logging
from linha.frontend.api_client import APIClient
import time
from linha.config.settings import CAPTURE_INTERVAL, ENABLE_PREPROCESSING

logger = logging.getLogger(__name__)

def render_cameras_content(api_client):
    """Conteúdo da tab de câmeras"""
    # Controles em linha
    col1, col2 = st.columns([1, 4])
    
    with col1:
        st.empty()  # Mantém alinhamento com a outra aba
    
    with col2:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Atualizar", use_container_width=True, key="btn_refresh_cameras"):
                st.rerun()
        with col_b:
            auto_refresh = st.checkbox("Auto (5s)", key="chk_auto_cameras")
    
    # Buscar status das câmeras
    status = api_client.get_capture_status()
    
    if 'error' in status:
        st.error(f"❌ {status['error']}")
    else:
        # Mostrar status das câmeras
        st.write("### Status das Câmeras")
        # Métricas globais do sistema
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sistema", "✅ Online" if status['system_running'] else "❌ Offline")
        with col2:
            st.metric("Câmeras", "✅ OK" if status['cameras_configured'] else "❌ Erro")
        with col3:
            st.metric("Captura", "✅ Ativa" if status['is_capturing'] else "❌ Parada")
        with col4:
            # Taxa de captura global
            images_per_minute = 60 / CAPTURE_INTERVAL if CAPTURE_INTERVAL > 0 else 0
            help_text = f"Intervalo entre capturas: {CAPTURE_INTERVAL}s"
            st.metric("Taxa de Captura", f"{images_per_minute:.1f} img/min", help=help_text)
        
        # Status por câmera
        cameras = status.get('cameras', {})
        for camera_id, camera in cameras.items():
            st.markdown("---")
            line_id = camera_id.split('_usb_')[0]
            st.subheader(f"Linha: {line_id}")
            
            cols = st.columns(4)  # Agora 4 colunas ao invés de 5
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

    # Lógica de atualização automática no final
    if auto_refresh:
        time.sleep(5)
        st.rerun()

def render_processor_content(api_client):
    """Conteúdo da tab de processamento"""
    # Estilo
    st.markdown("""
        <style>
            html { overflow-y: auto; }
            .main { overflow-y: auto; height: 100%; }
            .stTabs [data-baseweb="tab-panel"] { height: calc(100vh - 200px); overflow-y: auto; }
            
            /* Estilo para o seletor de tempo e atualização */
            [data-testid="stHorizontalBlock"] { gap: 1rem; align-items: center; }
            div[data-testid="stSelectbox"] { max-width: 100px; }
            
            /* Remover efeito de loading durante atualização */
            .stDeployButton { display: none; }
            .stSpinner { display: none; }
        </style>
    """, unsafe_allow_html=True)
    
    # Controles em linha
    col1, col2 = st.columns([1, 4])
    
    with col1:
        time_filter = st.selectbox(
            "Período:",
            options=[1, 3, 6, 12, 24],
            format_func=lambda x: f"{x}h",
            index=4,
            label_visibility="collapsed",
            key="time_filter"
        )
    
    with col2:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Atualizar", use_container_width=True, key="btn_refresh_processor"):
                st.rerun()
        with col_b:
            auto_refresh = st.checkbox("Auto (5s)", key="chk_auto_processor")
    
    # Buscar dados
    processor_status = api_client.get_processor_status(hours=time_filter)
    
    # Layout em 3 colunas para métricas
    col1, col2, col3 = st.columns(3)
    
    # Coluna 1 - Status dos Lotes
    with col1:
        st.subheader("Status dos Lotes")
        lot_cols1 = st.columns(2)
        with lot_cols1[0]:
            st.metric("Pendentes", processor_status['pending_batches'])
        with lot_cols1[1]:
            st.metric("Processando", processor_status['processing_batches'])
        
        lot_cols2 = st.columns(2)
        with lot_cols2[0]:
            st.metric("Completados", processor_status['completed_batches'])
        with lot_cols2[1]:
            st.metric("Erros", processor_status['error_batches'])
    
    # Coluna 2 - Detecção de Faces
    with col2:
        st.subheader("Detecção de Faces")
        face_cols1 = st.columns(2)
        with face_cols1[0]:
            st.metric("Detectadas", processor_status['total_faces_detected'])
        with face_cols1[1]:
            st.metric("Reconhecidas", processor_status['total_faces_recognized'])
        
        face_cols2 = st.columns(2)
        with face_cols2[0]:
            recognized_rate = (
                processor_status['total_faces_recognized'] / 
                processor_status['total_faces_detected'] * 100
            ) if processor_status['total_faces_detected'] > 0 else 0
            st.metric("Taxa", f"{recognized_rate:.1f}%")
        with face_cols2[1]:
            st.metric("Não Reconhecidas", processor_status['total_faces_unknown'])
    
    # Coluna 3 - Métricas Técnicas
    with col3:
        st.subheader("Métricas")
        metric_cols1 = st.columns(2)
        with metric_cols1[0]:
            st.metric("Tempo/Lote", f"{processor_status['avg_processing_time']:.1f}s")
        with metric_cols1[1]:
            st.metric("Tolerância", f"{processor_status['tolerance']:.3f}")
        
        metric_cols2 = st.columns(2)
        with metric_cols2[0]:
            st.metric("Distância", f"{processor_status['avg_distance']:.3f}")
        with metric_cols2[1]:
            st.empty()  # Mantém o grid 2x2 mesmo com apenas 3 métricas

    # Separador
    st.markdown("---")

    # Gráficos em nova seção
    st.subheader("Histórico")
    graph_cols = st.columns(2)
    
    with graph_cols[0]:
        st.caption("Lotes Processados por Hora")
        df = pd.DataFrame(processor_status['hourly_stats'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        st.line_chart(df['total_batches'], height=250)
        
    with graph_cols[1]:
        st.caption("Faces Detectadas por Hora")
        st.line_chart(df['total_faces'], height=250)

    if 'error' in processor_status:
        st.error(f"❌ {processor_status['error']}")

    # Lógica de atualização automática no final
    if auto_refresh:
        time.sleep(5)
        st.rerun()

def render_monitoring_page(api_client):
    """Renderiza página de monitoramento"""
    try:
        st.title("LineGuard - Monitoramento")
        
        # Criar tabs
        tab_cameras, tab_processor = st.tabs(["Câmeras", "Processamento"])
        
        # Tab Câmeras
        with tab_cameras:
            if tab_cameras.selected:  # Só carrega se a tab estiver ativa
                render_cameras_content(api_client)
            
        # Tab Processamento
        with tab_processor:
            if tab_processor.selected:  # Só carrega se a tab estiver ativa
                render_processor_content(api_client)
                
    except Exception as e:
        st.error("❌ Erro ao carregar dados")
        st.error(str(e))
        logger.exception("Erro na página de monitoramento") 