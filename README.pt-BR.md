# BFF Dance

*[Read in English](README.md)*

**Best Friends Forever Dance** - Um jogo de dança cooperativo para Raspberry Pi 5 com aceleração Hailo 8.

## Conceito

Dois jogadores dançam juntos: um faz poses e movimentos, o outro imita. Quanto mais parecido, mais pontos! Descubra easter eggs fazendo gestos colaborativos como corações ou high-fives.

### Modos de Jogo

- **Modo Desafio**: Turnos alternados - um faz, outro imita
- **Modo Coreografia**: Grave uma dança inteira e desafie amigos a imitarem

### Características

- Detecção de poses em tempo real via Hailo 8 (~27 FPS)
- Easter eggs colaborativos (coração, high-five, poses espelhadas)
- Sistema de combos e pontuação
- Classificação de conteúdo por idade
- Temas personalizáveis (fofurices, aventura, mistureba)
- Coletáveis interativos na tela

## Requisitos de Hardware

- Raspberry Pi 5
- Hailo 8/8L AI Accelerator
- Câmera compatível (testado com IMX708)
- Monitor/TV para exibição

## Requisitos de Software

- Raspberry Pi OS (Bookworm ou superior)
- HailoRT 4.20+
- Python 3.11+
- Picamera2
- OpenCV 4.6+
- Pygame 2.1+

## Instalação

```bash
# Clonar repositório
git clone https://github.com/marcelomessa/bffdance.git
cd bffdance

# Instalar dependências Python
pip install -r requirements.txt

# Verificar Hailo
hailortcli --version
```

## Uso

```bash
# Teste de detecção de poses (headless)
python main.py --test-headless

# Teste com visualização (requer display)
python main.py --test

# Iniciar jogo
python main.py
```

## Estrutura do Projeto

```
bffdance/
├── src/
│   ├── core/           # Detecção de poses, comparação, buffer
│   ├── game/           # Lógica do jogo, modos, jogadores
│   ├── detection/      # Detecção de turnos e gestos
│   ├── graphics/       # Renderização (Pygame)
│   ├── audio/          # Música e efeitos sonoros
│   ├── data/           # Persistência (SQLite)
│   └── config/         # Configurações
├── assets/             # Recursos (imagens, sons, fontes)
├── tests/              # Testes automatizados
├── main.py             # Entry point
└── requirements.txt    # Dependências Python
```

## Classificação Etária

Todos os jogadores têm acesso a todas as funcionalidades. A classificação etária apenas filtra conteúdo inapropriado:

| Idade | Filtro de Conteúdo |
|-------|-------------------|
| 4-7   | Apenas imagens, músicas e linguagem apropriadas para família |
| 8-12  | Conteúdo moderado permitido |
| 13+   | Sem restrições de conteúdo |

## Temas de Coletáveis

- **Fofurices**: panda, cachorro, capivara, gatinho, coelhinho, unicórnio
- **Aventura**: astronauta, foguete, carrinho, bola, dinossauro, robô
- **Mistureba**: todos os itens misturados

## Contribuindo

Contribuições são bem-vindas! Por favor, abra uma issue para discutir mudanças significativas antes de submeter um PR.

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

*Powered by AI*
