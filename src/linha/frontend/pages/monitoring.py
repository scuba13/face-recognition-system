import streamlit as st
import cv2
from datetime import datetime
import pandas as pd
import logging
from linha.frontend.api_client import APIClient
import time
from linha.config.settings import CAPTURE_INTERVAL, ENABLE_PREPROCESSING

logger = logging.getLogger(__name__)

def render_monitoring_page(api_client):
    """Renderiza página de monitoramento"""
    try:
        st.title("Monitoramento do Sistema")
        
        # Criar tabs
        tab_cameras, tab_processor = st.tabs([
            "Câmeras",
            "Processamento"
        ])
        
        # Tab Câmeras
        with tab_cameras:
            # Buscar status das câmeras
            print("\nChamando GET /cameras/status")
            status = api_client.get_capture_status()
            
            # Botão de atualização para câmeras
            if st.button("🔄 Atualizar Status das Câmeras", key="refresh_cameras", use_container_width=True):
                st.rerun()
            
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
        
        # Tab Processamento
        with tab_processor:
            # Buscar status do processador
            print("\nChamando GET /processor/status")
            processor_status = api_client.get_processor_status()
            
            # Botão de atualização para processamento
            if st.button("🔄 Atualizar Status do Processamento", key="refresh_processor", use_container_width=True):
                st.rerun()
            
            if 'error' in processor_status:
                st.error(f"❌ {processor_status['error']}")
            else:
                # Container principal com 3 colunas
                main_cols = st.columns([1.2, 1.2, 0.6])
                
                # Coluna 1 - Status dos Lotes
                with main_cols[0]:
                    st.subheader("Status dos Lotes")
                    
                    # Grid 2x2 para métricas
                    lot_cols1 = st.columns(2)
                    with lot_cols1[0]:
                        st.metric(
                            "Pendentes",
                            processor_status['pending_batches'],
                            delta=None,
                            help="Aguardando processamento"
                        )
                    with lot_cols1[1]:
                        st.metric(
                            "Processando",
                            processor_status['processing_batches'],
                            delta=None,
                            help="Em processamento"
                        )
                    
                    lot_cols2 = st.columns(2)
                    with lot_cols2[0]:
                        st.metric(
                            "Completados",
                            processor_status['completed_batches'],
                            delta=None,
                            help="Processamento finalizado"
                        )
                    with lot_cols2[1]:
                        st.metric(
                            "Erros",
                            processor_status['error_batches'],
                            delta=None,
                            delta_color="inverse",
                            help="Falhas no processamento"
                        )
                    
                    # Gráfico de lotes por hora
                    st.caption("Lotes Processados por Hora")
                    st.line_chart(
                        pd.DataFrame(processor_status['hourly_stats'])
                        .set_index('hour')['total_batches'],
                        height=120,
                        use_container_width=True
                    )
                
                # Coluna 2 - Detecção de Faces
                with main_cols[1]:
                    st.subheader("Detecção de Faces")
                    
                    # Grid 2x2 para métricas
                    face_cols1 = st.columns(2)
                    with face_cols1[0]:
                        st.metric(
                            "Detectadas",
                            processor_status['total_faces_detected'],
                            delta=None,
                            help="Total de faces nas imagens"
                        )
                    with face_cols1[1]:
                        st.metric(
                            "Reconhecidas",
                            processor_status['total_faces_recognized'],
                            delta=None,
                            help="Faces com match"
                        )
                    
                    face_cols2 = st.columns(2)
                    with face_cols2[0]:
                        recognized_rate = (
                            processor_status['total_faces_recognized'] / 
                            processor_status['total_faces_detected'] * 100
                        ) if processor_status['total_faces_detected'] > 0 else 0
                        st.metric(
                            "Taxa",
                            f"{recognized_rate:.1f}%",
                            delta=None,
                            help="Taxa de reconhecimento"
                        )
                    with face_cols2[1]:
                        st.metric(
                            "Não Reconhecidas",
                            processor_status['total_faces_unknown'],
                            delta=None,
                            help="Faces sem match"
                        )
                    
                    # Gráfico de faces por hora
                    st.caption("Faces Detectadas por Hora")
                    st.line_chart(
                        pd.DataFrame(processor_status['hourly_stats'])
                        .set_index('hour')['total_faces'],
                        height=120,
                        use_container_width=True
                    )
                
                # Coluna 3 - Métricas Técnicas
                with main_cols[2]:
                    st.subheader("Métricas")
                    st.metric(
                        "Tempo/Lote",
                        f"{processor_status['avg_processing_time']:.1f}s",
                        delta=None,
                        help="Tempo médio de processamento"
                    )
                    st.metric(
                        "Distância",
                        f"{processor_status['avg_distance']:.3f}",
                        delta=None,
                        help="Média das distâncias (menor = mais similar)"
                    )
                    st.metric(
                        "Tolerância",
                        f"{processor_status['tolerance']:.3f}",
                        delta=None,
                        help="Limite para reconhecimento"
                    )
        
    except Exception as e:
        st.error("❌ Erro ao carregar dados")
        st.error(str(e))
        logger.exception("Erro na página de monitoramento") 