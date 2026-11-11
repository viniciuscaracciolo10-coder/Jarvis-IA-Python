# -*- coding: utf-8 -*-
import math
import random
import sys
import threading
import time
from collections import deque
import os
import wave
import pyaudio
import pyttsx3
from groq import Groq
import asyncio
import edge_tts
import pygame
import tkinter as tk
import json
import pywhatkit
import subprocess
import winsound
import pyautogui
import requests
import urllib.parse
from Config import *
# ======================================================================
# 0. CONFIGURAÇÃO VISUAL E API
# ======================================================================
LARGURA, ALTURA = 1280, 720
FPS = 60
CX, CY = LARGURA // 2, 355          
COR_FUNDO = (5, 5, 12) 

XMIN, XMAX, YMIN, YMAX = 330, 950, 100, 610

historico = []
if os.path.exists("memoria.json"):
    with open("memoria.json", "r", encoding="utf-8") as f:
        historico = json.load(f)

CORES_ESTADO = {
    "AGUARDANDO":  (0, 150, 255),    
    "OUVINDO":     (130, 0, 255),    
    "PROCESSANDO": (200, 0, 255),    
    "FALANDO":     (0, 255, 200),    
}
VEL_ANEIS   = {"AGUARDANDO": 1.0, "OUVINDO": 2.8, "PROCESSANDO": 3.6, "FALANDO": 1.6}
FREQ_PULSO  = {"AGUARDANDO": 0.35, "OUVINDO": 1.3, "PROCESSANDO": 2.2, "FALANDO": 1.0}
INTENSIDADE = {"AGUARDANDO": 0.30, "OUVINDO": 0.85, "PROCESSANDO": 0.65, "FALANDO": 0.90}

CHAVE_POLLINATIONS = chavepoli
CHAVE_API = chavegroq
client = Groq(api_key=CHAVE_API)

programas = {
    "roblox": "roblox://",
    "whatsapp": "whatsapp://",
    "brave": "brave", 
    "vs code": "code",
    "calculadora": "calc",
    "bloco de notas": "notepad"
}

# ======================================================================
# VARIÁVEIS GLOBAIS
# ======================================================================
ESTADO_ATUAL = "AGUARDANDO"   
TEXTO_USUARIO = ""
TEXTO_JARVIS = ""
RODANDO = True
MODO_MAO_ATIVO = False
NIVEL_AUDIO = 0.0             
FORCAR_ESTADO = None          

MODO_ENTRADA = "NENHUM" 
TEXTO_DIGITADO = ""
PROCESSANDO_REQ = False

# ======================================================================
# 1. FUNÇÕES DE APOIO E JANELAS
# ======================================================================
def abrir_janela_copia(texto):
    if not texto: return
    def _criar_janela():
        janela = tk.Tk()
        janela.title("Copiar Resposta do Jarvis")
        janela.geometry("600x400")
        janela.configure(bg="#0F0C15")
        
        caixa_texto = tk.Text(janela, wrap="word", bg="#1A1A1A", fg="#00FFCC", font=("Consolas", 12))
        caixa_texto.pack(expand=True, fill="both", padx=10, pady=10)
        caixa_texto.insert("1.0", texto)
        caixa_texto.focus_set()
        janela.mainloop()

    threading.Thread(target=_criar_janela, daemon=True).start()

# ======================================================================
# 2. BACKEND (AUDIO, IA E TTS)
# ======================================================================
def gravar_audio():
    global NIVEL_AUDIO
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1 
    RATE = 48000
    RECORD_SECONDS = 4
    WAVE_OUTPUT_FILENAME = "input.wav"

    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, input_device_index=1, frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Erro no microfone: {e}")
        return

    frames = []
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    NIVEL_AUDIO = 0.0

def transcrever_com_groq():
    try:
        with open("input.wav", "rb") as file:
            transcricao = client.audio.transcriptions.create(
                file=(os.path.basename("input.wav"), file.read()),
                model="whisper-large-v3",
                language="pt",
                prompt="Conversa em português do Brasil. Gírias como 'aoba', 'mano', 'meu povo'."
            )
        return transcricao.text
    except Exception as e:
        return f"Erro na transcrição: {e}"

def perguntar_ia(mensagem):
    global historico
    try:    
        historico.append({"role": "user", "content": mensagem})
        historico_recente = historico[-50:]
        mensagens_para_api = [
            {
                "role": "system", 
                "content": "Você é o Jarvis, um assistente inteligente e direto. O usuário se chama Vinicius (trate-o como Mestre). Responda de forma curta, direta e em português. REGRA: Sem markdown, sem asteriscos, apenas texto puro."
            }
        ] + historico_recente
        chat_completion = client.chat.completions.create(
            messages=mensagens_para_api,
            model="openai/gpt-oss-120b",
        )
        resposta = chat_completion.choices[0].message.content
        historico.append({"role": "assistant", "content": resposta})
        return resposta
    except Exception as e:
        return f"Erro na IA: {e}"

def salvar_memoria():
    with open("memoria.json", "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=4)

def falar(texto):
    try:
        print(f"\n[JARVIS FALANDO]: {texto}")
        arquivo_temp = f"temp_jarvis_voice_{int(time.time()*1000)}.mp3" 
        
        from gtts import gTTS
        tts = gTTS(text=texto, lang='pt', tld='com.br', slow=False)
        tts.save(arquivo_temp)
        
        som = pygame.mixer.Sound(arquivo_temp)
        duracao = som.get_length() 
        canal = som.play()
        
        if canal:
            inicio_play = time.time()
            while canal.get_busy():
                pygame.time.Clock().tick(10)
                if time.time() - inicio_play > duracao + 2.0:
                    canal.stop()
                    break
            
        if os.path.exists(arquivo_temp):
            os.remove(arquivo_temp)
            
    except Exception as e:
        print(f"❌ Erro no TTS: {e}")

# ======================================================================
# 3. COMANDOS DO JARVIS (FUNÇÕES ESPECÍFICAS)
# ======================================================================
def pegar_clima_real(cidade):
    try:
        url = f"https://wttr.in/{cidade}?format=j1"
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            dados = resposta.json()
            agora = dados["current_condition"][0]
            temp = agora["temp_C"]
            sensacao = agora["FeelsLikeC"]
            umidade = agora["humidity"]
            vento = agora["windspeedKmph"]
            descricao = agora["lang_pt"][0]["value"] if "lang_pt" in agora else agora["weatherDesc"][0]["value"]
            return f"Mestre, agora em {cidade.title()} está {temp} graus, com sensação de {sensacao}. O tempo está {descricao.lower()}, com umidade de {umidade} por cento e ventos de {vento} quilômetros por hora."
        else:
            return "Não consegui pegar os dados do satélite, Mestre."
    except Exception as e:
        return "Erro de conexão com o serviço de meteorologia."

def tocar_musica(nome_musica):
    try:
        pywhatkit.playonyt(nome_musica)
        return f"Tocando {nome_musica} no YouTube, Mestre."
    except Exception as e:
        return f"Não consegui tocar a música. Erro: {e}"

def baixar_video(url_ou_nome):
    try:
        if not os.path.exists("Downloads_Jarvis"):
            os.makedirs("Downloads_Jarvis")
        termo = f"ytsearch1:{url_ou_nome}" if not url_ou_nome.startswith("http") else url_ou_nome
        comando = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]", "--merge-output-format", "mp4", "-o", "Downloads_Jarvis/%(title)s.%(ext)s", termo]
        subprocess.run(comando, check=True)
        return f"Download de '{url_ou_nome}' concluído na pasta Downloads_Jarvis, Mestre."
    except Exception as e:
        return f"Erro no download: {e}"

def abrir_programa(nome_programa):
    if nome_programa in programas:
        comando = programas[nome_programa]
        os.system(f'start "" {comando}') 
        return f"Abrindo {nome_programa}, Mestre."
    else:
        return "Não sei como abrir esse programa."

def enviar_whatsapp(numero, mensagem):
    try:
        if not numero.startswith("+"):
            numero = "+55" + numero
        pywhatkit.sendwhatmsg_instantly(phone_no=numero, message=mensagem, wait_time=15, tab_close=True, close_time=3)
        return "Mensagem enviada com sucesso, Mestre!"
    except Exception as e:
        return f"Erro ao enviar mensagem: {e}"

def gerar_imagem_pollinations(prompt):
    try:
        if not os.path.exists("Imagens_Jarvis"):
            os.makedirs("Imagens_Jarvis")
        nome_arquivo = f"Imagens_Jarvis/img_{int(time.time())}.png"
        prompt_encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&nologo=true&key={CHAVE_POLLINATIONS}"
        resposta = requests.get(url, timeout=60) 
        if resposta.status_code == 200:
            with open(nome_arquivo, "wb") as f:
                f.write(resposta.content)
            return f"Imagem gerada com sucesso e salva na pasta Imagens_Jarvis, Mestre."
        else:
            return f"Erro na API do Pollinations. Status: {resposta.status_code}"
    except Exception as e:
        return f"Erro ao gerar imagem: {e}"

# --- NOVA FUNÇÃO: Gerar Modelo 3D ---
def gerar_modelo_3d(prompt: str, pasta_destino: str = "Modelos_3D"):
    url = "https://three.ws/api/3d/generate"
    payload = {"prompt": prompt, "format": "glb"}
    
    print(f"🎨 Gerando modelo 3D para: '{prompt}'...")
    print("   (Isso pode levar alguns segundos...)")

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "done":
            glb_url = data.get("glbUrl")
        elif data.get("status") == "pending":
            job_id = data.get("job")
            retry_after = data.get("retryAfter", 5) 
            while True:
                time.sleep(retry_after)
                job_url = f"https://three.ws/api/3d/generate?job={job_id}"
                job_response = requests.get(job_url, timeout=30)
                job_response.raise_for_status()
                job_data = job_response.json()

                if job_data.get("status") == "done":
                    glb_url = job_data.get("glbUrl")
                    break
                elif job_data.get("status") == "pending":
                    retry_after = job_data.get("retryAfter", retry_after)
                    print(f"   ...ainda processando. Próxima checagem em {retry_after}s.")
                else:
                    return None
        else:
            return None

        if not glb_url:
            return None

        os.makedirs(pasta_destino, exist_ok=True)
        nome_arquivo = prompt.lower().replace(" ", "_")[:50] + ".glb"
        caminho_final = os.path.join(pasta_destino, nome_arquivo)

        with requests.get(glb_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(caminho_final, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        return caminho_final
    except Exception as e:
        print(f"   ❌ Erro inesperado (3D): {e}")
        return None

# ======================================================================
# 4. MODO DE CONTROLE POR MÃOS (MEDIAPIPE)
# ======================================================================
def loop_modo_mao():
    global MODO_MAO_ATIVO
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1, min_hand_detection_confidence=0.7)
    detector = vision.HandLandmarker.create_from_options(options)
    cap = cv2.VideoCapture(0)
    
    y_anterior = 0.5
    x_anterior = 0.5
    ultimo_comando = 0
    COOLDOWN = 1.5
    
    distancia_media = 0.1
    ultimo_vol_tempo = 0
    COOLDOWN_VOL = 0.3 
    
    punho_fechado_anterior = False
    mao_aberta_anterior = False
    ultimo_media = 0 
    
    while RODANDO:
        if not MODO_MAO_ATIVO:
            time.sleep(0.5)
            continue
            
        sucesso, frame = cap.read()
        if not sucesso: continue
        
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        resultado = detector.detect(mp_image)
        
        if resultado.hand_landmarks:
            mao = resultado.hand_landmarks[0]
            dedo_y = mao[8].y 
            dedo_x = mao[8].x
            
            delta_y = dedo_y - y_anterior
            delta_x = dedo_x - x_anterior
            tempo_atual = time.time()
            
            # Volume
            polegar = mao[4]
            indicador = mao[8]
            distancia_bruta = math.sqrt((polegar.x - indicador.x)**2 + (polegar.y - indicador.y)**2)
            distancia_media = (distancia_bruta * 0.2) + (distancia_media * 0.8)
            
            if tempo_atual - ultimo_vol_tempo > COOLDOWN_VOL:
                if distancia_media > 0.18:
                    pyautogui.press('volumeup')
                    ultimo_vol_tempo = tempo_atual
                    distancia_media = 0.1
                elif distancia_media < 0.05:
                    pyautogui.press('volumedown')
                    ultimo_vol_tempo = tempo_atual
                    distancia_media = 0.1
                    
            # Play / Pause
            indicador_cima = mao[8].y < mao[6].y
            medio_cima = mao[12].y < mao[10].y
            anelar_cima = mao[16].y < mao[14].y
            mindinho_cima = mao[20].y < mao[18].y
            mao_aberta = indicador_cima and medio_cima and anelar_cima and mindinho_cima
            punho_fechado = not indicador_cima and not medio_cima and not anelar_cima and not mindinho_cima
            
            if tempo_atual - ultimo_media > 2.0:
                if punho_fechado and not punho_fechado_anterior:
                    pyautogui.press('playpause')
                    ultimo_media = tempo_atual
                elif mao_aberta and not mao_aberta_anterior:
                    pyautogui.press('playpause')
                    ultimo_media = tempo_atual
            
            punho_fechado_anterior = punho_fechado
            mao_aberta_anterior = mao_aberta

            # Swipes
            if not punho_fechado and not mao_aberta and (tempo_atual - ultimo_comando > COOLDOWN):
                if delta_y < -0.1: 
                    pyautogui.hotkey('win', 'd')
                    ultimo_comando = tempo_atual
                elif delta_y > 0.1: 
                    pyautogui.hotkey('win', 'd')
                    ultimo_comando = tempo_atual
                elif delta_x > 0.12: 
                    pyautogui.hotkey('alt', 'tab')
                    ultimo_comando = tempo_atual
                elif delta_x < -0.12:
                    pyautogui.hotkey('alt', 'shift', 'tab')
                    ultimo_comando = tempo_atual
                    
            y_anterior = dedo_y
            x_anterior = dedo_x 
            
        else:
            y_anterior = 0.5 
            x_anterior = 0.5
            distancia_media = 0.1 
            punho_fechado_anterior = False
            mao_aberta_anterior = False
            
    cap.release()

# ======================================================================
# 5. LEMBRETES E JANELA
# ======================================================================
def abrir_janela_lembrete(mensagem):
    def _criar():
        janela = tk.Tk()
        janela.title("Alerta do Jarvis")
        largura, altura = 400, 200
        x = (janela.winfo_screenwidth() // 2) - (largura // 2)
        y = (janela.winfo_screenheight() // 2) - (altura // 2)
        janela.geometry(f"{largura}x{altura}+{x}+{y}")
        janela.configure(bg="#0F0C15")
        tk.Label(janela, text="⏰ LEMBRETE", font=("Consolas", 20, "bold"), bg="#0F0C15", fg="#00FFCC").pack(pady=(20, 10))
        tk.Label(janela, text=mensagem, font=("Segoe UI", 14), bg="#0F0C15", fg="#FFFFFF", wraplength=350).pack(pady=10)
        tk.Button(janela, text="OK, Mestre", font=("Segoe UI", 12), bg="#00FFCC", fg="#000000", command=janela.destroy).pack(pady=15)
        janela.mainloop()
    threading.Thread(target=_criar, daemon=True).start()

def tocar_alarme_por_4s():
    inicio = time.time()
    while time.time() - inicio < 4:
        winsound.Beep(1000, 300)
        time.sleep(0.1)
        winsound.Beep(1500, 300)
        time.sleep(0.1)

def criar_lembrete(tempo_segundos, mensagem):
    def acao_do_lembrete():
        time.sleep(tempo_segundos)
        threading.Thread(target=tocar_alarme_por_4s, daemon=True).start()
        abrir_janela_lembrete(mensagem)
        falar(f"Mestre, lembrete: {mensagem}")
    threading.Thread(target=acao_do_lembrete, daemon=True).start()
    return f"Entendido, Mestre. Vou te avisar em {tempo_segundos} segundos."

# ======================================================================
# 6. PROCESSAMENTO DE REQUISIÇÕES (ROTEADOR)
# ======================================================================
def processar_requisicao(modo_entrada, texto_digitado=""):
    global ESTADO_ATUAL, TEXTO_USUARIO, TEXTO_JARVIS, PROCESSANDO_REQ

    PROCESSANDO_REQ = True
    try:
        if modo_entrada == "VOZ":
            ESTADO_ATUAL = "OUVINDO"
            gravar_audio()
            ESTADO_ATUAL = "PROCESSANDO"
            TEXTO_USUARIO = transcrever_com_groq()
        elif modo_entrada == "TEXTO":
            ESTADO_ATUAL = "PROCESSANDO"
            TEXTO_USUARIO = texto_digitado
            time.sleep(0.5)

        if not TEXTO_USUARIO or not TEXTO_USUARIO.strip():
            ESTADO_ATUAL = "AGUARDANDO"
            PROCESSANDO_REQ = False
            return

        comando = TEXTO_USUARIO.lower().strip()

        if "sair" in comando or "desligar" in comando:
            salvar_memoria()
            TEXTO_JARVIS = "Até logo, Mestre."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            global RODANDO
            RODANDO = False
            return
            
        elif "ligar modo" in comando and ("mao" in comando or "mão" in comando):
            global MODO_MAO_ATIVO
            MODO_MAO_ATIVO = True
            TEXTO_JARVIS = "Modo de controle gestual ativado. Levante a mão para minimizar as janelas e abaixe para restaurar."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        elif "desligar modo" in comando and ("mao" in comando or "mão" in comando):
            MODO_MAO_ATIVO = False
            TEXTO_JARVIS = "Modo de controle gestual desativado."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return
            
        elif "whatsapp" in comando and ("mande" in comando or "envie" in comando):
            try:
                parte_numero = comando.split(" para ")[1]
                numero = parte_numero.split()[0]
                mensagem = comando.split(" dizendo ")[1].strip()
                
                TEXTO_JARVIS = f"Enviando mensagem para o número {numero}, Mestre. Por favor, aguarde, o WhatsApp Web está abrindo."
                ESTADO_ATUAL = "FALANDO"
                falar(TEXTO_JARVIS)
                resultado = enviar_whatsapp(numero, mensagem)
                TEXTO_JARVIS = resultado
            except IndexError:
                TEXTO_JARVIS = "Mestre, não entendi. Tente falar: 'Mande um whatsapp para 11999999999 dizendo que já estou indo'."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return
            
        elif "desenhe" in comando or "gere uma imagem" in comando:
            prompt = comando.replace("desenhe", "").replace("gere uma imagem", "").strip()
            TEXTO_JARVIS = f"Entendido, Mestre. Criando a imagem de {prompt}. Isso pode levar alguns segundos..."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            
            prompt_ia_msg = f"Crie um prompt detalhado em inglês para gerar a seguinte imagem: {prompt}. Retorne apenas o prompt, sem explicações."
            prompt_ingles = perguntar_ia(prompt_ia_msg)
            
            resultado = gerar_imagem_pollinations(prompt_ingles.strip())
            TEXTO_JARVIS = resultado
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        # --- NOVO COMANDO: GERAR MODELO 3D ---
        elif "modelo 3d" in comando:
            prompt = comando.replace("crie um modelo 3d", "").replace("gere um modelo 3d", "").replace("modelo 3d", "").replace("de", "").strip()
            if not prompt:
                prompt = "um objeto aleatório"
                
            TEXTO_JARVIS = f"Entendido, Mestre. Gerando o modelo 3D de {prompt}. Isso pode demorar um pouco, aguarde..."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            
            # Usa a IA para traduzir e melhorar o prompt para a API 3D
            prompt_ia_msg = f"Crie um prompt detalhado em inglês para gerar o seguinte modelo 3D: {prompt}. Retorne apenas o prompt, sem explicações."
            prompt_ingles = perguntar_ia(prompt_ia_msg)
            
            # Chama a função do three.ws
            resultado = gerar_modelo_3d(prompt_ingles.strip())
            
            if resultado:
                TEXTO_JARVIS = "Modelo 3D gerado com sucesso e salvo na pasta Modelos_3D, Mestre."
            else:
                TEXTO_JARVIS = "Desculpe Mestre, ocorreu um erro ao gerar o modelo 3D."
                
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        elif "clima" in comando or "tempo" in comando:
            cidade = "Suzano"
            if " em " in comando:
                cidade = comando.split(" em ")[-1].strip()
            TEXTO_JARVIS = pegar_clima_real(cidade)
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        elif "toque" in comando or "tocar" in comando:
            musica = comando.replace("toque", "").replace("tocar", "").replace("música", "").strip()
            TEXTO_JARVIS = tocar_musica(musica)
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        elif "avise" in comando or "lembre" in comando or "lembrete" in comando:
            try:
                partes = comando.split("segundos para ")
                tempo = int(partes[0].split()[-1])
                mensagem = partes[1].strip()
                TEXTO_JARVIS = criar_lembrete(tempo, mensagem)
            except:
                TEXTO_JARVIS = "Mestre, não entendi o tempo. Tente dizer: 'Me avise em 10 segundos para tomar água'."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        elif "baixe" in comando or "baixar" in comando:
            alvo = comando.replace("baixe", "").replace("baixar", "").replace("o vídeo", "").replace("video", "").strip()
            TEXTO_JARVIS = f"Iniciando o download de {alvo}, Mestre..."
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS) 
            resultado = baixar_video(alvo)
            TEXTO_JARVIS = resultado
            falar(TEXTO_JARVIS)
            return

        elif comando.startswith("abrir"):
            nome = comando.replace("abrir ", "").strip()
            TEXTO_JARVIS = abrir_programa(nome)
            ESTADO_ATUAL = "FALANDO"
            falar(TEXTO_JARVIS)
            return

        # Se não for nenhum comando específico, manda para a IA
        TEXTO_JARVIS = perguntar_ia(TEXTO_USUARIO)
        salvar_memoria()
        ESTADO_ATUAL = "FALANDO"
        falar(TEXTO_JARVIS)

    except Exception as erro: 
        TEXTO_JARVIS = f"Erro: {erro}"
        time.sleep(2.0)
    finally:
        ESTADO_ATUAL = "AGUARDANDO"
        PROCESSANDO_REQ = False

# ======================================================================
# 7. O HUD (PYGAME)
# ======================================================================
# ... [Mantidas todas as funções de desenho do HUD e a classe HUD] ...
def lerp(a, b, t): return a + (b - a) * t
def misturar(c1, c2, t):
    return (int(round(lerp(c1[0], c2[0], t))), int(round(lerp(c1[1], c2[1], t))), int(round(lerp(c1[2], c2[2], t))))
def esc(cor, k):
    k = max(0.0, min(1.0, k))
    return (int(cor[0] * k), int(cor[1] * k), int(cor[2] * k))
def polar(cx, cy, r, ang_graus):
    a = math.radians(ang_graus)
    return (cx + r * math.cos(a), cy + r * math.sin(a))

def arco(surf, cor, cx, cy, r, a0, a1, esp=1):
    ext = a1 - a0
    n = max(3, int(math.radians(abs(ext)) * r / 3.0))
    if esp <= 1:
        pts = [polar(cx, cy, r, a0 + ext * i / n) for i in range(n + 1)]
        pygame.draw.aalines(surf, cor, False, pts)
    else:
        re, ri = r + esp / 2.0, r - esp / 2.0
        fora = [polar(cx, cy, re, a0 + ext * i / n) for i in range(n + 1)]
        dentro = [polar(cx, cy, ri, a0 + ext * (n - i) / n) for i in range(n + 1)]
        pygame.draw.polygon(surf, cor, fora + dentro)

def dist_limite(ang_graus):
    a = math.radians(ang_graus)
    dx, dy = math.cos(a), math.sin(a)
    ts = []
    if dx > 1e-6: ts.append((XMAX - CX) / dx)
    elif dx < -1e-6: ts.append((XMIN - CX) / dx)
    if dy > 1e-6: ts.append((YMAX - CY) / dy)
    elif dy < -1e-6: ts.append((YMIN - CY) / dy)
    return min(ts)

def contorno(surf, cor, rect, c=10):
    x, y, w, h = rect
    pts = [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c),
           (x + w - c, y + h), (x + c, y + h), (x, y + h - c), (x, y + c)]
    pygame.draw.aalines(surf, cor, True, pts)

def escrever(surf, s, fonte, cor, pos, alinh="esq"):
    img = fonte.render(s, True, cor)
    x, y = pos
    if alinh == "centro": x -= img.get_width() // 2
    elif alinh == "dir": x -= img.get_width()
    surf.blit(img, (x, y))
    return img.get_width()

def quebrar_texto(txt, fonte, largura):
    linhas, atual = [], ""
    for palavra in txt.replace("\n", " ").split():
        teste = (atual + " " + palavra).strip()
        if fonte.size(teste)[0] <= largura:
            atual = teste
            continue
        if atual: linhas.append(atual)
        atual = palavra
    if atual: linhas.append(atual)
    return linhas or [""]

def criar_fonte(tamanho, negrito=False):
    return pygame.font.SysFont("consolas,couriernew,monospace", tamanho, bold=negrito)

class HUD:
    def __init__(self, tela):
        self.tela = tela
        self.luz = pygame.Surface((LARGURA, ALTURA), 0, 32).convert()
        self.camada_texto = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA).convert_alpha()
        self.glow_surf = None
        self.quadro = 0
        self.glow = True

        self.f_titulo = criar_fonte(50, True)
        self.f_status = criar_fonte(32, True)  
        self.f_texto = criar_fonte(20, False)   
        self.f_peq = criar_fonte(16, True)           

        self.t = 0.0
        self.dt = 1 / 60
        self.fps = 60
        self.cor = CORES_ESTADO["AGUARDANDO"]
        self.mult_vel = 1.0
        self.intens = 0.3
        self.amp = 0.0
        self.carga_ia = 0.0
        self.fase_pulso = 0.0
        self.fase_varredura = 0.0
        self.fase_dots = 0.0
        self.ang_ticks = 0.0
        self.ang_radial = 0.0
        self.ang_hex = 0.0

        self.scroll_jarvis = 0
        self.scroll_usuario = 0

        self.aneis = [
            dict(r=74,  esp=3, v=75,  seg=[(0, 80), (120, 80), (240, 80)], k=1.00, ang=0.0),
            dict(r=104, esp=1, v=-48, seg=[(i * 15, 8) for i in range(24)], k=0.75, ang=0.0),
            dict(r=138, esp=4, v=-32, seg=[(20, 110), (200, 110)], k=0.95, ang=40.0),
            dict(r=150, esp=1, v=12,  seg=[(0, 360)], k=0.30, ang=0.0),
            dict(r=176, esp=2, v=24,  seg=[(0, 200), (230, 60), (310, 30)], k=0.85, ang=0.0),
            dict(r=214, esp=1, v=-14, seg=[(0, 90), (120, 90), (240, 90)], k=0.85, ang=0.0),
        ]

        rnd = random.Random(7)
        self.blips = [(rnd.uniform(0, 360), rnd.uniform(70, 200)) for _ in range(9)]

        self.ondas = []          
        self.ult_onda = 0.0
        self.hex_addr = 0x3F00
        self.hex_linhas = deque(maxlen=7)
        for _ in range(7): self.hex_linhas.append(self._linha_hex())
        self.hex_timer = 0.0
        self.trafego = deque([0.3] * 70, maxlen=70)
        self.traf_timer = 0.0
        self.picos = [0.0] * 28

        self.fundo = pygame.Surface((LARGURA, ALTURA)).convert()
        self.fundo.fill(COR_FUNDO)
        for x in range(20, LARGURA, 40):
            for y in range(20, ALTURA, 40):
                pygame.draw.line(self.fundo, (20, 10, 40), (x - 2, y), (x + 2, y))
                pygame.draw.line(self.fundo, (20, 10, 40), (x, y - 2), (x, y + 2))

    def _linha_hex(self):
        return "%04X  %s" % (self.hex_addr & 0xFFFF, " ".join("%04X" % random.randrange(65536) for _ in range(4)))

    def atualizar(self, dt, estado):
        self.dt = dt
        self.t += dt
        t = self.t

        self.cor = misturar(self.cor, CORES_ESTADO[estado], 1 - math.exp(-dt * 7))
        self.mult_vel = lerp(self.mult_vel, VEL_ANEIS[estado], 1 - math.exp(-dt * 3))
        self.intens = lerp(self.intens, INTENSIDADE[estado], 1 - math.exp(-dt * 3))
        self.carga_ia = lerp(self.carga_ia, 1.0 if estado == "PROCESSANDO" else 0.0, 1 - math.exp(-dt * 2))

        if estado == "OUVINDO": alvo = 0.2 + 0.5 * abs(math.sin(t * 6.3))
        elif estado == "FALANDO": alvo = 0.15 + 0.65 * abs(math.sin(t * 8.7))
        elif estado == "PROCESSANDO": alvo = 0.15
        else: alvo = 0.04
        self.amp = lerp(self.amp, alvo, 1 - math.exp(-dt * 14))

        self.fase_pulso += 2 * math.pi * FREQ_PULSO[estado] * dt
        self.fase_varredura = (self.fase_varredura + 110 * self.mult_vel * dt) % 360
        self.fase_dots += dt * 0.12 * self.mult_vel
        self.ang_ticks = (self.ang_ticks + 8 * self.mult_vel * dt) % 360
        self.ang_radial = (self.ang_radial + 1.5 * self.mult_vel * dt) % 360
        self.ang_hex = (self.ang_hex + 30 * self.mult_vel * dt) % 360
        for a in self.aneis:
            a["ang"] = (a["ang"] + a["v"] * self.mult_vel * dt) % 360

        if estado == "FALANDO" and t - self.ult_onda > 0.42:
            self.ondas.append((t, 1))
            self.ult_onda = t
        elif estado == "OUVINDO" and t - self.ult_onda > 0.70:
            self.ondas.append((t, -1))
            self.ult_onda = t
        self.ondas = [o for o in self.ondas if t - o[0] < 1.4]

        self.hex_timer += dt
        passo = 0.07 if estado == "PROCESSANDO" else 0.18
        while self.hex_timer >= passo:
            self.hex_timer -= passo
            self.hex_addr += 16
            self.hex_linhas.append(self._linha_hex())

        self.traf_timer += dt
        while self.traf_timer >= 0.08:
            self.traf_timer -= 0.08
            v = (0.35 + 0.22 * math.sin(t * 1.3) + 0.12 * math.sin(t * 4.1) + 0.30 * self.intens * random.random())
            self.trafego.append(max(0.02, min(1.0, v)))

    def painel(self, s, rect, titulo):
        x, y, w, h = rect
        cor = self.cor
        contorno(s, esc(cor, 0.5), rect, 10)
        forte = esc(cor, 1.0)
        pygame.draw.line(s, forte, (x + 10, y), (x + 40, y), 2)
        pygame.draw.line(s, forte, (x, y + 10), (x, y + 40), 2)
        pygame.draw.line(s, forte, (x + w - 10, y + h), (x + w - 40, y + h), 2)
        pygame.draw.line(s, forte, (x + w, y + h - 10), (x + w, y + h - 40), 2)
        pygame.draw.line(s, esc(cor, 0.25), (x + 10, y + 24), (x + w - 10, y + 24))
        pygame.draw.rect(s, esc(cor, 0.9), (x + w - 22, y + 9, 6, 6))
        escrever(self.camada_texto, titulo, self.f_peq, esc(cor, 0.95), (x + 14, y + 4))
        return pygame.Rect(x + 10, y + 30, w - 20, h - 38)

    def molduras(self, s):
        cor = esc(self.cor, 0.45)
        L = 34
        for (x, y, dx, dy) in ((XMIN, YMIN, 1, 1), (XMAX, YMIN, -1, 1), (XMIN, YMAX, 1, -1), (XMAX, YMAX, -1, -1)):
            pygame.draw.line(s, cor, (x, y), (x + dx * L, y), 2)
            pygame.draw.line(s, cor, (x, y), (x, y + dy * L), 2)
        
        c2 = esc(self.cor, 0.35)
        m, L2 = 8, 36
        for (x, y, dx, dy) in ((m, m, 1, 1), (LARGURA - m, m, -1, 1), (m, ALTURA - m, 1, -1), (LARGURA - m, ALTURA - m, -1, -1)):
            pygame.draw.line(s, c2, (x, y), (x + dx * L2, y), 1)
            pygame.draw.line(s, c2, (x, y), (x, y + dy * L2), 1)

    def radar(self, s):
        cor = self.cor
        n = 16
        for i in range(n):
            ang = i * 360.0 / n + self.ang_radial
            fim = dist_limite(ang)
            p0 = polar(CX, CY, 46, ang)
            p1 = polar(CX, CY, fim, ang)
            pygame.draw.aaline(s, esc(cor, 0.16), p0, p1)
            pygame.draw.circle(s, esc(cor, 0.55), (int(p1[0]), int(p1[1])), 2)
            for j in range(2):
                fase = (self.fase_dots + i * 0.173 + j * 0.5) % 1.0
                r = 46 + fase * (fim - 46)
                brilho = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self.t * 9 + i * 1.7 + j * 3.0))
                p = polar(CX, CY, r, ang)
                pygame.draw.circle(s, esc(cor, brilho), (int(p[0]), int(p[1])), 2)

    def varredura(self, s):
        cor = self.cor
        ang = self.fase_varredura
        R, n, passo = 205, 28, 2.2
        for i in range(n):
            a0 = ang - i * passo
            a1 = a0 - passo
            k = 0.30 * (1 - i / n) ** 1.6
            pygame.draw.polygon(s, esc(cor, k), [(CX, CY), polar(CX, CY, R, a0), polar(CX, CY, R, a1)])
        pygame.draw.aaline(s, esc(cor, 0.9), (CX, CY), polar(CX, CY, R, ang))
        for ang_b, r_b in self.blips:
            diff = (ang - ang_b) % 360
            k = 1 - diff / 140.0
            if k > 0:
                p = polar(CX, CY, r_b, ang_b)
                pygame.draw.circle(s, esc(cor, k), (int(p[0]), int(p[1])), int(2 + 2 * k))
                arco(s, esc(cor, k * 0.6), p[0], p[1], 7 + 4 * (1 - k), 0, 360)

    def aneis_giratorios(self, s):
        cor = self.cor
        for a in self.aneis:
            brilho = a["k"] * (0.75 + 0.25 * self.intens)
            c = esc(cor, brilho)
            for (ini, tam) in a["seg"]:
                a0 = a["ang"] + ini
                arco(s, c, CX, CY, a["r"], a0, a0 + tam, a["esp"])
                if a["esp"] >= 2:
                    p = polar(CX, CY, a["r"], a0)
                    pygame.draw.circle(s, esc(cor, 1.0), (int(p[0]), int(p[1])), 3)
        arco(s, esc(cor, 0.20), CX, CY, 250, 0, 360)
        arco(s, esc(cor, 0.12), CX, CY, 124, 0, 360)
        for i in range(120):
            ang = self.ang_ticks + i * 3
            if i % 10 == 0: tam, k = 13, 0.95
            elif i % 5 == 0: tam, k = 8, 0.6
            else: tam, k = 4, 0.35
            p_ext = polar(CX, CY, 246, ang)
            p_int = polar(CX, CY, 246 - tam, ang)
            pygame.draw.aaline(s, esc(cor, k), p_int, p_ext)

    def ondas_sonoras(self, s):
        cor = self.cor
        for nasc, sentido in self.ondas:
            idade = self.t - nasc
            r = 34 + idade * 205 if sentido > 0 else 285 - idade * 190
            k = 1 - idade / 1.4
            if r > 20 and k > 0:
                arco(s, esc(cor, 0.85 * k), CX, CY, r, 0, 360)
                arco(s, esc(cor, 0.35 * k), CX, CY, r - 6, 0, 360)

    def nucleo(self, s):
        cor = self.cor
        resp = 0.5 + 0.5 * math.sin(self.fase_pulso)          
        r = 22 + 9 * resp + 20 * self.amp
        for dr, k in ((14, 0.55), (24, 0.30), (36, 0.15)):
            arco(s, esc(cor, k), CX, CY, r + dr, 0, 360)
        pygame.draw.circle(s, esc(cor, 0.85), (CX, CY), int(r))
        pygame.draw.circle(s, misturar(cor, (255, 255, 255), 0.55), (CX, CY), max(2, int(r * 0.55)))
        hexa = [polar(CX, CY, 54, self.ang_hex + i * 60) for i in range(6)]
        pygame.draw.aalines(s, esc(cor, 0.8), True, hexa)
        tri = [polar(CX, CY, 46, -self.ang_hex * 1.6 + i * 120) for i in range(3)]
        pygame.draw.aalines(s, esc(cor, 0.5), True, tri)

    def titulo(self, s):
        cor = self.cor
        escrever(self.camada_texto, "V U N I X", self.f_titulo, cor, (CX, 14), "centro")
        escrever(self.camada_texto, "NEURAL INTERFACE  //  JARVIS CORE", self.f_peq, esc(cor, 0.8), (CX, 72), "centro")
        escrever(self.camada_texto, "VUNIX // CORE ONLINE", self.f_peq, esc(cor, 0.7), (30, 5))
        escrever(self.camada_texto, "FPS %02d   %s" % (self.fps, time.strftime("%H:%M:%S")), self.f_peq, esc(cor, 0.7), (LARGURA - 30, 5), "dir")
        
        for (x0, x1) in ((XMIN, 505), (775, XMAX)):
            pygame.draw.line(s, esc(cor, 0.4), (x0, 40), (x1, 40))
            pygame.draw.line(s, esc(cor, 0.8), (x0, 40), (x0 + 22, 40), 2)
            pygame.draw.line(s, esc(cor, 0.8), (x1 - 22, 40), (x1, 40), 2)

    def status(self, s, estado):
        cor = self.cor
        if estado == "PROCESSANDO":
            escrever(self.camada_texto, "PROCESSANDO", self.f_status, cor, (CX, 610), "centro")
            ativo = int(self.t * 12) % 12
            for i in range(12):
                d = (ativo - i) % 12
                k = max(0.12, 1 - d * 0.18) if d < 5 else 0.12
                pygame.draw.rect(s, esc(cor, k), (CX - 96 + i * 16, 650, 10, 10))
        else:
            escrever(self.camada_texto, ">> %s <<" % estado, self.f_status, cor, (CX, 610), "centro")
            ligados = int(max(0.0, min(1.0, self.amp * 1.4)) * 24)
            for i in range(24):
                x = CX - 132 + i * 11
                if i < ligados:
                    pygame.draw.rect(s, esc(cor, 0.5 + 0.5 * i / 24), (x, 650, 8, 10))
                else:
                    pygame.draw.rect(s, esc(cor, 0.15), (x, 650, 8, 10), 1)

    def painel_camera(self, s, x, y, w, h):
        cor = self.cor
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "CAM-01 // PERIMETRO")
        area = pygame.Rect(ax, ay, aw, ah)
        pygame.draw.rect(s, esc(cor, 0.05), area)
        s.set_clip(area)
        for gx in range(ax, ax + aw, 20): pygame.draw.line(s, esc(cor, 0.10), (gx, ay), (gx, ay + ah))
        for gy in range(ay, ay + ah, 20): pygame.draw.line(s, esc(cor, 0.10), (ax, gy), (ax + aw, gy))

        mx, my = ax + aw / 2, ay + ah / 2
        for escala, vel, k in ((30, 1.0, 0.9), (14, -1.7, 0.5)):
            yaw, pitch = self.t * 0.9 * vel, self.t * 0.6 * vel
            pts = []
            for i in range(8):
                vx, vy, vz = (1 if i & 4 else -1), (1 if i & 2 else -1), (1 if i & 1 else -1)
                x1 = vx * math.cos(yaw) + vz * math.sin(yaw)
                z1 = -vx * math.sin(yaw) + vz * math.cos(yaw)
                y2 = vy * math.cos(pitch) - z1 * math.sin(pitch)
                z2 = vy * math.sin(pitch) + z1 * math.cos(pitch)
                f = 4.0 / (4.0 + z2)
                pts.append((mx + x1 * f * escala, my + y2 * f * escala))
            for i in range(8):
                for j in range(i + 1, 8):
                    if bin(i ^ j).count("1") == 1:
                        pygame.draw.aaline(s, esc(cor, k), pts[i], pts[j])

        by = ay + int((self.t * 40) % ah)
        pygame.draw.line(s, esc(cor, 0.35), (ax, by), (ax + aw, by), 2)
        s.set_clip(None)
        pygame.draw.line(s, esc(cor, 0.6), (mx - 10, my), (mx + 10, my))
        pygame.draw.line(s, esc(cor, 0.6), (mx, my - 10), (mx, my + 10))
        
        pygame.draw.circle(s, esc((255, 60, 60), 1.0), (ax + 10, ay + 10), 4)
        
        escrever(self.camada_texto, "REC", self.f_peq, esc(cor, 0.9), (ax + 18, ay + 3))
        escrever(self.camada_texto, time.strftime("%H:%M:%S"), self.f_peq, esc(cor, 0.7), (ax + aw - 4, ay + ah - 16), "dir")

    def painel_ondas(self, s, x, y, w, h):
        cor = self.cor
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "ATIVIDADE NEURAL")
        meio = ay + ah / 2.0
        amp_base = (ah / 2.0 - 4) * (0.25 + 0.75 * self.intens)
        pygame.draw.line(s, esc(cor, 0.15), (ax, meio), (ax + aw, meio))
        ondas = ((0.045, 3.0, 0.0, 1.0), (0.070, -2.2, 1.3, 0.6), (0.110, 4.1, 2.6, 0.35))
        for idx, (freq, vel, fase, k) in enumerate(ondas):
            pts = []
            for px in range(0, aw + 1, 3):
                env = math.sin(px / aw * math.pi) ** 0.6
                v = math.sin(px * freq + self.t * vel + fase)
                v *= 0.6 + 0.4 * math.sin(px * 0.031 + self.t * 1.3 + idx)
                v += 0.35 * math.sin(px * freq * 2.7 - self.t * vel * 1.4)
                pts.append((ax + px, meio + v * amp_base * 0.72 * env))
            pygame.draw.aalines(s, esc(cor, k), False, pts)

    def painel_sistema(self, s, x, y, w, h, estado):
        cor, t = self.cor, self.t
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "STATUS DO SISTEMA")
        itens = [
            ("CPU", 0.45 + 0.20 * math.sin(t * 0.9) + 0.10 * math.sin(t * 3.1) + 0.20 * self.carga_ia),
            ("MEM", 0.60 + 0.08 * math.sin(t * 0.5 + 1.1)),
            ("REDE", 0.35 + 0.25 * math.sin(t * 1.4 + 2.0) * math.sin(t * 0.37)),
            ("AUDIO", 0.08 + 0.92 * self.amp),
            ("IA", 0.10 + 0.85 * self.carga_ia),
        ]
        linha = ah / len(itens)
        x0, larg = ax + 48, aw - 48 - 40
        segs = 16
        sw = larg / segs
        for i, (nome, v) in enumerate(itens):
            v = max(0.0, min(1.0, v))
            ry = ay + i * linha
            escrever(self.camada_texto, nome, self.f_peq, esc(cor, 0.9), (ax, ry + 3))
            acesos = int(v * segs)
            for k in range(segs):
                r = pygame.Rect(int(x0 + k * sw), int(ry + 4), max(2, int(sw) - 2), 9)
                if k < acesos: pygame.draw.rect(s, esc(cor, 0.55 + 0.45 * k / segs), r)
                else: pygame.draw.rect(s, esc(cor, 0.15), r, 1)
            escrever(self.camada_texto, "%3d%%" % int(v * 100), self.f_peq, esc(cor, 0.8), (ax + aw, ry + 3), "dir")

    def painel_medidores(self, s, x, y, w, h):
        cor, t = self.cor, self.t
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "NUCLEO")
        itens = (("TEMP", 0.42 + 0.06 * math.sin(t * 0.7)), ("ENERGIA", 0.88 - 0.04 * math.sin(t * 0.5)), ("SINC", 0.55 + 0.35 * self.intens))
        for i, (nome, v) in enumerate(itens):
            gx, gy = ax + aw * (i + 0.5) / 3, ay + 19
            arco(s, esc(cor, 0.22), gx, gy, 17, 135, 405, 3)
            arco(s, esc(cor, 1.0), gx, gy, 17, 135, 135 + 270 * v, 3)
            escrever(self.camada_texto, "%d" % int(v * 100), self.f_peq, esc(cor, 0.95), (gx, gy - 7), "centro")
            escrever(self.camada_texto, nome, self.f_peq, esc(cor, 0.6), (gx, gy + 20), "centro")

    def painel_hex(self, s, x, y, w, h):
        cor = self.cor
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "FLUXO DE DADOS")
        n = len(self.hex_linhas)
        for i, linha in enumerate(self.hex_linhas):
            escrever(self.camada_texto, linha, self.f_peq, esc(cor, 0.25 + 0.65 * (i + 1) / n), (ax, ay + i * 16))

    def painel_espectro(self, s, x, y, w, h):
        cor, t = self.cor, self.t
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "ESPECTRO DE AUDIO")
        n = len(self.picos)
        bw = aw / n
        ganho = 0.25 + 0.75 * max(self.intens, self.amp)
        for i in range(n):
            v = (0.5 + 0.5 * math.sin(t * (2.2 + i * 0.31) + i * 1.7)) * (0.5 + 0.5 * math.sin(t * 1.3 + i * 0.6))
            v = 0.08 + 0.92 * v * ganho
            v = max(0.0, min(1.0, v))
            self.picos[i] = max(self.picos[i] - self.dt * 0.4, v)
            alt = int(v * (ah - 4))
            bx = int(ax + i * bw + 1)
            pygame.draw.rect(s, esc(cor, 0.45 + 0.55 * v), (bx, ay + ah - alt, max(2, int(bw) - 2), alt))
            py = int(ay + ah - self.picos[i] * (ah - 4)) - 2
            pygame.draw.line(s, esc(cor, 0.9), (bx, py), (bx + max(2, int(bw) - 2), py))

    def painel_trafego(self, s, x, y, w, h):
        cor = self.cor
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "TRAFEGO NEURAL")
        n = len(self.trafego)
        pts = []
        for i, v in enumerate(self.trafego):
            px = ax + i * aw / (n - 1)
            py = ay + ah - 4 - v * (ah - 22)
            pts.append((px, py))
            pygame.draw.line(s, esc(cor, 0.14), (px, py), (px, ay + ah - 2))
        pygame.draw.aalines(s, esc(cor, 0.95), False, pts)
        escrever(self.camada_texto, "%5.1f MB/S" % (self.trafego[-1] * 40), self.f_peq, esc(cor, 0.9), (ax + 2, ay + 1))

    def painel_modulos(self, s, x, y, w, h, estado):
        cor = self.cor
        ax, ay, aw, ah = self.painel(s, (x, y, w, h), "MODULOS")
        linhas = (
            ("MIC", "ATIVO" if estado == "OUVINDO" else "STANDBY", estado == "OUVINDO"),
            ("STT / LLM", "PROCESSANDO" if estado == "PROCESSANDO" else "PRONTO", estado == "PROCESSANDO"),
            ("TTS", "FALANDO" if estado == "FALANDO" else "PRONTO", estado == "FALANDO"),
        )
        for i, (nome, st, ativo) in enumerate(linhas):
            ry = ay + i * 19
            if ativo: pygame.draw.rect(s, esc(cor, 1.0), (ax, ry + 3, 9, 9))
            else: pygame.draw.rect(s, esc(cor, 0.35), (ax, ry + 3, 9, 9), 1)
            escrever(self.camada_texto, nome, self.f_peq, esc(cor, 0.9 if ativo else 0.6), (ax + 18, ry + 1))
            escrever(self.camada_texto, st, self.f_peq, esc(cor, 1.0 if ativo else 0.45), (ax + aw, ry + 1), "dir")

    def painel_texto(self, s, rect, titulo, texto, cor_texto, vazio, is_typing=False, scroll_offset=0):
        cor = self.cor
        area = self.painel(s, rect, titulo)
        
        pygame.draw.rect(self.camada_texto, (5, 5, 15, 255), area)
        pygame.draw.rect(self.camada_texto, (*esc(cor, 0.3), 255), area, 1)
        
        if texto: conteudo, c = texto, cor_texto
        else: 
            if is_typing: conteudo, c = "Digite aqui...", esc(cor_texto, 0.5)
            else: conteudo, c = vazio, esc(cor_texto, 0.5)
                
        if is_typing and int(self.t * 2) % 2 == 0:
            if texto: conteudo += "|"
        
        linhas = quebrar_texto(conteudo, self.f_texto, area.w - 20)
        passo = self.f_texto.get_linesize()
        max_linhas = max(1, area.h // passo)
        total_linhas = len(linhas)
        
        if total_linhas <= max_linhas:
            inicio = 0
        else:
            inicio = max(0, min(scroll_offset, total_linhas - max_linhas))
            
            altura_barra = area.h
            tamanho_thumb = max(20, int(altura_barra * (max_linhas / total_linhas)))
            pos_thumb = int((inicio / (total_linhas - max_linhas)) * (altura_barra - tamanho_thumb))
            
            pygame.draw.rect(self.camada_texto, (30, 30, 40, 200), (area.x + area.w - 6, area.y, 6, altura_barra))
            pygame.draw.rect(self.camada_texto, esc(cor, 0.8), (area.x + area.w - 6, area.y + pos_thumb, 6, tamanho_thumb))

        for i in range(inicio, min(inicio + max_linhas, total_linhas)):
            escrever(self.camada_texto, linhas[i], self.f_texto, c, (area.x + 5, area.y + 5 + (i - inicio) * passo))

    def desenhar_botoes(self, s):
        mx, my = CX, 590
        btn_w, btn_h = 140, 40
        
        cor_voz = (0, 255, 200) if MODO_ENTRADA == "VOZ" else esc(self.cor, 0.6)
        cor_txt = (0, 255, 200) if MODO_ENTRADA == "TEXTO" else esc(self.cor, 0.6)
        
        rect_voz = pygame.Rect(mx - btn_w - 10, my - 20, btn_w, btn_h)
        pygame.draw.rect(s, esc(cor_voz, 0.2), rect_voz)
        pygame.draw.rect(s, cor_voz, rect_voz, 2)
        escrever(self.camada_texto, "[F1] FALAR", self.f_peq, cor_voz, (rect_voz.centerx, rect_voz.centery), "centro")
        
        rect_txt = pygame.Rect(mx + 10, my - 20, btn_w, btn_h)
        pygame.draw.rect(s, esc(cor_txt, 0.2), rect_txt)
        pygame.draw.rect(s, cor_txt, rect_txt, 2)
        escrever(self.camada_texto, "[F2] DIGITAR", self.f_peq, cor_txt, (rect_txt.centerx, rect_txt.centery), "centro")
        
        return rect_voz, rect_txt

    def aplicar_glow(self):
        if self.quadro % 2 == 0 or self.glow_surf is None:
            p4 = pygame.transform.smoothscale(self.luz, (LARGURA // 4, ALTURA // 4))
            p8 = pygame.transform.smoothscale(p4, (LARGURA // 8, ALTURA // 8))
            p4.blit(p4.copy(), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            for _ in range(2): p8.blit(p8.copy(), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            p8_grande = pygame.transform.smoothscale(p8, (LARGURA // 4, ALTURA // 4))
            p4.blit(p8_grande, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.glow_surf = pygame.transform.smoothscale(p4, (LARGURA, ALTURA))
        self.tela.blit(self.glow_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def desenhar(self, estado, texto_usuario, texto_jarvis):
        self.quadro += 1
        s = self.luz
        s.fill((0, 0, 0))
        self.camada_texto.fill((0, 0, 0, 0))

        self.molduras(s)
        self.radar(s)
        self.varredura(s)
        self.aneis_giratorios(s)
        self.ondas_sonoras(s)
        self.nucleo(s)
        self.titulo(s)
        self.status(s, estado)

        self.painel_camera(s, 30, 24, 270, 150)
        self.painel_ondas(s, 30, 186, 270, 110)
        self.painel_sistema(s, 30, 308, 270, 140, estado)
        self.painel_medidores(s, 30, 460, 270, 96)

        xd = LARGURA - 30 - 270
        self.painel_hex(s, xd, 24, 270, 150)
        self.painel_espectro(s, xd, 186, 270, 110)
        self.painel_trafego(s, xd, 308, 270, 140)
        self.painel_modulos(s, xd, 460, 270, 96, estado)
        
        rect_voz, rect_txt = self.desenhar_botoes(s)

        is_typing = (MODO_ENTRADA == "TEXTO")
        
        self.painel_texto(s, (30, 570, 460, 140), "VOCE  >", texto_usuario, (170, 230, 255), "Aguardando...", is_typing, self.scroll_usuario)
        
        rect_jarvis = pygame.Rect(LARGURA - 30 - 460, 570, 460, 140)
        botao_copiar_rect = pygame.Rect(rect_jarvis.x + rect_jarvis.w - 80, rect_jarvis.y + 5, 60, 20)
        
        self.painel_texto(s, rect_jarvis, "JARVIS  >", texto_jarvis, (255, 255, 255), "Sistemas online.", False, self.scroll_jarvis)
        
        pygame.draw.rect(s, esc(self.cor, 0.2), botao_copiar_rect)
        pygame.draw.rect(s, esc(self.cor, 0.8), botao_copiar_rect, 1)
        escrever(self.camada_texto, "COPIAR", self.f_peq, esc(self.cor, 1.0), (botao_copiar_rect.centerx, botao_copiar_rect.centery), "centro")

        self.tela.blit(self.fundo, (0, 0))
        self.tela.blit(s, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if self.glow: self.aplicar_glow()
        self.tela.blit(self.camada_texto, (0, 0))
        
        return rect_voz, rect_txt, botao_copiar_rect

# ======================================================================
# 8. LOOP PRINCIPAL
# ======================================================================
def main():
    global RODANDO, FORCAR_ESTADO, MODO_ENTRADA, TEXTO_DIGITADO, TEXTO_USUARIO, PROCESSANDO_REQ

    pygame.init()
    pygame.mixer.init()
    pygame.mixer.set_num_channels(32)
    tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("VUNIX HUD")
    relogio = pygame.time.Clock()
    hud = HUD(tela)
    
    # Inicia a thread do modo mão
    threading.Thread(target=loop_modo_mao, daemon=True).start()
    
    teclas_estado = {pygame.K_1: "AGUARDANDO", pygame.K_2: "OUVINDO", pygame.K_3: "PROCESSANDO", pygame.K_4: "FALANDO"}

    while RODANDO:
        dt = min(relogio.tick(FPS) / 1000.0, 0.05)

        mouse_click = pygame.mouse.get_pressed()[0]
        mouse_pos = pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: RODANDO = False
            
            elif ev.type == pygame.MOUSEWHEEL:
                rect_jarvis = pygame.Rect(LARGURA - 30 - 460, 570, 460, 140)
                rect_usuario = pygame.Rect(30, 570, 460, 140)
                
                if rect_jarvis.collidepoint(mouse_pos):
                    hud.scroll_jarvis -= ev.y * 2 
                    if hud.scroll_jarvis < 0: hud.scroll_jarvis = 0
                
                if rect_usuario.collidepoint(mouse_pos):
                    hud.scroll_usuario -= ev.y * 2
                    if hud.scroll_usuario < 0: hud.scroll_usuario = 0

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: 
                    if MODO_ENTRADA == "TEXTO":
                        MODO_ENTRADA = "NENHUM"
                        TEXTO_DIGITADO = ""
                    else:
                        RODANDO = False
                
                elif ev.key == pygame.K_F1 and not PROCESSANDO_REQ:
                    MODO_ENTRADA = "VOZ"
                    threading.Thread(target=processar_requisicao, args=("VOZ",), daemon=True).start()
                elif ev.key == pygame.K_F2 and not PROCESSANDO_REQ:
                    MODO_ENTRADA = "TEXTO"
                    TEXTO_DIGITADO = ""
                    TEXTO_USUARIO = ""
                    hud.scroll_usuario = 0 
                
                elif MODO_ENTRADA == "TEXTO":
                    if ev.key == pygame.K_RETURN:
                        if TEXTO_DIGITADO.strip():
                            MODO_ENTRADA = "NENHUM"
                            threading.Thread(target=processar_requisicao, args=("TEXTO", TEXTO_DIGITADO), daemon=True).start()
                            hud.scroll_jarvis = 0 
                    elif ev.key == pygame.K_BACKSPACE:
                        TEXTO_DIGITADO = TEXTO_DIGITADO[:-1]
                    else:
                        if ev.unicode.isprintable():
                            TEXTO_DIGITADO += ev.unicode

                elif ev.key == pygame.K_F11: pygame.display.toggle_fullscreen()
                elif ev.key == pygame.K_g: hud.glow = not hud.glow
                elif ev.key == pygame.K_0: FORCAR_ESTADO = None
                elif ev.key in teclas_estado: FORCAR_ESTADO = teclas_estado[ev.key]

        estado = FORCAR_ESTADO or ESTADO_ATUAL
        if estado not in CORES_ESTADO: estado = "AGUARDANDO"
        
        if MODO_ENTRADA == "TEXTO":
            TEXTO_USUARIO = TEXTO_DIGITADO

        hud.fps = int(relogio.get_fps())
        hud.atualizar(dt, estado)
        rect_voz, rect_txt, botao_copiar = hud.desenhar(estado, TEXTO_USUARIO, TEXTO_JARVIS)
        
        if mouse_click and not PROCESSANDO_REQ:
            if rect_voz.collidepoint(mouse_pos) and MODO_ENTRADA != "VOZ":
                MODO_ENTRADA = "VOZ"
                threading.Thread(target=processar_requisicao, args=("VOZ",), daemon=True).start()
                hud.scroll_jarvis = 0
            elif rect_txt.collidepoint(mouse_pos) and MODO_ENTRADA != "TEXTO":
                MODO_ENTRADA = "TEXTO"
                TEXTO_DIGITADO = ""
                TEXTO_USUARIO = ""
                hud.scroll_usuario = 0
                pygame.time.wait(150)
            elif botao_copiar.collidepoint(mouse_pos) and TEXTO_JARVIS:
                abrir_janela_copia(TEXTO_JARVIS)
                pygame.time.wait(200)

        pygame.display.flip()

    pygame.quit()
    if os.path.exists("input.wav"):
        os.remove("input.wav")
    salvar_memoria()
    sys.exit()

if __name__ == "__main__":
    main()