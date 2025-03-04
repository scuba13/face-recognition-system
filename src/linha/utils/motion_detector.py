"""
Serviço para detecção de movimento em frames de vídeo.
"""
import cv2
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Cores padrão
COR_VERDE = (0, 255, 0)
COR_VERMELHO = (0, 0, 255)

class MotionDetector:
    """
    Classe para detecção de movimento entre frames.
    Utiliza técnicas de processamento de imagem para detectar diferenças significativas.
    """
    
    def __init__(self, threshold=25.0, area_minima=500.0, desenhar_contornos=True):
        """
        Inicializa o detector de movimento
        
        Args:
            threshold: Limiar para considerar movimento (quanto menor, mais sensível)
            area_minima: Área mínima para considerar como movimento válido
            desenhar_contornos: Se deve desenhar contornos nos frames com movimento
        """
        self.threshold = threshold
        self.area_minima = area_minima
        self.desenhar_contornos = desenhar_contornos
        logger.info(f"Detector de movimento inicializado: threshold={threshold}, area_minima={area_minima}")
    
    def detectar(self, frame_atual, frame_anterior):
        """
        Detecta movimento entre dois frames
        
        Args:
            frame_atual: Frame atual
            frame_anterior: Frame anterior para comparação
            
        Returns:
            Tupla (movimento_detectado, area_movimento, frame_marcado)
        """
        # Converter para escala de cinza
        gray_atual = cv2.cvtColor(frame_atual, cv2.COLOR_BGR2GRAY)
        gray_anterior = cv2.cvtColor(frame_anterior, cv2.COLOR_BGR2GRAY)
        
        # Aplicar desfoque gaussiano para reduzir ruído
        gray_atual = cv2.GaussianBlur(gray_atual, (21, 21), 0)
        gray_anterior = cv2.GaussianBlur(gray_anterior, (21, 21), 0)
        
        # Calcular diferença absoluta entre frames
        frame_delta = cv2.absdiff(gray_anterior, gray_atual)
        
        # Aplicar limiar para destacar diferenças significativas
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilatar para preencher buracos
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Encontrar contornos
        contornos, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Criar cópia do frame para desenhar
        frame_marcado = frame_atual.copy()
        
        # Variáveis para controle
        movimento_detectado = False
        area_total = 0
        contornos_validos = 0
        
        # Processar contornos encontrados
        for contorno in contornos:
            area = cv2.contourArea(contorno)
            
            # Verificar se área é maior que o mínimo
            if area < self.area_minima:
                continue
                
            contornos_validos += 1
            area_total += area
            
            # Desenhar contorno se configurado
            if self.desenhar_contornos:
                (x, y, w, h) = cv2.boundingRect(contorno)
                cv2.rectangle(frame_marcado, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame_marcado, f"Area: {area:.0f}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Verificar se área total é maior que o threshold
        movimento_detectado = area_total > self.threshold
        
        # Adicionar informações no frame
        if self.desenhar_contornos:
            info_text = f"Movimento: {'SIM' if movimento_detectado else 'NAO'} | Area: {area_total:.0f} | Threshold: {self.threshold}"
            cv2.putText(frame_marcado, info_text, (10, 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Logar detalhes da detecção
        if movimento_detectado:
            logger.debug(f"Movimento detectado: área={area_total:.0f}, contornos={contornos_validos}, threshold={self.threshold}")
        elif contornos_validos > 0:
            logger.debug(f"Movimento abaixo do threshold: área={area_total:.0f}, contornos={contornos_validos}, threshold={self.threshold}")
        
        return movimento_detectado, area_total, frame_marcado
    
    def salvar_frame_movimento(self, frame, movimento_area, diretorio="capturas/movimento"):
        """
        Salva o frame com movimento detectado
        
        Args:
            frame: Frame a ser salvo
            movimento_area: Área do movimento detectado
            diretorio: Diretório onde salvar o frame
            
        Returns:
            str: Caminho do arquivo salvo
        """
        import os
        
        # Criar diretório se não existir
        os.makedirs(diretorio, exist_ok=True)
        
        # Gerar nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Milissegundos
        filename = f"{diretorio}/movimento_{movimento_area:.0f}_{timestamp}.jpg"
        
        # Salvar imagem
        cv2.imwrite(filename, frame)
        
        logger.info(f"Frame de movimento salvo: {filename}")
        return filename 