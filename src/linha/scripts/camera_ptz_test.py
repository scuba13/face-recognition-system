import time
import logging
from onvif import ONVIFCamera
import cv2
import threading
import subprocess
import os
import signal
import sys
import datetime
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração da câmera
CAMERA_IP = "192.168.0.130"
ONVIF_PORT = 6688  # Porta ONVIF confirmada
RTSP_PORT = 8554   # Porta RTSP para streaming
USERNAME = "admin"
PASSWORD = "admin123456"

# Variáveis globais para controle do stream de vídeo
stream_process = None

def obter_posicao_atual(ptz, profile_token):
    """
    Obtém a posição atual da câmera
    """
    try:
        status = ptz.GetStatus({'ProfileToken': profile_token})
        if status and hasattr(status, 'Position') and hasattr(status.Position, 'PanTilt'):
            pan = status.Position.PanTilt.x
            tilt = status.Position.PanTilt.y
            return pan, tilt
        else:
            print("Não foi possível obter a posição atual")
            return None, None
    except Exception as e:
        print(f"Erro ao obter posição: {str(e)}")
        return None, None

def parar_camera(ptz, profile_token):
    """
    Para qualquer movimento atual da câmera
    """
    try:
        print("Parando qualquer movimento atual...")
        ptz.Stop({'ProfileToken': profile_token})
        time.sleep(2)  # Aguardar a parada
        print("Câmera parada.")
        return True
    except Exception as e:
        print(f"Erro ao parar câmera: {str(e)}")
        return False

def centralizar_camera(ptz, profile_token):
    """
    Centraliza a câmera (move para posição 0/0)
    """
    try:
        # Obter posição atual
        pan_atual, tilt_atual = obter_posicao_atual(ptz, profile_token)
        if pan_atual is None or tilt_atual is None:
            print("Não foi possível obter a posição atual para centralizar")
            return False
            
        print(f"Posição atual: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
        
        # Verificar se já está na posição central
        if abs(pan_atual) < 0.05 and abs(tilt_atual) < 0.05:
            print("Câmera já está na posição central (0/0)")
            return True
            
        print("\n>>> CENTRALIZANDO CÂMERA (POSIÇÃO 0/0) <<<")
        
        # Abordagem direta: mover diretamente para o centro usando AbsoluteMove
        try:
            print("Tentando mover diretamente para o centro usando AbsoluteMove...")
            
            # Criar request para movimento absoluto
            request = ptz.create_type('AbsoluteMove')
            request.ProfileToken = profile_token
            
            # Configurar posição alvo (0,0)
            request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Position.PanTilt.x = 0.0
            request.Position.PanTilt.y = 0.0
            
            # Configurar velocidade máxima
            request.Speed = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Speed.PanTilt.x = 1.0
            request.Speed.PanTilt.y = 1.0
            
            print("Movendo para posição central (0/0)...")
            ptz.AbsoluteMove(request)
            
            # Aguardar o movimento
            print("Aguardando 10 segundos para centralização...")
            time.sleep(10)
            
            # Parar movimento e verificar posição
            ptz.Stop({'ProfileToken': profile_token})
            time.sleep(2)
            
            # Verificar se chegou na posição central
            pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
            print(f"Posição após AbsoluteMove: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
            
            if abs(pan_final) < 0.1 and abs(tilt_final) < 0.1:
                print("Câmera centralizada com sucesso usando AbsoluteMove!")
                return True
            else:
                print("AbsoluteMove não conseguiu centralizar. Tentando método alternativo...")
        except Exception as e:
            print(f"Erro ao usar AbsoluteMove: {str(e)}. Tentando método alternativo...")
        
        # Método alternativo: usar movimentos relativos curtos
        print("\n>>> USANDO MÉTODO ALTERNATIVO PARA CENTRALIZAR <<<")
        
        # Centralizar horizontalmente (Pan)
        if abs(pan_atual) > 0.05:
            # Determinar direção para movimento horizontal
            direcao_horizontal = "direita" if pan_atual < 0 else "esquerda"
            velocidade_horizontal = 1.0 if pan_atual < 0 else -1.0
            
            print(f"Movendo para {direcao_horizontal} para centralizar horizontalmente...")
            
            # Criar request para movimento contínuo
            request = ptz.create_type('ContinuousMove')
            request.ProfileToken = profile_token
            
            # Obter status atual para usar como base para a velocidade
            status = ptz.GetStatus({'ProfileToken': profile_token})
            request.Velocity = status.Position
            
            # Configurar velocidade horizontal (máxima)
            request.Velocity.PanTilt.x = velocidade_horizontal
            request.Velocity.PanTilt.y = 0.0
            
            # Calcular tempo aproximado para centralizar
            # Ajuste: usar metade da distância para evitar ultrapassar o centro
            tempo_horizontal = abs(pan_atual) * 5  # 5 segundos por unidade de distância
            
            print(f"Iniciando movimento horizontal (velocidade: {abs(velocidade_horizontal)})...")
            ptz.ContinuousMove(request)
            
            print(f"Aguardando {tempo_horizontal:.1f} segundos...")
            time.sleep(tempo_horizontal)
            
            print("Parando movimento horizontal...")
            ptz.Stop({'ProfileToken': profile_token})
            time.sleep(2)
        
        # Verificar posição após movimento horizontal
        pan_atual, tilt_atual = obter_posicao_atual(ptz, profile_token)
        print(f"Posição após movimento horizontal: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
        
        # Centralizar verticalmente (Tilt)
        if abs(tilt_atual) > 0.05:
            # Determinar direção para movimento vertical
            direcao_vertical = "cima" if tilt_atual < 0 else "baixo"
            velocidade_vertical = 1.0 if tilt_atual < 0 else -1.0
            
            print(f"Movendo para {direcao_vertical} para centralizar verticalmente...")
            
            # Criar request para movimento contínuo
            request = ptz.create_type('ContinuousMove')
            request.ProfileToken = profile_token
            
            # Obter status atual para usar como base para a velocidade
            status = ptz.GetStatus({'ProfileToken': profile_token})
            request.Velocity = status.Position
            
            # Configurar velocidade vertical (máxima)
            request.Velocity.PanTilt.x = 0.0
            request.Velocity.PanTilt.y = velocidade_vertical
            
            # Calcular tempo aproximado para centralizar
            # Ajuste: usar metade da distância para evitar ultrapassar o centro
            tempo_vertical = abs(tilt_atual) * 5  # 5 segundos por unidade de distância
            
            print(f"Iniciando movimento vertical (velocidade: {abs(velocidade_vertical)})...")
            ptz.ContinuousMove(request)
            
            print(f"Aguardando {tempo_vertical:.1f} segundos...")
            time.sleep(tempo_vertical)
            
            print("Parando movimento vertical...")
            ptz.Stop({'ProfileToken': profile_token})
            time.sleep(2)
        
        # Verificar posição final
        pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
        print(f"Posição final: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
        
        # Verificar se a centralização foi bem-sucedida
        if abs(pan_final) < 0.1 and abs(tilt_final) < 0.1:
            print("Câmera centralizada com sucesso!")
            return True
        else:
            print("Aviso: A câmera não chegou exatamente na posição central.")
            resposta = input("Deseja tentar novamente? (s/n): ")
            if resposta.lower() == 's':
                return centralizar_camera(ptz, profile_token)
            return False
    
    except Exception as e:
        print(f"Erro ao centralizar câmera: {str(e)}")
        return False

def mover_pan_absoluto(ptz, profile_token):
    """
    Move a câmera para uma posição absoluta de Pan e Tilt especificada pelo usuário
    """
    try:
        # Obter posição atual
        pan_atual, tilt_atual = obter_posicao_atual(ptz, profile_token)
        if pan_atual is None or tilt_atual is None:
            print("Não foi possível obter a posição atual")
            return False
            
        print(f"Posição atual: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
        
        # Solicitar ao usuário o valor de Pan desejado
        try:
            # Loop para ajuste interativo
            ajuste_concluido = False
            pan_alvo = pan_atual
            tilt_alvo = tilt_atual
            
            while not ajuste_concluido:
                # Exibir posição atual
                print(f"\nPosição atual: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
                
                # Menu de ajuste
                print("\nOpções de ajuste:")
                print("1 - Definir valor de Pan")
                print("2 - Definir valor de Tilt")
                print("3 - Mover para a posição definida")
                print("4 - Cancelar")
                
                # Exibir valores alvo atuais
                print(f"\nValores alvo: Pan={pan_alvo:.4f}, Tilt={tilt_alvo:.4f}")
                
                opcao = input("\nEscolha uma opção: ")
                
                if opcao == "1":
                    try:
                        pan_alvo = float(input("Digite o valor de Pan desejado (ex: 0.7 para 90° direita, -0.7 para 90° esquerda): "))
                    except ValueError:
                        print("Valor inválido. Use um número decimal.")
                
                elif opcao == "2":
                    try:
                        tilt_alvo = float(input("Digite o valor de Tilt desejado (ex: 0.5 para cima, -0.5 para baixo): "))
                    except ValueError:
                        print("Valor inválido. Use um número decimal.")
                
                elif opcao == "3":
                    ajuste_concluido = True
                
                elif opcao == "4":
                    print("Ajuste cancelado.")
                    return False
                
                else:
                    print("Opção inválida. Tente novamente.")
            
            # Verificar se já está na posição desejada
            if abs(pan_atual - pan_alvo) < 0.05 and abs(tilt_atual - tilt_alvo) < 0.05:
                print(f"Câmera já está na posição Pan = {pan_alvo:.4f}, Tilt = {tilt_alvo:.4f}")
                return True
                
            print(f"\n>>> MOVENDO PARA PAN = {pan_alvo:.4f}, TILT = {tilt_alvo:.4f} <<<")
            
            # Usar AbsoluteMove para mover para a posição específica
            try:
                # Criar request para movimento absoluto
                request = ptz.create_type('AbsoluteMove')
                request.ProfileToken = profile_token
                
                # Configurar posição alvo (pan_alvo, tilt_alvo)
                request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
                request.Position.PanTilt.x = pan_alvo  # Pan definido pelo usuário
                request.Position.PanTilt.y = tilt_alvo  # Tilt definido pelo usuário
                
                # Configurar velocidade
                request.Speed = ptz.GetStatus({'ProfileToken': profile_token}).Position
                request.Speed.PanTilt.x = 1.0
                request.Speed.PanTilt.y = 1.0
                
                print(f"Movendo para posição Pan = {pan_alvo:.4f}, Tilt = {tilt_alvo:.4f}...")
                
                # Iniciar movimento
                ptz.AbsoluteMove(request)
                
                # Aguardar o movimento (tempo estimado baseado na distância)
                distancia_pan = abs(pan_alvo - pan_atual)
                distancia_tilt = abs(tilt_alvo - tilt_atual)
                distancia_total = max(distancia_pan, distancia_tilt)
                tempo_estimado = distancia_total * 10  # Estimativa: 10 segundos para percorrer a distância máxima
                tempo_estimado = max(1, min(tempo_estimado, 15))  # Entre 1 e 15 segundos
                
                print(f"Aguardando {tempo_estimado:.1f} segundos para o movimento...")
                time.sleep(tempo_estimado)
                
                # Verificar posição final
                pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
                if pan_final is not None and tilt_final is not None:
                    print(f"Posição após AbsoluteMove: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
                    
                    # Verificar se chegou na posição desejada
                    if abs(pan_final - pan_alvo) < 0.1 and abs(tilt_final - tilt_alvo) < 0.1:
                        print(f"Câmera movida com sucesso para Pan = {pan_alvo:.4f}, Tilt = {tilt_alvo:.4f}!")
                    else:
                        print(f"AVISO: A câmera pode não ter chegado exatamente na posição desejada.")
                        print(f"Diferença: Pan={abs(pan_final - pan_alvo):.4f}, Tilt={abs(tilt_final - tilt_alvo):.4f}")
                
                print(f"\n>>> POSIÇÃO ATUAL: Pan={pan_final:.4f}, Tilt={tilt_final:.4f} <<<")
                return True
                
            except Exception as e:
                print(f"Erro durante o movimento: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Erro ao processar entrada do usuário: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Erro ao mover para posição absoluta: {str(e)}")
        return False

def mover_pan_90_direita(ptz, profile_token):
    """
    Move a câmera para a posição de 90 graus à direita (Pan = 0.7) monitorando a posição em tempo real
    """
    try:
        # Obter posição atual
        pan_atual, tilt_atual = obter_posicao_atual(ptz, profile_token)
        if pan_atual is None or tilt_atual is None:
            print("Não foi possível obter a posição atual")
            return False
            
        print(f"Posição atual: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
        
        # Valor fixo para 90 graus à direita
        pan_alvo = 0.7
        
        # Verificar se já está na posição desejada
        if abs(pan_atual - pan_alvo) < 0.05:
            print("Câmera já está na posição de 90 graus à direita (Pan = 0.7)")
            return True
            
        print("\n>>> MOVENDO PARA 90 GRAUS À DIREITA (PAN = 0.7) <<<")
        
        # Usar AbsoluteMove para mover para a posição específica
        try:
            # Criar request para movimento absoluto
            request = ptz.create_type('AbsoluteMove')
            request.ProfileToken = profile_token
            
            # Configurar posição alvo (0.7, tilt_atual)
            request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Position.PanTilt.x = pan_alvo  # Pan = 0.7 (90 graus à direita)
            request.Position.PanTilt.y = tilt_atual  # Manter o tilt atual
            
            # Configurar velocidade
            request.Speed = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Speed.PanTilt.x = 1.0
            request.Speed.PanTilt.y = 1.0
            
            print("Movendo para posição de 90 graus à direita...")
            ptz.AbsoluteMove(request)
            
            # Monitorar a posição em tempo real até chegar próximo da posição alvo
            start_time = time.time()
            max_time = 15  # Tempo máximo a aguardar em segundos
            threshold = 0.1  # Tolerância para considerar que chegou na posição
            
            print("Monitorando posição em tempo real...")
            while time.time() - start_time < max_time:
                pan_atual, _ = obter_posicao_atual(ptz, profile_token)
                if pan_atual is None:
                    time.sleep(0.1)
                    continue
                    
                # Verificar se chegamos próximo ao alvo
                if abs(pan_atual - pan_alvo) < threshold:
                    print(f"Posição alvo alcançada! Pan={pan_atual:.4f}")
                    break
                    
                # Aguardar brevemente antes de verificar novamente
                time.sleep(0.1)
            
            # Verificar se chegou na posição desejada
            pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
            print(f"Posição final: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
            
            return True
                
        except Exception as e:
            print(f"Erro ao usar AbsoluteMove: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Erro ao mover para 90 graus à direita: {str(e)}")
        return False

def mover_pan_90_esquerda(ptz, profile_token):
    """
    Move a câmera para a posição de 90 graus à esquerda (Pan = -0.7) monitorando a posição em tempo real
    """
    try:
        # Obter posição atual
        pan_atual, tilt_atual = obter_posicao_atual(ptz, profile_token)
        if pan_atual is None or tilt_atual is None:
            print("Não foi possível obter a posição atual")
            return False
            
        print(f"Posição atual: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
        
        # Valor fixo para 90 graus à esquerda
        pan_alvo = -0.7
        
        # Verificar se já está na posição desejada
        if abs(pan_atual - pan_alvo) < 0.05:
            print("Câmera já está na posição de 90 graus à esquerda (Pan = -0.7)")
            return True
            
        print("\n>>> MOVENDO PARA 90 GRAUS À ESQUERDA (PAN = -0.7) <<<")
        
        # Usar AbsoluteMove para mover para a posição específica
        try:
            # Criar request para movimento absoluto
            request = ptz.create_type('AbsoluteMove')
            request.ProfileToken = profile_token
            
            # Configurar posição alvo (-0.7, tilt_atual)
            request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Position.PanTilt.x = pan_alvo  # Pan = -0.7 (90 graus à esquerda)
            request.Position.PanTilt.y = tilt_atual  # Manter o tilt atual
            
            # Configurar velocidade
            request.Speed = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Speed.PanTilt.x = 1.0
            request.Speed.PanTilt.y = 1.0
            
            print("Movendo para posição de 90 graus à esquerda...")
            ptz.AbsoluteMove(request)
            
            # Monitorar a posição em tempo real até chegar próximo da posição alvo
            start_time = time.time()
            max_time = 15  # Tempo máximo a aguardar em segundos
            threshold = 0.1  # Tolerância para considerar que chegou na posição
            
            print("Monitorando posição em tempo real...")
            while time.time() - start_time < max_time:
                pan_atual, _ = obter_posicao_atual(ptz, profile_token)
                if pan_atual is None:
                    time.sleep(0.1)
                    continue
                    
                # Verificar se chegamos próximo ao alvo
                if abs(pan_atual - pan_alvo) < threshold:
                    print(f"Posição alvo alcançada! Pan={pan_atual:.4f}")
                    break
                    
                # Aguardar brevemente antes de verificar novamente
                time.sleep(0.1)
            
            # Verificar se chegou na posição desejada
            pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
            print(f"Posição final: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
            
            return True
                
        except Exception as e:
            print(f"Erro ao usar AbsoluteMove: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Erro ao mover para 90 graus à esquerda: {str(e)}")
        return False

def criar_preset(ptz, profile_token):
    """
    Cria um preset (posição salva) com a posição atual da câmera
    """
    try:
        # Obter posição atual
        pan_atual, tilt_atual = obter_posicao_atual(ptz, profile_token)
        if pan_atual is None or tilt_atual is None:
            print("Não foi possível obter a posição atual")
            return False
            
        print(f"Posição atual: Pan={pan_atual:.4f}, Tilt={tilt_atual:.4f}")
        
        # Solicitar nome para o preset
        nome_preset = input("Digite um nome para este preset: ")
        if not nome_preset:
            print("Nome inválido. Operação cancelada.")
            return False
        
        try:
            # Criar request para definir preset
            request = ptz.create_type('SetPreset')
            request.ProfileToken = profile_token
            request.PresetName = nome_preset
            
            # Enviar request para criar preset
            print(f"Criando preset '{nome_preset}' na posição atual...")
            response = ptz.SetPreset(request)
            
            if hasattr(response, 'PresetToken'):
                print(f"Preset '{nome_preset}' criado com sucesso! (Token: {response.PresetToken})")
                return True
            else:
                print("Não foi possível criar o preset. Resposta sem token.")
                return False
                
        except Exception as e:
            print(f"Erro ao criar preset: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Erro ao criar preset: {str(e)}")
        return False

def listar_presets(ptz, profile_token):
    """
    Lista todos os presets disponíveis na câmera
    """
    try:
        # Criar request para obter presets
        request = ptz.create_type('GetPresets')
        request.ProfileToken = profile_token
        
        # Enviar request para obter presets
        print("Obtendo lista de presets disponíveis...")
        presets = ptz.GetPresets(request)
        
        if not presets:
            print("Nenhum preset encontrado.")
            return []
        
        print("\n=== PRESETS DISPONÍVEIS ===")
        for i, preset in enumerate(presets, 1):
            nome = preset.Name if hasattr(preset, 'Name') and preset.Name else "Sem nome"
            token = preset.token if hasattr(preset, 'token') else "Desconhecido"
            print(f"{i}. Nome: {nome} (Token: {token})")
        
        return presets
        
    except Exception as e:
        print(f"Erro ao listar presets: {str(e)}")
        return []

def ir_para_preset(ptz, profile_token):
    """
    Move a câmera para um preset selecionado
    """
    try:
        # Listar presets disponíveis
        presets = listar_presets(ptz, profile_token)
        
        if not presets:
            return False
        
        # Solicitar seleção do preset
        try:
            indice = int(input("\nDigite o número do preset desejado: "))
            if indice < 1 or indice > len(presets):
                print("Índice inválido.")
                return False
            
            preset_selecionado = presets[indice-1]
            token_preset = preset_selecionado.token if hasattr(preset_selecionado, 'token') else None
            nome_preset = preset_selecionado.Name if hasattr(preset_selecionado, 'Name') else "Sem nome"
            
            if not token_preset:
                print("Token do preset não encontrado.")
                return False
            
            # Criar request para ir para o preset
            request = ptz.create_type('GotoPreset')
            request.ProfileToken = profile_token
            request.PresetToken = token_preset
            
            # Configurar velocidade
            request.Speed = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Speed.PanTilt.x = 1.0
            request.Speed.PanTilt.y = 1.0
            
            print(f"Movendo para o preset '{nome_preset}'...")
            ptz.GotoPreset(request)
            
            # Aguardar o movimento
            print("Aguardando 10 segundos para o movimento...")
            time.sleep(10)
            
            # Parar movimento e verificar posição
            ptz.Stop({'ProfileToken': profile_token})
            time.sleep(2)
            
            # Obter posição final
            pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
            print(f"Posição após movimento: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
            
            print(f"Câmera movida para o preset '{nome_preset}'.")
            return True
            
        except ValueError:
            print("Entrada inválida. Digite um número.")
            return False
            
    except Exception as e:
        print(f"Erro ao ir para preset: {str(e)}")
        return False

def remover_preset(ptz, profile_token):
    """
    Remove um preset selecionado
    """
    try:
        # Listar presets disponíveis
        presets = listar_presets(ptz, profile_token)
        
        if not presets:
            return False
        
        # Solicitar seleção do preset
        try:
            indice = int(input("\nDigite o número do preset que deseja remover: "))
            if indice < 1 or indice > len(presets):
                print("Índice inválido.")
                return False
            
            preset_selecionado = presets[indice-1]
            token_preset = preset_selecionado.token if hasattr(preset_selecionado, 'token') else None
            nome_preset = preset_selecionado.Name if hasattr(preset_selecionado, 'Name') else "Sem nome"
            
            if not token_preset:
                print("Token do preset não encontrado.")
                return False
            
            # Confirmar remoção
            confirmacao = input(f"Tem certeza que deseja remover o preset '{nome_preset}'? (s/n): ")
            if confirmacao.lower() != 's':
                print("Operação cancelada.")
                return False
            
            # Criar request para remover o preset
            request = ptz.create_type('RemovePreset')
            request.ProfileToken = profile_token
            request.PresetToken = token_preset
            
            print(f"Removendo o preset '{nome_preset}'...")
            ptz.RemovePreset(request)
            
            print(f"Preset '{nome_preset}' removido com sucesso!")
            return True
            
        except ValueError:
            print("Entrada inválida. Digite um número.")
            return False
            
    except Exception as e:
        print(f"Erro ao remover preset: {str(e)}")
        return False

def capturar_posicao(ptz, profile_token):
    """
    Captura a posição atual da câmera e retorna um timestamp
    """
    pan, tilt = obter_posicao_atual(ptz, profile_token)
    timestamp = time.time()
    return {"pan": pan, "tilt": tilt, "timestamp": timestamp}

def teste_velocidade_movimento(ptz, profile_token):
    """
    Testa a velocidade de movimento da câmera
    """
    try:
        print("\n=== INICIANDO TESTE DE VELOCIDADE ===")
        print("Este teste medirá o tempo para a câmera se mover de 90° à direita para 90° à esquerda")
        
        # Primeiro, mover para 90 graus à direita (posição inicial)
        print("\n1. Movendo para posição inicial (90° à direita)...")
        if not mover_pan_90_direita(ptz, profile_token):
            print("Falha ao mover para posição inicial. Abortando teste.")
            return False
            
        # Aguardar um momento na posição inicial
        print("\nAguardando 3 segundos na posição inicial...")
        time.sleep(3)
        
        # Verificar posição inicial
        pan_inicial, tilt_inicial = obter_posicao_atual(ptz, profile_token)
        if pan_inicial is None or tilt_inicial is None:
            print("Não foi possível obter a posição inicial. Abortando teste.")
            return False
            
        print(f"Posição inicial confirmada: Pan={pan_inicial:.4f}, Tilt={tilt_inicial:.4f}")
        
        # Agora, mover para 90 graus à esquerda e medir o tempo
        print("\n2. Iniciando movimento para 90° à esquerda...")
        
        # Usar AbsoluteMove para mover para a posição específica
        try:
            # Criar request para movimento absoluto
            request = ptz.create_type('AbsoluteMove')
            request.ProfileToken = profile_token
            
            # Configurar posição alvo (-0.7, tilt_atual)
            request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Position.PanTilt.x = -0.7  # Pan = -0.7 (90 graus à esquerda)
            request.Position.PanTilt.y = tilt_inicial  # Manter o tilt atual
            
            # Configurar velocidade máxima
            request.Speed = ptz.GetStatus({'ProfileToken': profile_token}).Position
            request.Speed.PanTilt.x = 1.0
            request.Speed.PanTilt.y = 1.0
            
            # Iniciar cronômetro
            print("Iniciando cronômetro...")
            tempo_inicio = time.time()
            
            # Iniciar movimento
            ptz.AbsoluteMove(request)
            
            # Aguardar o movimento (tempo máximo de 20 segundos)
            print("Movimento iniciado. Aguardando conclusão...")
            tempo_maximo = 20
            movimento_em_andamento = True
            
            while movimento_em_andamento and (time.time() - tempo_inicio < tempo_maximo):
                # Verificar posição atual
                pan_atual, _ = obter_posicao_atual(ptz, profile_token)
                if pan_atual is None:
                    continue
                    
                # Verificar se chegou próximo da posição alvo
                if abs(pan_atual - (-0.7)) < 0.05:
                    print(f"Chegou próximo da posição alvo: Pan={pan_atual:.4f}")
                    movimento_em_andamento = False
                    break
                    
                # Pequena pausa para não sobrecarregar
                time.sleep(0.2)
            
            # Registrar tempo final
            tempo_fim = time.time()
            
            # Parar movimento e verificar posição final
            ptz.Stop({'ProfileToken': profile_token})
            time.sleep(2)
            
            # Verificar posição final
            pan_final, tilt_final = obter_posicao_atual(ptz, profile_token)
            print(f"Posição final: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
            
            # Calcular tempo, distância e velocidade
            tempo_movimento = tempo_fim - tempo_inicio
            distancia_angular = abs(pan_final - pan_inicial)
            velocidade_media = distancia_angular / tempo_movimento if tempo_movimento > 0 else 0
            
            # Exibir resultados
            print("\n=== RESULTADOS DO TESTE DE VELOCIDADE ===")
            print(f"Posição inicial: Pan={pan_inicial:.4f}, Tilt={tilt_inicial:.4f}")
            print(f"Posição final: Pan={pan_final:.4f}, Tilt={tilt_final:.4f}")
            print(f"Tempo de movimento: {tempo_movimento:.4f} segundos")
            print(f"Distância angular percorrida: {distancia_angular:.4f}")
            print(f"Velocidade média: {velocidade_media:.4f} unidades/segundo")
            
            # Retornar para a posição inicial (opcional)
            resposta = input("\nDeseja retornar à posição inicial (90° à direita)? (s/n): ")
            if resposta.lower() == 's':
                print("Retornando à posição inicial...")
                mover_pan_90_direita(ptz, profile_token)
            
            return True
            
        except Exception as e:
            print(f"Erro durante teste de velocidade: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Erro ao executar teste de velocidade: {str(e)}")
        return False

def iniciar_stream_video(rtsp_url=None):
    """
    Inicia o stream de vídeo da câmera em uma janela separada usando um processo externo
    """
    global stream_process
    
    # Parar qualquer stream existente
    parar_stream_video()
    
    # Se não for fornecida uma URL, usar a URL padrão
    if rtsp_url is None:
        rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile0"
    
    print(f"Iniciando visualização do stream: {rtsp_url}")
    
    try:
        # Verificar se estamos no Windows ou Unix
        if os.name == 'nt':  # Windows
            # Criar um processo separado para exibir o stream com ffplay ou VLC
            try:
                # Tentar com VLC primeiro
                command = f'start "Camera PTZ Stream" "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe" "{rtsp_url}" --no-video-title-show'
                stream_process = subprocess.Popen(command, shell=True)
                print("Stream iniciado com VLC.")
            except:
                # Tentar com ffplay como alternativa
                command = f'start ffplay -fflags nobuffer -flags low_delay -framedrop -rtsp_transport tcp -i "{rtsp_url}" -window_title "Camera PTZ Stream" -x 800 -y 600'
                stream_process = subprocess.Popen(command, shell=True)
                print("Stream iniciado com FFplay.")
        else:  # Unix/Mac
            # Iniciar o stream em um processo separado
            # Tentar abrir com VLC
            try:
                command = ['vlc', rtsp_url, '--no-audio', '--video-on-top', '--width=800', '--height=600']
                stream_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("Stream iniciado com VLC.")
            except:
                # Tentar usar ffplay como alternativa
                try:
                    command = ['ffplay', '-fflags', 'nobuffer', '-flags', 'low_delay', '-framedrop', '-rtsp_transport', 'tcp', '-i', rtsp_url, '-window_title', 'Camera PTZ Stream', '-x', '800', '-y', '600']
                    stream_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("Stream iniciado com FFplay.")
                except Exception as e:
                    print(f"Erro ao iniciar players externos: {str(e)}")
                    print("Tentando abrir com o método OpenCV em modo simplificado...")
                    
                    # Como última opção, tentar abrir o próprio OpenCV em um processo separado
                    command = [sys.executable, '-c', 
                            f'import cv2; cap = cv2.VideoCapture("{rtsp_url}", cv2.CAP_FFMPEG); ' + 
                            'cap.set(cv2.CAP_PROP_BUFFERSIZE, 1); ' +
                            'import time; ' +
                            'if not cap.isOpened(): print("Erro ao abrir stream"); exit(1); ' +
                            'print("Stream aberto com sucesso"); ' +
                            'cv2.namedWindow("Camera PTZ Stream", cv2.WINDOW_NORMAL); ' +
                            'cv2.resizeWindow("Camera PTZ Stream", 800, 600); ' +
                            'while True: ' +
                            '    ret, frame = cap.read(); ' +
                            '    if not ret: time.sleep(0.1); continue; ' +
                            '    cv2.imshow("Camera PTZ Stream", frame); ' +
                            '    if cv2.waitKey(1) & 0xFF == 27: break; ' +
                            'cv2.destroyAllWindows(); cap.release()']
                    
                    stream_process = subprocess.Popen(command)
                    print("Stream iniciado com OpenCV standalone.")
        
        print("Visualização iniciada em janela separada. Feche a janela para parar a visualização.")
        time.sleep(1)  # Dar tempo para o processo iniciar
        return True
    except Exception as e:
        print(f"Erro ao iniciar stream de vídeo: {str(e)}")
        return False

def parar_stream_video():
    """
    Para o stream de vídeo da câmera
    """
    global stream_process
    
    if stream_process is not None:
        try:
            # Encerrar o processo
            if os.name == 'nt':  # Windows
                subprocess.run(f'taskkill /F /PID {stream_process.pid} /T', shell=True, stderr=subprocess.PIPE)
            else:  # Unix/Mac
                os.killpg(os.getpgid(stream_process.pid), signal.SIGTERM)
        except:
            # Tentar método alternativo
            try:
                stream_process.terminate()
                stream_process.wait(timeout=1)
            except:
                try:
                    stream_process.kill()
                except:
                    pass
        
        stream_process = None
        print("Stream de vídeo parado")

def capturar_frame_e_salvar(rtsp_url, nome_arquivo, tempo_estabilizacao=0.1):
    """
    Captura um frame do stream RTSP e salva como imagem com alta qualidade
    Implementa múltiplas estratégias para garantir uma captura bem-sucedida
    """
    try:
        # Garantir que o diretório exista
        diretorio = "frames_capturados"
        if not os.path.exists(diretorio):
            os.makedirs(diretorio)
        
        # Caminho completo do arquivo
        caminho_arquivo = os.path.join(diretorio, nome_arquivo)
        
        # Número de tentativas de conexão
        max_tentativas_conexao = 4  # Aumentado para 4 tentativas
        
        # Tentar diferentes estratégias de conexão
        melhor_frame_global = None
        melhor_qualidade_global = 0
        
        for tentativa in range(max_tentativas_conexao):
            print(f"\nTentativa de captura #{tentativa+1}...")
            
            # Adicionar um tempo de estabilização dinâmico, aumentando a cada tentativa
            tempo_estab_ajustado = tempo_estabilizacao * (tentativa + 1.5)  # Fator aumentado para 1.5
            if tempo_estab_ajustado > 0:
                print(f"Aguardando {tempo_estab_ajustado:.1f}s para estabilização da câmera...")
                time.sleep(tempo_estab_ajustado)
            
            # Conectar à câmera com configurações aprimoradas
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            
            # Configurações para melhorar qualidade
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 5)  # Aumentar buffer para ter frames mais estáveis
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # Full HD
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
            if not cap.isOpened():
                print(f"Erro ao abrir stream RTSP na tentativa {tentativa+1}")
                time.sleep(1)  # Esperar um pouco antes da próxima tentativa
                continue
            
            # Mudar a abordagem para descartar frames iniciais
            print(f"Descartando frames iniciais...")
            frames_descartados = 0
            max_frames_descarte = 20  # Aumentado para 20 frames descartados
            
            while frames_descartados < max_frames_descarte:
                ret = cap.grab()  # Mais rápido que read() pois não decodifica o frame
                if not ret:
                    time.sleep(0.05)
                    continue
                frames_descartados += 1
                
                # A cada 5 frames, tentar ler um para verificar qualidade
                if frames_descartados % 5 == 0:
                    ret, frame_teste = cap.retrieve()
                    if ret:
                        gray = cv2.cvtColor(frame_teste, cv2.COLOR_BGR2GRAY)
                        std_dev = np.std(gray)
                        print(f"Frame de teste #{frames_descartados//5}: Variação={std_dev:.2f}")
                        # Se a qualidade já estiver boa, podemos parar o descarte
                        if std_dev > 30:
                            print("Frame de teste com boa variação detectado, continuando com a captura")
                            break
            
            # Tentar capturar mais frames para ter mais opções de escolha
            frames = []
            qualidades = []
            nitidez_valores = []
            variacao_valores = []
            num_frames_por_tentativa = 15  # Aumentado para 15 frames
            intervalo_entre_frames = 0.2  # Aumentado para dar mais tempo entre capturas
            
            print(f"Capturando {num_frames_por_tentativa} frames...")
            
            for i in range(num_frames_por_tentativa):
                ret, frame = cap.read()
                if ret:
                    # Verificar se o frame tem conteúdo (não é completamente preto/branco/estático)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    std_dev = np.std(gray)  # Desvio padrão dos pixels (mede variação)
                    
                    # Um frame com pouca variação provavelmente é inválido
                    if std_dev < 15:  # Limiar para considerar frame muito uniforme/vazio
                        print(f"Frame {i+1} descartado (baixa variação: {std_dev:.2f})")
                        continue
                    
                    # Calcular nitidez usando Laplaciano - valores mais altos = mais nítido
                    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                    
                    # Incluir informações de bordas
                    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3).var()
                    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3).var()
                    edge_content = (sobel_x + sobel_y) / 2
                    
                    # Calcular uma pontuação ponderada
                    qualidade = lap_var * 0.7 + edge_content * 0.2 + std_dev * 0.1
                    
                    print(f"Frame {i+1}: Nitidez={lap_var:.2f}, Bordas={edge_content:.2f}, Variação={std_dev:.2f}, Qualidade={qualidade:.2f}")
                    
                    frames.append(frame)
                    qualidades.append(qualidade)
                    nitidez_valores.append(lap_var)
                    variacao_valores.append(std_dev)
                else:
                    print(f"Falha ao ler frame {i+1}")
                
                # Intervalo entre capturas para ter frames diferentes
                time.sleep(intervalo_entre_frames)
            
            # Liberar recursos
            cap.release()
            
            # Verificar se conseguimos capturar frames válidos
            if len(frames) == 0:
                print("Não foi possível capturar frames válidos nesta tentativa")
                continue  # Tentar novamente
            
            # Filtrar para manter apenas frames com qualidade aceitável
            if len(frames) > 1:
                media_qualidade = sum(qualidades) / len(qualidades)
                frames_filtrados = []
                qualidades_filtradas = []
                indices_mantidos = []
                
                for i, (frame, qualidade) in enumerate(zip(frames, qualidades)):
                    # Manter apenas frames com qualidade acima de 85% da média
                    if qualidade >= media_qualidade * 0.85:
                        frames_filtrados.append(frame)
                        qualidades_filtradas.append(qualidade)
                        indices_mantidos.append(i)
                
                if len(frames_filtrados) > 0:
                    frames = frames_filtrados
                    qualidades = qualidades_filtradas
                    print(f"{len(frames)} frames mantidos após filtragem de qualidade: {[i+1 for i in indices_mantidos]}")
            
            # Escolher o frame com maior qualidade
            if frames:
                melhor_indice = qualidades.index(max(qualidades))
                melhor_frame = frames[melhor_indice]
                melhor_qualidade = qualidades[melhor_indice]
                
                print(f"Melhor frame selecionado: #{melhor_indice+1} (qualidade: {melhor_qualidade:.2f})")
                
                # Atualizar o melhor frame global se for melhor que o anterior
                if melhor_qualidade > melhor_qualidade_global:
                    melhor_frame_global = melhor_frame
                    melhor_qualidade_global = melhor_qualidade
                    print(f"Novo melhor frame global (qualidade: {melhor_qualidade_global:.2f})")
            
            # Determinar se a qualidade é aceitável
            qualidade_minima = 150  # Aumento do limiar mínimo
            if melhor_qualidade_global >= qualidade_minima:
                print(f"Qualidade satisfatória alcançada ({melhor_qualidade_global:.2f} >= {qualidade_minima})")
                break
            elif tentativa < max_tentativas_conexao-1:
                print(f"Qualidade abaixo do ideal ({melhor_qualidade_global:.2f} < {qualidade_minima})")
                print("Tentando novamente com tempo de estabilização maior...")
        
        # Verificar se temos um frame válido para salvar
        if melhor_frame_global is None:
            print("Não foi possível obter um frame de qualidade adequada após todas as tentativas")
            return False
        
        # Salvar o melhor frame global em formato PNG (sem perdas) e JPEG (compactado)
        # PNG para preservar qualidade exata
        caminho_png = os.path.join(diretorio, os.path.splitext(nome_arquivo)[0] + ".png")
        cv2.imwrite(caminho_png, melhor_frame_global)
        
        # JPEG com alta qualidade (95%)
        params_jpg = [cv2.IMWRITE_JPEG_QUALITY, 95]
        sucesso = cv2.imwrite(caminho_arquivo, melhor_frame_global, params_jpg)
        
        if sucesso:
            print(f"Frames salvos com sucesso:")
            print(f"- JPEG (95%): {nome_arquivo}")
            print(f"- PNG (sem perdas): {os.path.basename(caminho_png)}")
            return True
        else:
            print("Erro ao salvar frames")
            return False
            
    except Exception as e:
        print(f"Erro ao capturar frame: {str(e)}")
        import traceback
        print(f"Detalhes: {traceback.format_exc()}")
        return False

def teste_captura_extremos(ptz, profile_token):
    """
    Move a câmera para 90° à direita e depois para 90° à esquerda,
    capturando frames em cada posição com múltiplas tentativas e estratégias
    """
    try:
        print("\n=== INICIANDO TESTE DE CAPTURA NOS EXTREMOS ===")
        
        # Configurações iniciais
        rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile0"
        
        # Solicitar configurações do teste
        try:
            num_ciclos = int(input("Número de ciclos a realizar (padrão=3): ") or "3")
            if num_ciclos < 1:
                num_ciclos = 1
                
            tempo_estabilizacao = float(input("Tempo de estabilização base da imagem em segundos (padrão=1.5): ") or "1.5")
            if tempo_estabilizacao < 0:
                tempo_estabilizacao = 0
            
            # Verificar se já existe um stream ativo
            stream_ativo = stream_process is not None
            usar_stream_existente = False
            
            if stream_ativo:
                print("\nATENÇÃO: Um stream de vídeo está ativo. Isso pode afetar a velocidade de captura.")
                usar_stream_existente = input("Deseja parar o stream durante o teste para aumentar a velocidade? (s/n, padrão=s): ").lower() != 'n'
                
                if usar_stream_existente:
                    print("Mantendo o stream ativo durante o teste.")
                else:
                    print("Parando o stream para otimizar a captura...")
                    parar_stream_video()
            else:
                iniciar_stream = input("Deseja iniciar o stream de vídeo durante o teste? (s/n, padrão=n): ").lower() == 's'
                if iniciar_stream:
                    print("Iniciando stream de vídeo...")
                    iniciar_stream_video(rtsp_url)
                else:
                    print("Executando teste sem visualização do stream (captura mais rápida).")
                
            print(f"\nConfiguração: {num_ciclos} ciclos, {tempo_estabilizacao}s de estabilização base")
            
            # Configuração de otimização
            otimizar_por_posicao = input("Otimizar estabilização por posição? (s/n, padrão=s): ").lower() != 'n'
            
            # Valores iniciais de estabilização por posição
            tempos_estabilizacao = {
                "direita": tempo_estabilizacao,
                "esquerda": tempo_estabilizacao
            }
            
            if otimizar_por_posicao:
                print("\nA estabilização será otimizada automaticamente para cada posição")
                print("com base no sucesso das capturas anteriores.")
            
        except ValueError:
            print("Entrada inválida, usando valores padrão: 3 ciclos, 1.5s estabilização")
            num_ciclos = 3
            tempo_estabilizacao = 1.5
            otimizar_por_posicao = True
            tempos_estabilizacao = {
                "direita": tempo_estabilizacao,
                "esquerda": tempo_estabilizacao
            }
        
        # Iniciar o teste
        print(f"\nIniciando {num_ciclos} ciclos de captura...")
        start_time = time.time()
        frames_capturados = 0
        capturas_posicao = {"direita": 0, "esquerda": 0}
        
        # Registrar quais ciclos tiveram melhor qualidade
        qualidade_por_ciclo = {}
        
        for ciclo in range(1, num_ciclos+1):
            print(f"\n--- Ciclo {ciclo}/{num_ciclos} ---")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Mover para direita com verificação adicional
            print("\nMovendo para 90° à direita...")
            if not mover_pan_90_direita(ptz, profile_token):
                print("Erro ao mover para direita. Continuando para o próximo ciclo...")
                continue
            
            # Espera adicional para garantir que a câmera se estabilizou completamente
            print("Garantindo estabilização na posição...")
            time.sleep(0.5)  # Espera fixa adicional
            
            # Verificar se a câmera realmente chegou na posição desejada
            pan_atual, _ = obter_posicao_atual(ptz, profile_token)
            if abs(pan_atual - 0.7) > 0.1:
                print(f"AVISO: Posição não alcançada (Pan={pan_atual:.4f}). Ajustando...")
                # Tentar ajustar a posição
                request = ptz.create_type('AbsoluteMove')
                request.ProfileToken = profile_token
                request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
                request.Position.PanTilt.x = 0.7
                ptz.AbsoluteMove(request)
                time.sleep(2)  # Tempo adicional para o ajuste
            
            # Usar tempo de estabilização otimizado para esta posição
            tempo_estab_direita = tempos_estabilizacao["direita"]
            print(f"Usando tempo de estabilização para direita: {tempo_estab_direita:.2f}s")
            
            nome_arquivo_direita = f"direita_{ciclo}_{timestamp}.jpg"
            resultado_direita = capturar_frame_e_salvar(rtsp_url, nome_arquivo_direita, tempo_estab_direita)
            
            if resultado_direita:
                frames_capturados += 1
                capturas_posicao["direita"] += 1
                # Se captura foi bem sucedida mas estamos adiantados no processo, podemos reduzir o tempo
                if otimizar_por_posicao and ciclo > 1 and tempos_estabilizacao["direita"] > tempo_estabilizacao:
                    # Reduzir ligeiramente o tempo de estabilização (10%)
                    tempos_estabilizacao["direita"] *= 0.9
                    print(f"Reduzindo tempo de estabilização para direita: {tempos_estabilizacao['direita']:.2f}s")
            else:
                # Se falhou, aumentar o tempo para a próxima vez
                if otimizar_por_posicao:
                    tempos_estabilizacao["direita"] *= 1.5  # Aumentar 50%
                    print(f"Aumentando tempo de estabilização para direita: {tempos_estabilizacao['direita']:.2f}s")
            
            # Mover para esquerda com verificação adicional
            print("\nMovendo para 90° à esquerda...")
            if not mover_pan_90_esquerda(ptz, profile_token):
                print("Erro ao mover para esquerda. Continuando para o próximo ciclo...")
                continue
            
            # Espera adicional para garantir que a câmera se estabilizou completamente
            print("Garantindo estabilização na posição...")
            time.sleep(0.5)  # Espera fixa adicional
            
            # Verificar se a câmera realmente chegou na posição desejada
            pan_atual, _ = obter_posicao_atual(ptz, profile_token)
            if abs(pan_atual - (-0.7)) > 0.1:
                print(f"AVISO: Posição não alcançada (Pan={pan_atual:.4f}). Ajustando...")
                # Tentar ajustar a posição
                request = ptz.create_type('AbsoluteMove')
                request.ProfileToken = profile_token
                request.Position = ptz.GetStatus({'ProfileToken': profile_token}).Position
                request.Position.PanTilt.x = -0.7
                ptz.AbsoluteMove(request)
                time.sleep(2)  # Tempo adicional para o ajuste
            
            # Usar tempo de estabilização otimizado para esta posição
            tempo_estab_esquerda = tempos_estabilizacao["esquerda"]
            print(f"Usando tempo de estabilização para esquerda: {tempo_estab_esquerda:.2f}s")
            
            nome_arquivo_esquerda = f"esquerda_{ciclo}_{timestamp}.jpg"
            resultado_esquerda = capturar_frame_e_salvar(rtsp_url, nome_arquivo_esquerda, tempo_estab_esquerda)
            
            if resultado_esquerda:
                frames_capturados += 1
                capturas_posicao["esquerda"] += 1
                # Se captura foi bem sucedida mas estamos adiantados no processo, podemos reduzir o tempo
                if otimizar_por_posicao and ciclo > 1 and tempos_estabilizacao["esquerda"] > tempo_estabilizacao:
                    # Reduzir ligeiramente o tempo de estabilização (10%)
                    tempos_estabilizacao["esquerda"] *= 0.9
                    print(f"Reduzindo tempo de estabilização para esquerda: {tempos_estabilizacao['esquerda']:.2f}s")
            else:
                # Se falhou, aumentar o tempo para a próxima vez
                if otimizar_por_posicao:
                    tempos_estabilizacao["esquerda"] *= 1.5  # Aumentar 50%
                    print(f"Aumentando tempo de estabilização para esquerda: {tempos_estabilizacao['esquerda']:.2f}s")
            
            # Registrar resultado do ciclo
            qualidade_por_ciclo[ciclo] = {
                "direita": resultado_direita,
                "esquerda": resultado_esquerda,
                "total": int(resultado_direita) + int(resultado_esquerda)
            }
            
            # Mostrar resultados parciais
            sucessos_ciclo = int(resultado_direita) + int(resultado_esquerda)
            print(f"\nResultado do ciclo {ciclo}: {sucessos_ciclo}/2 capturas bem-sucedidas")
        
        # Calcular tempo total e exibir estatísticas
        tempo_total = time.time() - start_time
        tempo_por_ciclo = tempo_total / num_ciclos
        taxa_sucesso = (frames_capturados / (num_ciclos * 2)) * 100 if num_ciclos > 0 else 0
        
        # Resultados
        print("\n=== TESTE DE CAPTURA CONCLUÍDO ===")
        print(f"Total de ciclos realizados: {num_ciclos}")
        print(f"Frames capturados com sucesso: {frames_capturados}/{num_ciclos*2} ({taxa_sucesso:.1f}%)")
        print(f"  - Direita: {capturas_posicao['direita']}/{num_ciclos} ({capturas_posicao['direita']*100/num_ciclos:.1f}%)")
        print(f"  - Esquerda: {capturas_posicao['esquerda']}/{num_ciclos} ({capturas_posicao['esquerda']*100/num_ciclos:.1f}%)")
        print(f"Tempo total: {tempo_total:.2f} segundos")
        print(f"Tempo médio por ciclo: {tempo_por_ciclo:.2f} segundos")
        print(f"Velocidade: {(1/tempo_por_ciclo)*60:.1f} ciclos por minuto")
        
        # Mostrar resultados por ciclo
        print("\nResultado por ciclo:")
        for ciclo, resultado in qualidade_por_ciclo.items():
            print(f"  Ciclo {ciclo}: {resultado['total']}/2 capturas bem-sucedidas")
            print(f"    - Direita: {'Sucesso' if resultado['direita'] else 'Falha'}")
            print(f"    - Esquerda: {'Sucesso' if resultado['esquerda'] else 'Falha'}")
        
        pasta = os.path.abspath("frames_capturados")
        print(f"\nFrames salvos em: {pasta}")
        
        # Perguntar se centraliza
        if input("\nCentralizar câmera? (s/n): ").lower() == 's':
            print("Centralizando câmera...")
            centralizar_camera(ptz, profile_token)
        
        # Restaurar stream se foi parado e estava ativo anteriormente
        stream_estava_ativo = 'usar_stream_existente' in locals() and not usar_stream_existente and stream_ativo
        if stream_estava_ativo:
            print("Reiniciando o stream de vídeo...")
            iniciar_stream_video(rtsp_url)
        
        return True
            
    except Exception as e:
        print(f"Erro durante teste: {str(e)}")
        import traceback
        print(f"Detalhes: {traceback.format_exc()}")
        return False

def main():
    print("\n=== TESTE INTERATIVO DE MOVIMENTOS DA CÂMERA ===")
    print("Este teste permite controlar a câmera PTZ e gerenciar posições salvas (presets)")
    
    try:
        # Conectar à câmera
        print(f"Conectando à câmera em {CAMERA_IP}:{ONVIF_PORT}...")
        cam = ONVIFCamera(CAMERA_IP, ONVIF_PORT, USERNAME, PASSWORD)
        
        # Inicializar serviços
        media = cam.create_media_service()
        ptz = cam.create_ptz_service()
        
        # Obter perfis disponíveis
        profiles = media.GetProfiles()
        
        if not profiles:
            print("Nenhum perfil encontrado na câmera. Encerrando.")
            return
        
        # Usar o primeiro perfil
        profile = profiles[0]
        print(f"Usando perfil: {profile.Name} (Token: {profile.token})")
        
        # Parar qualquer movimento atual
        parar_camera(ptz, profile.token)
        
        # Perguntar ao usuário se deseja iniciar o stream de vídeo
        rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile0"
        iniciar_stream = input("\nDeseja iniciar o stream de vídeo? (s/n, padrão=s): ").lower() != 'n'
        
        if iniciar_stream:
            print("Iniciando stream de vídeo...")
            iniciar_stream_video(rtsp_url)
        else:
            print("Stream de vídeo não iniciado. Use a opção 11 no menu para iniciá-lo quando necessário.")
        
        # Loop principal interativo
        while True:
            # Obter e mostrar posição atual
            pan, tilt = obter_posicao_atual(ptz, profile.token)
            if pan is not None and tilt is not None:
                print(f"\n>>> POSIÇÃO ATUAL: Pan={pan:.4f}, Tilt={tilt:.4f} <<<")
            
            # Menu de opções
            print("\nEscolha uma opção:")
            print("1 - Parar movimento")
            print("2 - Centralizar câmera (mover para posição 0/0)")
            print("3 - Mover para posição absoluta de Pan e Tilt (definir valores manualmente)")
            print("4 - Mover para 90 graus à direita (Pan = 0.7)")
            print("5 - Mover para 90 graus à esquerda (Pan = -0.7)")
            print("6 - Criar preset (salvar posição atual)")
            print("7 - Listar presets disponíveis")
            print("8 - Ir para preset")
            print("9 - Remover preset")
            print("10 - Teste de velocidade (90° direita -> 90° esquerda)")
            print("11 - Iniciar/Reiniciar stream de vídeo")
            print("12 - Parar stream de vídeo")
            print("13 - Capturar frames nos extremos (90° direita e 90° esquerda)")
            print("0 - Sair")
            
            # Mostrar status do stream
            if stream_process is not None:
                print("Status: Stream de vídeo ATIVO")
            else:
                print("Status: Stream de vídeo INATIVO")
            
            opcao = input("Digite o número da opção desejada: ")
            
            if opcao == "1":
                parar_camera(ptz, profile.token)
            elif opcao == "2":
                centralizar_camera(ptz, profile.token)
            elif opcao == "3":
                mover_pan_absoluto(ptz, profile.token)
            elif opcao == "4":
                mover_pan_90_direita(ptz, profile.token)
            elif opcao == "5":
                mover_pan_90_esquerda(ptz, profile.token)
            elif opcao == "6":
                criar_preset(ptz, profile.token)
            elif opcao == "7":
                listar_presets(ptz, profile.token)
            elif opcao == "8":
                ir_para_preset(ptz, profile.token)
            elif opcao == "9":
                remover_preset(ptz, profile.token)
            elif opcao == "10":
                teste_velocidade_movimento(ptz, profile.token)
            elif opcao == "11":
                print("Iniciando/Reiniciando stream de vídeo...")
                iniciar_stream_video(rtsp_url)
            elif opcao == "12":
                print("Parando stream de vídeo...")
                parar_stream_video()
            elif opcao == "13":
                teste_captura_extremos(ptz, profile.token)
            elif opcao == "0":
                print("Encerrando teste...")
                parar_camera(ptz, profile.token)
                parar_stream_video()
                break
            else:
                print("Opção inválida. Tente novamente.")
        
        print("\n=== TESTE DE MOVIMENTOS CONCLUÍDO ===")
        
    except Exception as e:
        print(f"Erro durante o teste: {str(e)}")
        import traceback
        print(f"Detalhes do erro: {traceback.format_exc()}")
        
        # Tentar parar qualquer movimento em andamento
        try:
            ptz.Stop({'ProfileToken': profile.token})
            parar_stream_video()
        except:
            pass

# Garantir que os processos secundários sejam encerrados quando o programa principal terminar
def cleanup():
    parar_stream_video()

# Registrar a função de limpeza para ser chamada na saída do programa
import atexit
atexit.register(cleanup)

if __name__ == "__main__":
    main() 