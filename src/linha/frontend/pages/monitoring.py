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
        
        # Botão de atualização
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.rerun()
        
        # Inicializar estado da tab ativa
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "Câmeras"
            
        # Seletor de tabs
        st.session_state.active_tab = st.radio(
            "Selecione a aba:",
            ["Câmeras", "Processamento"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        print(f"\n=== Renderizando tab: {st.session_state.active_tab} ===")
        
        # Renderizar conteúdo da tab ativa
        if st.session_state.active_tab == "Câmeras":
            print("\nChamando GET /cameras/status")
            status = api_client.get_capture_status()
            print(f"Resposta: {status}")
            if 'error' in status:
                st.error(f"❌ Erro: {status['error']}")
                return
            
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
        
        elif st.session_state.active_tab == "Processamento":
            print("\nChamando GET /processor/status")
            processor_status = api_client.get_processor_status()
            print(f"Resposta: {processor_status}")
            
            if 'error' in processor_status:
                st.error(f"❌ {processor_status['error']}")
            else:
                # Métricas principais
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Tempo Médio/Lote",
                        f"{processor_status['avg_processing_time']:.1f}s",
                        help="Tempo médio de processamento por lote"
                    )
                with col2:
                    st.metric(
                        "Faces Detectadas/Reconhecidas",
                        f"{processor_status['total_faces_recognized']}/{processor_status['total_faces_detected']}",
                        help="Total de faces detectadas vs reconhecidas"
                    )
                with col3:
                    st.metric(
                        "Faces Não Reconhecidas",
                        processor_status['total_faces_unknown'],
                        help="Total de faces que não foram reconhecidas"
                    )
                
                # Segunda linha de métricas
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Distância Média",
                        f"{processor_status['avg_distance']:.3f}",
                        help="Média das distâncias entre faces (menor = mais similar)"
                    )
                with col2:
                    st.metric(
                        "Tolerância",
                        f"{processor_status['tolerance']:.3f}",
                        help="Limite de distância para reconhecimento (maior = mais permissivo)"
                    )
                
                # Gráfico por hora
                st.markdown("---")
                st.subheader("Processamentos por Hora")
                
                hourly_data = processor_status['hourly_stats']
                if hourly_data:
                    df = pd.DataFrame(hourly_data)
                    df = df.sort_values('hour')
                    
                    # Gráficos em 2 colunas
                    col1, col2 = st.columns(2)
                    with col1:
                        st.line_chart(df.set_index('hour')['total_batches'])
                        st.write("Total de Lotes")
                    with col2:
                        st.line_chart(df.set_index('hour')['total_faces'])
                        st.write("Total de Faces")
        
    except Exception as e:
        st.error("❌ Erro ao carregar dados")
        st.error(str(e))
        logger.exception("Erro na página de monitoramento") 