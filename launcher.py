import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import struct
import pyaudiowpatch as pyaudio
import threading

NUM_BALLS = 500
BASE_RADIUS = 2.0
EXPAND_RADIUS = 5.0
NEIGHBORS = 4
BLOCKSIZE = 512

audio_level = 0.0
audio_lock = threading.Lock()


def find_loopback(p):
    best = None
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if "loopback" in dev["name"].lower():
            if "onn" in dev["name"].lower():
                return dev
            if best is None:
                best = dev
    return best


def audio_callback(in_data, frame_count, time_info, status):
    pass


def create_sphere_points(n):
    pts = []
    surface = int(n * 0.6)
    inner = n - surface
    for _ in range(surface):
        while True:
            x = random.gauss(0, 1)
            y = random.gauss(0, 1)
            z = random.gauss(0, 1)
            norm = math.sqrt(x*x + y*y + z*z)
            if norm > 0.01:
                break
        s = random.uniform(0.9, 1.1)
        inv = s / norm
        pts.append(x * inv)
        pts.append(y * inv)
        pts.append(z * inv)
    for _ in range(inner):
        x = random.gauss(0, 1)
        y = random.gauss(0, 1)
        z = random.gauss(0, 1)
        norm = math.sqrt(x*x + y*y + z*z)
        if norm < 0.01:
            norm = 1.0
        r = random.uniform(0.0, 0.85)
        inv = r / norm
        pts.append(x * inv)
        pts.append(y * inv)
        pts.append(z * inv)
    groups = [(pts[i*3], pts[i*3+1], pts[i*3+2]) for i in range(n)]
    random.shuffle(groups)
    result = []
    for g in groups:
        result.extend(g)
    return result


def compute_edges(points):
    n = NUM_BALLS
    edges = set()
    for i in range(n):
        xi = points[i*3]
        yi = points[i*3+1]
        zi = points[i*3+2]
        dists = []
        for j in range(n):
            dx = xi - points[j*3]
            dy = yi - points[j*3+1]
            dz = zi - points[j*3+2]
            dists.append((dx*dx + dy*dy + dz*dz, j))
        dists[i] = (1e30, i)
        dists.sort()
        for _, j in dists[:NEIGHBORS]:
            edges.add((min(i, j), max(i, j)))
    return list(edges)


def main():
    global audio_level

    pygame.init()
    disp_info = pygame.display.Info()
    w, h = disp_info.current_w, disp_info.current_h
    screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL | FULLSCREEN)
    pygame.display.set_caption("3D Particle Sphere")
    clock = pygame.time.Clock()

    glClearColor(0, 0, 0, 1)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glEnable(GL_POINT_SMOOTH)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, w / h, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    print("Generating sphere...")
    points = create_sphere_points(NUM_BALLS)
    print("Computing edges...")
    edges = compute_edges(points)
    num_edges = len(edges)
    print("Edges: " + str(num_edges))

    ei = [e[0] for e in edges]
    ej = [e[1] for e in edges]

    p = pyaudio.PyAudio()
    loopback = find_loopback(p)
    if loopback is None:
        print("No loopback device found")
        p.terminate()
        pygame.quit()
        return

    rate = int(loopback["defaultSampleRate"])
    channels = int(loopback["maxInputChannels"])
    print("Desktop audio: " + loopback["name"] + " (" + str(rate) + "Hz, " + str(channels) + "ch)")

    stream = p.open(format=pyaudio.paFloat32, channels=channels, rate=rate,
                    input=True, input_device_index=loopback["index"],
                    frames_per_buffer=BLOCKSIZE)

    ax = 0.0
    ay = 0.0
    current_r = BASE_RADIUS
    target_r = BASE_RADIUS
    zoom = -8.0
    zoom_vel = 0.0
    is_fullscreen = True
    smooth_vol = 0.0
    smooth_bass = 0.0
    beat_energy = 0.0
    pulse = 0.0
    pulse_phase = 0.0
    base_speed_x = 0.01
    base_speed_y = 0.015

    dot_layers = [
        (12.0, 0.03), (6.0, 0.08), (3.0, 0.18), (1.5, 0.45), (0.8, 1.0),
    ]

    print("Running!")
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if is_fullscreen:
                        is_fullscreen = False
                        w, h = 800, 600
                        screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL)
                        glViewport(0, 0, w, h)
                        glMatrixMode(GL_PROJECTION)
                        glLoadIdentity()
                        gluPerspective(45, w / h, 0.1, 100.0)
                        glMatrixMode(GL_MODELVIEW)
                    else:
                        running = False
                elif event.key == K_f:
                    if is_fullscreen:
                        is_fullscreen = False
                        w, h = 800, 600
                        screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL)
                    else:
                        is_fullscreen = True
                        disp_info = pygame.display.Info()
                        w, h = disp_info.current_w, disp_info.current_h
                        screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL | FULLSCREEN)
                    glViewport(0, 0, w, h)
                    glMatrixMode(GL_PROJECTION)
                    glLoadIdentity()
                    gluPerspective(45, w / h, 0.1, 100.0)
                    glMatrixMode(GL_MODELVIEW)
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    target_r = EXPAND_RADIUS if target_r == BASE_RADIUS else BASE_RADIUS
                elif event.button == 4:
                    zoom_vel += 0.3
                elif event.button == 5:
                    zoom_vel -= 0.3

        with audio_lock:
            target_vol = audio_level

        beat = 0.0
        bass = 0.0
        try:
            raw = stream.read(BLOCKSIZE)
            n = min(len(raw) // 4, BLOCKSIZE)
            data = struct.unpack_from('f' * n, raw, 0)
            dot = 0.0
            for v in data:
                dot += v * v
            target_vol = min(1.0, math.sqrt(dot / max(n, 1)) * 15.0)

            # frequency analysis for beat/bass detection using DFT over small window
            num_bins = 64
            bass_sum = 0.0
            for j in range(1, num_bins + 1):
                re = 0.0
                im = 0.0
                step = j * 2.0 * math.pi / n
                for k in range(0, n, 4):
                    v = data[k]
                    ph = step * k
                    re += v * math.cos(ph)
                    im -= v * math.sin(ph)
                mag = (re * re + im * im)
                if j <= 6:
                    bass_sum += mag
                else:
                    bass_sum += mag * 0.2
            bass = min(1.0, math.sqrt(bass_sum / (num_bins * n)) * 25.0)
        except Exception:
            pass

        smooth_vol += (target_vol - smooth_vol) * 0.15
        smooth_bass += (bass - smooth_bass) * 0.25

        # beat detection: sudden bass spike
        if bass > 0.35 and bass > smooth_bass * 1.5:
            beat = 1.0
        beat_energy += (beat - beat_energy) * 0.35

        # pulse: bounce radius on each beat
        pulse += (beat_energy * 0.8 - pulse) * 0.25
        pulse_phase += 0.35 * (1.0 + smooth_bass)

        current_r += (target_r + smooth_vol * 2.0 - current_r) * 0.06
        zoom += zoom_vel
        zoom_vel *= 0.92
        if abs(zoom_vel) < 0.001:
            zoom_vel = 0.0
        zoom = max(-25.0, min(-3.0, zoom))
        if zoom in (-3.0, -25.0):
            zoom_vel = 0.0

        # bass breathing + beat kick on the radius
        breathe = 1.0 + smooth_bass * 0.15
        kick = 1.0 + pulse * 0.45
        radius_now = current_r * breathe * kick

        ax += base_speed_x * (1.0 + smooth_vol * 4.0 + smooth_bass * 2.0)
        ay += base_speed_y * (1.0 + smooth_vol * 4.0 + smooth_bass * 2.0)

        cx = math.cos(ax)
        sx = math.sin(ax)
        cy = math.cos(ay)
        sy = math.sin(ay)

        bright = [0.0] * NUM_BALLS
        rx = [0.0] * NUM_BALLS
        ry = [0.0] * NUM_BALLS
        rz = [0.0] * NUM_BALLS

        # per-particle beat wobble phase (wave that cascades through the sphere)
        for i in range(NUM_BALLS):
            px = points[i * 3]
            py = points[i * 3 + 1]
            pz = points[i * 3 + 2]
            y1 = py * cx - pz * sx
            z1 = py * sx + pz * cx
            x1 = px * cy + z1 * sy
            z2 = -px * sy + z1 * cy
            wobble = 1.0 + pulse * 0.15 * (0.5 + 0.5 * math.sin(pulse_phase + i * 0.2))
            rx[i] = x1 * radius_now * wobble
            ry[i] = y1 * radius_now * wobble
            rz[i] = z2 * radius_now * wobble
            depth = z2 / radius_now * 0.5 + 0.5
            bright[i] = 0.3 + 0.7 * depth

        glow = smooth_bass * 0.5 + pulse * 0.8

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, zoom)
        glDepthMask(GL_FALSE)

        # draw lines with glBegin/glEnd
        glLineWidth(1.0 + smooth_vol * 2.0 + beat_energy * 4.0)
        glBegin(GL_LINES)
        for k in range(num_edges):
            bi = ei[k]
            bj = ej[k]
            lb = (bright[bi] + bright[bj]) * 0.5
            lc_r = lb * 1.0 + glow * 0.3
            lc_g = lb * 0.92 + glow * 0.3
            lc_b = lb * 0.78 + glow * 0.3
            lc_a = lb * (0.35 + smooth_vol * 0.6 + glow * 0.5)
            glColor4f(lc_r, lc_g, lc_b, lc_a)
            glVertex3f(rx[bi], ry[bi], rz[bi])
            glVertex3f(rx[bj], ry[bj], rz[bj])
        glEnd()

        # draw glow dots with glBegin/glEnd
        for pt_size, alpha_mul in dot_layers:
            glPointSize(pt_size + smooth_vol * 4.0 + beat_energy * 6.0)
            glBegin(GL_POINTS)
            for i in range(NUM_BALLS):
                b = bright[i]
                a = b * alpha_mul + smooth_vol * 0.3 + glow * 0.5
                v = b + smooth_vol * 0.1 + glow * 0.3
                glColor4f(v, v * 0.92, v * 0.78, a)
                glVertex3f(rx[i], ry[i], rz[i])
            glEnd()

        glDepthMask(GL_TRUE)
        pygame.display.flip()
        clock.tick(60)

    stream.stop_stream()
    stream.close()
    p.terminate()
    pygame.quit()


if __name__ == "__main__":
    main()
