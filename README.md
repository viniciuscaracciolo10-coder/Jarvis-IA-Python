# 🤖 VUNIX HUD: Assistente Virtual com IA e Controle Gestual

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.x-green.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-orange.svg)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow.svg)

Um assistente virtual inspirado no **J.A.R.V.I.S. (Homem de Ferro)**, construído do zero em Python. O projeto integra uma interface gráfica estilo HUD (Heads-Up Display) com Inteligência Artificial conversacional, síntese de voz e **Visão Computacional** para controle do sistema operacional por gestos das mãos.

*(Substitua o texto acima por um print do seu HUD)*
<!-- ![Print do HUD](link_para_o_print.png) -->

## 🚀 Funcionalidades

O projeto foi dividido em três pilares principais: Inteligência, Interface e Visão.

### 🧠 Inteligência Artificial e Automação
- **Conversação com Memória:** Integração com a API da Groq (Llama 3) com histórico de conversa salvo em JSON. O Jarvis lembra do contexto (ex: onde você mora).
- **Síntese de Voz (TTS):** Respostas faladas com vozes neurais ultrarrealistas (Edge-TTS/gTTS) fatiadas para latência quase zero.
- **Comandos de Voz:** Transcrição de áudio em tempo real usando Whisper.
- **Automação do Windows:** Abre programas, envia mensagens no WhatsApp Web, toca músicas no YouTube e consulta a previsão do tempo real (via API wttr.in).
- **Geração de Mídia:** Criação de imagens (via Pollinations AI) e modelos 3D (via three.ws) a partir de comandos de voz.

### 👁️ Visão Computacional e Controle Gestual (NUI)
Usando OpenCV e MediaPipe para rastrear a mão do usuário em tempo real (rodando em thread separada).
- ✊ **Punho Fechado / ✋ Mão Aberta:** Play/Pause em players de mídia.
- 🤏 **Gesto de Pinça:** Controle de volume do sistema (com filtro de média móvel para evitar tremores da mão).
- 👆 **Swipe para Cima/Baixo:** Minimizar/Restaurar todas as janelas (Win + D).
- 👉 **Swipe para Esquerda/Direita:** Alternar entre janelas (Alt + Tab).

### 🖥️ Interface Gráfica (HUD)
- Interface 3D simulada (Pseudo-3D) rodando a 60 FPS com Pygame.
- Radar animado, gráficos de espectro de áudio e telemetria do sistema.
- Suporte a scroll de texto e janela integrada para cópia de código gerado pela IA.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3
- **Interface:** Pygame, Tkinter
- **Áudio:** PyAudio, gTTS, Edge-TTS
- **IA e APIs:** Groq (Whisper e Llama 3), Pollinations AI, three.ws, wttr.in
- **Visão Computacional:** OpenCV, MediaPipe
- **Automação:** PyAutoGUI, PyWhatKit, subprocess

## ⚙️ Instalação e Execução

### Pré-requisitos
- Python 3.10 ou superior.
- Uma webcam funcional (para o modo gestual).
- Uma chave de API gratuita na [Groq Cloud](https://console.groq.com/).

### Passo a Passo

1. Clone o repositório:
   bash
   git clone https://github.com/SEU_USUARIO/vunix-hud-jarvis.git
   cd vunix-hud-jarvis
   

2. Instale as dependências:
   bash
   pip install -r requirements.txt
   
   *(Crie um arquivo requirements.txt com: pygame, pyaudio, groq, gtts, edge-tts, opencv-python, mediapipe, pyautogui, pywhatkit, requests)*

3. Configure as chaves de API:
   Crie um arquivo config.py na raiz do projeto e adicione sua chave:
   python
   CHAVE_GROQ = "gsk_sua_chave_aqui"
   CHAVE_POLLINATIONS = "sk_sua_chave_aqui"
   
   *(Atenção: Adicione o config.py ao seu .gitignore).*

4. Baixe o modelo do MediaPipe:
   Baixe o arquivo hand_landmarker.task no [site oficial do MediaPipe](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker) e coloque na raiz do projeto.

5. Execute o assistente:
   bash
   python main.py
   

## 🎮 Como Usar

- **Aperte F1:** Para falar com o Jarvis via microfone.
- **Aperte F2:** Para digitar a pergunta.
- **Modo Gestual:** Fale "Jarvis, ligar modo mão" e faça os gestos na frente da câmera.
- **Aperte G:** Liga/desliga o efeito de brilho (Glow) do HUD para melhorar a performance.

## 🧠 Arquitetura do Código

O projeto foi construído pensando em **concorrência e separação de responsabilidades**:
- A interface (Pygame) roda na thread principal para manter os 60 FPS.
- O processamento de áudio, IA e visão computacional rodam em threads secundárias (threading), evitando que o HUD congele enquanto a IA "pensa" ou a câmera processa os frames.
- A memória de conversa é persistida localmente em JSON, com limite de contexto para economizar tokens da API.

## 👨‍💻 Autor

Desenvolvido por **Vinicius (12 anos)**.
Estudante apaixonado por Engenharia de Software, Inteligência Artificial e Cibersegurança.

---
*Este projeto foi construído para fins de estudo, explorando a integração de LLMs, visão computacional e interfaces gráficas em Python.*
