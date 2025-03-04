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
    """Classe para detecção de movimento em frames de vídeo"""
    
    def __init__(self, threshold=1000, area_minima=500, desenhar_contornos=True):
        """
        Inicializa o detector de movimento com os parâmetros especificados
        
        Args:
            threshold: Limiar de área total para considerar movimento
            area_minima: Área mínima de um contorno para ser considerado movimento
            desenhar_contornos: Se deve desenhar retângulos nos contornos detectados
        """
        self.threshold = threshold
        self.area_minima = area_minima
        self.desenhar_contornos = desenhar_contornos
        logger.info(f"Detector de movimento inicializado: threshold={threshold}, area_minima={area_minima}")
    
    def detectar(self, frame1, frame2):
        """
        Detecta movimento entre dois frames consecutivos
        
        Args:
            frame1: Frame atual
            frame2: Frame anterior
            
        Returns:
            tuple: (movimento_detectado, movimento_area, frame_com_marcacoes)
        """
        if frame1 is None or frame2 is None:
            return False, 0, frame1
            
        try:
            # Converter para escala de cinza
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # Aplicar blur para reduzir ruído
            gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
            gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
            
            # Calcular diferença absoluta entre os frames
            frame_diff = cv2.absdiff(gray1, gray2)
            
            # Aplicar threshold para destacar áreas com movimento
            thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
            
            # Dilatar o threshold para preencher buracos
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            movimento_detectado = False
            movimento_area = 0
            
            # Criar uma cópia do frame para desenhar
            frame_marcado = frame1.copy() if self.desenhar_contornos else frame1
            
            # Verificar se há contornos significativos
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > self.area_minima:  # Filtrar contornos pequenos (ruído)
                    movimento_area += area
                    
                    # Desenhar retângulo ao redor do movimento
                    if self.desenhar_contornos:
                        (x, y, w, h) = cv2.boundingRect(contour)
                        cv2.rectangle(frame_marcado, (x, y), (x + w, y + h), COR_VERDE, 2)
            
            # Verificar se a área total de movimento é significativa
            if movimento_area > self.threshold:
                movimento_detectado = True
                
                # Adicionar texto indicando movimento
                if self.desenhar_contornos:
                    cv2.putText(
                        frame_marcado, 
                        f"Movimento: {movimento_area:.0f}", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        1, 
                        COR_VERMELHO, 
                        2
                    )
                
                logger.debug(f"Movimento detectado: área={movimento_area:.0f}, threshold={self.threshold}")
            
            return movimento_detectado, movimento_area, frame_marcado
            
        except Exception as e:
            logger.error(f"Erro ao detectar movimento: {str(e)}")
            return False, 0, frame1
    
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