# BFF Dance

*[Leia em Português](README.pt-BR.md)*

**Best Friends Forever Dance** - A cooperative dance game for Raspberry Pi 5 with Hailo 8 acceleration.

## Concept

Two players dance together: one strikes poses and moves, the other imitates. The more similar, the more points! Discover easter eggs by making collaborative gestures like hearts or high-fives.

### Game Modes

- **Challenge Mode**: Alternating turns - one performs, the other imitates
- **Choreography Mode**: Record a full dance and challenge friends to imitate

### Features

- Real-time pose detection via Hailo 8 (~27 FPS)
- Collaborative easter eggs (heart, high-five, mirrored poses)
- Combo and scoring system
- Age-based content rating
- Customizable themes (cute, adventure, mixed)
- Interactive on-screen collectibles

## Hardware Requirements

- Raspberry Pi 5
- Hailo 8/8L AI Accelerator
- Compatible camera (tested with IMX708)
- Monitor/TV for display

## Software Requirements

- Raspberry Pi OS (Bookworm or later)
- HailoRT 4.20+
- Python 3.11+
- Picamera2
- OpenCV 4.6+
- Pygame 2.1+

## Installation

```bash
# Clone repository
git clone https://github.com/marcelomessa/bffdance.git
cd bffdance

# Install Python dependencies
pip install -r requirements.txt

# Verify Hailo
hailortcli --version
```

## Usage

```bash
# Pose detection test (headless)
python main.py --test-headless

# Test with visualization (requires display)
python main.py --test

# Start game
python main.py
```

## Project Structure

```
bffdance/
├── src/
│   ├── core/           # Pose detection, comparison, buffer
│   ├── game/           # Game logic, modes, players
│   ├── detection/      # Turn and gesture detection
│   ├── graphics/       # Rendering (Pygame)
│   ├── audio/          # Music and sound effects
│   ├── data/           # Persistence (SQLite)
│   └── config/         # Settings
├── assets/             # Resources (images, sounds, fonts)
├── tests/              # Automated tests
├── main.py             # Entry point
└── requirements.txt    # Python dependencies
```

## Age Rating

All players have access to all features. Age rating only filters inappropriate content:

| Age   | Content Filter |
|-------|----------------|
| 4-7   | Family-friendly images, music, and language only |
| 8-12  | Moderate content allowed |
| 13+   | No content restrictions |

## Collectible Themes

- **Cute**: panda, dog, capybara, kitten, bunny, unicorn
- **Adventure**: astronaut, rocket, car, ball, dinosaur, robot
- **Mixed**: all items combined

## Contributing

Contributions are welcome! Please open an issue to discuss significant changes before submitting a PR.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Powered by AI*
