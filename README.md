# Audio Reactive Particle Sphere

A fullscreen 3D OpenGL particle sphere that reacts to your desktop audio in real time. The sphere pulses, breathes, and glows in sync with the bass and beats of whatever music you're playing.

![Python](https://img.shields.io/badge/python-3.14-blue)

## Features

- Captures **desktop (loopback) audio** on Windows via WASAPI
- **Beat detection** with kick-drum triggering a sharp pulse
- **Bass breathing** — low-frequency energy makes the sphere expand and contract
- **Pulse wave** cascading through the particles on each beat
- Beat-driven **brightness flashes** and glowing lines
- 900 glowing dots connected to their nearest neighbors
- Fullscreen with scroll-to-zoom

## Requirements

- Windows (uses WASAPI loopback capture)
- Python 3.14+

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python launcher.py
```

Play some music and the sphere will react.

### Controls

| Key / Input | Action |
|-------------|--------|
| `ESC` | Quit |
| `F` | Toggle fullscreen |
| Left click | Toggle sphere expansion |
| Scroll | Zoom in / out |

## How it works

The app captures desktop audio through the WASAPI loopback device using `pyaudiowpatch`. Each frame it reads a block of audio and performs a lightweight frequency analysis in the main loop (no background threads — required for stability on Python 3.14). Bass energy drives the sphere's breathing radius, and sudden bass spikes are detected as beats, triggering a pulsing ripple that cascades through the 900 particles. The whole sphere spins faster with the music, and the lines glow brighter on each hit.
