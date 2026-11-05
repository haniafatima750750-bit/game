import json
import math
import os
import random
import sys
from pathlib import Path

import pygame


WIDTH = 420
HEIGHT = 720
GROUND_HEIGHT = 92
PIPE_WIDTH = 86
DIFFICULTIES = {
    "Normal": {"gap": 170, "interval": 1.45, "speed": 160},
    "Medium": {"gap": 150, "interval": 1.25, "speed": 185},
    "Hard": {"gap": 130, "interval": 1.05, "speed": 210},
}
GRAVITY = 900
FLAP_FORCE = -270
BIRD_X = 120

BG_TOP = (91, 174, 218)
BG_BOTTOM = (220, 239, 230)
GROUND_COLOR = (91, 165, 92)
GROUND_DARK = (47, 111, 75)
PIPE_COLOR = (83, 181, 91)
PIPE_SHADOW = (36, 112, 67)
PLANE_PAPER = (255, 250, 229)
PLANE_TOP = (226, 242, 231)
PLANE_FOLD = (154, 198, 187)
PLANE_SHADOW = (90, 133, 129)
PLANE_EYE = (40, 73, 78)
CLOUD_COLOR = (250, 254, 251)
INK = (24, 53, 65)
PANEL_COLOR = (21, 48, 62)
ACCENT_COLOR = (129, 205, 127)
MAX_NAME_LENGTH = 16


def score_file_path():
    if getattr(sys, "frozen", False):
        score_directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "YumcooksGame"
    else:
        score_directory = Path(__file__).resolve().parent
    return score_directory / "yumcook_scores.json"


def load_scores():
    path = score_file_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Could not read score data in {path}: {error}") from error
    except OSError as error:
        raise RuntimeError(f"Could not read score data in {path}: {error}") from error

    if not isinstance(data, dict) or not isinstance(data.get("players"), dict):
        raise RuntimeError(f"Score data in {path} has an invalid format.")
    players = data["players"]
    for player_key, player in players.items():
        if (
            not isinstance(player_key, str)
            or not isinstance(player, dict)
            or not isinstance(player.get("name"), str)
            or type(player.get("best_score")) is not int
            or type(player.get("last_score")) is not int
            or type(player.get("games_played")) is not int
        ):
            raise RuntimeError(f"Score data in {path} has an invalid player record.")
    return players


def save_score(player_name, score):
    players = load_scores()
    player_key = player_name.casefold()
    player = players.get(player_key, {
        "name": player_name,
        "best_score": 0,
        "last_score": 0,
        "games_played": 0,
    })
    player["name"] = player_name
    player["best_score"] = max(player["best_score"], score)
    player["last_score"] = score
    player["games_played"] += 1
    players[player_key] = player

    path = score_file_path()
    temporary_path = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps({"players": players}, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as error:
        raise RuntimeError(f"Could not save score data in {path}: {error}") from error
    return player


class Bird:
    def __init__(self):
        self.x = BIRD_X
        self.y = HEIGHT * 0.45
        self.velocity = 0
        self.radius = 16
        self.rotation = 0

    def flap(self):
        self.velocity = FLAP_FORCE

    def update(self, dt):
        self.velocity += GRAVITY * dt
        self.y += self.velocity * dt
        self.rotation = max(-1.2, min(1.6, self.velocity / 350))

    def draw(self, surface):
        sprite = pygame.Surface((56, 48), pygame.SRCALPHA)
        pygame.draw.ellipse(sprite, (30, 58, 64, 38), pygame.Rect(7, 34, 40, 7))
        pygame.draw.polygon(
            sprite,
            PLANE_SHADOW,
            [(4, 24), (52, 8), (31, 29), (39, 40), (27, 31)],
        )
        pygame.draw.polygon(sprite, PLANE_PAPER, [(4, 24), (52, 8), (30, 28)])
        pygame.draw.polygon(sprite, PLANE_TOP, [(4, 24), (30, 28), (18, 19)])
        pygame.draw.polygon(sprite, (240, 247, 232), [(4, 24), (30, 28), (39, 40)])
        pygame.draw.polygon(sprite, PLANE_FOLD, [(30, 28), (52, 8), (39, 40)])
        pygame.draw.line(sprite, (255, 255, 250), (8, 23), (46, 11), 2)
        pygame.draw.line(sprite, PLANE_SHADOW, (30, 28), (39, 39), 1)
        pygame.draw.ellipse(sprite, PLANE_EYE, pygame.Rect(25, 21, 3, 5))
        pygame.draw.ellipse(sprite, PLANE_EYE, pygame.Rect(32, 20, 3, 5))
        pygame.draw.circle(sprite, (242, 147, 143), (24, 28), 2)
        pygame.draw.circle(sprite, (242, 147, 143), (36, 27), 2)
        pygame.draw.arc(sprite, PLANE_EYE, pygame.Rect(27, 24, 7, 6), math.pi, 2 * math.pi, 1)

        rotated = pygame.transform.rotate(sprite, -math.degrees(self.rotation))
        surface.blit(rotated, rotated.get_rect(center=(round(self.x), round(self.y))))

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)


class Pipe:
    def __init__(self, x, gap_height, speed):
        self.x = x
        self.gap_height = gap_height
        self.gap_top = random.randint(120, 380)
        self.speed = speed
        self.scored = False

    def update(self, dt):
        self.x -= self.speed * dt

    def draw(self, surface):
        top_height = self.gap_top
        bottom_y = self.gap_top + self.gap_height
        bottom_height = HEIGHT - GROUND_HEIGHT - bottom_y

        def draw_pipe_section(y, height, cap_at_bottom):
            if height <= 0:
                return
            shaft = pygame.Rect(round(self.x + 7), y, PIPE_WIDTH - 14, height)
            pygame.draw.rect(surface, PIPE_SHADOW, shaft, border_radius=8)
            pygame.draw.rect(
                surface,
                PIPE_COLOR,
                pygame.Rect(shaft.x + 4, y, shaft.width - 12, height),
                border_radius=5,
            )
            pygame.draw.line(
                surface,
                (159, 221, 143),
                (shaft.x + 9, y + 3),
                (shaft.x + 9, y + height - 3),
                3,
            )
            pygame.draw.line(
                surface,
                PIPE_SHADOW,
                (shaft.right - 7, y + 3),
                (shaft.right - 7, y + height - 3),
                3,
            )

            if cap_at_bottom:
                cap_y = y + height - 18
            else:
                cap_y = y
            cap = pygame.Rect(round(self.x), cap_y, PIPE_WIDTH, 20)
            pygame.draw.rect(surface, PIPE_SHADOW, cap.move(0, 3), border_radius=6)
            pygame.draw.rect(surface, PIPE_COLOR, cap, border_radius=6)
            pygame.draw.rect(
                surface,
                (159, 221, 143),
                pygame.Rect(cap.x + 7, cap.y + 3, 5, cap.height - 6),
                border_radius=2,
            )
            pygame.draw.line(
                surface,
                (190, 231, 163),
                (cap.x + 8, cap.y + 2),
                (cap.right - 8, cap.y + 2),
                2,
            )

        draw_pipe_section(0, top_height, True)
        draw_pipe_section(bottom_y, bottom_height, False)

    def collides(self, bird):
        bird_rect = bird.get_rect()
        top_rect = pygame.Rect(self.x, 0, PIPE_WIDTH, self.gap_top)
        bottom_rect = pygame.Rect(self.x, self.gap_top + self.gap_height, PIPE_WIDTH, HEIGHT - GROUND_HEIGHT - (self.gap_top + self.gap_height))
        if bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect):
            return True
        return False


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Yumcook's Game")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon, (83, 151, 129), (16, 16), 16)
        pygame.draw.polygon(icon, PLANE_PAPER, [(4, 16), (29, 6), (17, 17)])
        pygame.draw.polygon(icon, PLANE_TOP, [(4, 16), (17, 17), (10, 12)])
        pygame.draw.polygon(icon, PLANE_FOLD, [(17, 17), (29, 6), (22, 26)])
        pygame.draw.line(icon, PLANE_SHADOW, (17, 17), (22, 26), 1)
        pygame.display.set_icon(icon)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 48, bold=True)
        self.title_font = pygame.font.SysFont("segoeui", 42, bold=True)
        self.subtitle_font = pygame.font.SysFont("segoeui", 26, bold=True)
        self.message_font = pygame.font.SysFont("segoeui", 23, bold=True)
        self.hint_font = pygame.font.SysFont("segoeui", 18)
        self.small_font = pygame.font.SysFont("segoeui", 15)
        self.input_font = pygame.font.SysFont("segoeui", 30)
        self.sky_surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            color = tuple(
                round(top + (bottom - top) * ratio)
                for top, bottom in zip(BG_TOP, BG_BOTTOM)
            )
            pygame.draw.line(self.sky_surface, color, (0, y), (WIDTH, y))

        self.reset()

    def reset(self):
        self.state = "name_entry"
        self.player_name = ""
        self.name_input = ""
        self.difficulty = None
        pygame.key.start_text_input()
        self.reset_round()

    def reset_round(self):
        self.bird = Bird()
        self.pipes = []
        self.pipe_timer = 0.0
        self.score = 0
        self.score_saved = False
        self.score_save_error = None

    def start(self, difficulty_name):
        if difficulty_name not in DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {difficulty_name}")
        self.difficulty = difficulty_name
        self.reset_round()
        self.state = "playing"
        self.bird.flap()

    def confirm_name(self):
        self.player_name = self.name_input.strip()
        if self.player_name:
            players = load_scores()
            self.player_record = players.get(self.player_name.casefold(), {
                "name": self.player_name,
                "best_score": 0,
                "last_score": 0,
                "games_played": 0,
            })
            pygame.key.stop_text_input()
            self.state = "level_select"

    def restart(self):
        self.reset_round()
        self.state = "level_select"

    def end_game(self):
        if self.state == "game_over":
            return

        self.state = "game_over"
        if self.score_saved:
            return
        self.score_saved = True
        try:
            self.player_record = save_score(self.player_name, self.score)
        except RuntimeError as error:
            self.score_save_error = str(error)
            print(self.score_save_error, file=sys.stderr)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False

        if self.state == "name_entry":
            if event.type == pygame.TEXTINPUT:
                available = MAX_NAME_LENGTH - len(self.name_input)
                self.name_input += "".join(
                    character for character in event.text if character.isprintable()
                )[:available]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.name_input = self.name_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.confirm_name()
            return True

        if event.type == pygame.KEYDOWN:
            if self.state == "level_select":
                difficulty_keys = {
                    pygame.K_1: "Normal",
                    pygame.K_2: "Medium",
                    pygame.K_3: "Hard",
                }
                if event.key in difficulty_keys:
                    self.start(difficulty_keys[event.key])
            elif event.key in (pygame.K_SPACE, pygame.K_UP):
                if self.state == "playing":
                    self.bird.flap()
                elif self.state == "game_over":
                    self.restart()
            elif event.key == pygame.K_r and self.state != "name_entry":
                self.restart()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == "level_select":
                for difficulty_name, button in self.difficulty_buttons():
                    if button.collidepoint(event.pos):
                        self.start(difficulty_name)
                        break
            elif self.state == "playing":
                self.bird.flap()
            elif self.state == "game_over":
                self.restart()

        return True

    @staticmethod
    def difficulty_buttons():
        return [
            (name, pygame.Rect(56, 345 + index * 68, WIDTH - 112, 58))
            for index, name in enumerate(DIFFICULTIES)
        ]

    def update(self, dt):
        if self.state == "playing":
            self.bird.update(dt)
            self.pipe_timer += dt

            settings = DIFFICULTIES[self.difficulty]
            if self.pipe_timer >= settings["interval"]:
                self.pipes.append(Pipe(WIDTH + 40, settings["gap"], settings["speed"]))
                self.pipe_timer = 0.0

            for pipe in self.pipes:
                pipe.update(dt)
                if not pipe.scored and pipe.x + PIPE_WIDTH < self.bird.x:
                    pipe.scored = True
                    self.score += 1

            self.pipes = [pipe for pipe in self.pipes if pipe.x + PIPE_WIDTH > -20]

            for pipe in self.pipes:
                if pipe.collides(self.bird):
                    self.end_game()
                    break

            if self.bird.y + self.bird.radius >= HEIGHT - GROUND_HEIGHT:
                self.end_game()
            if self.bird.y - self.bird.radius <= 0:
                self.bird.y = self.bird.radius
                self.bird.velocity = 0

        elif self.state == "level_select":
            self.bird.update(dt * 0.5)
            self.bird.y = HEIGHT * 0.45 + math.sin(pygame.time.get_ticks() / 250) * 6
            if self.bird.y <= 60 or self.bird.y >= HEIGHT - GROUND_HEIGHT - 60:
                self.bird.velocity *= -0.2

        elif self.state == "game_over":
            self.bird.velocity += GRAVITY * dt * 0.8
            self.bird.y += self.bird.velocity * dt * 0.8

    def draw_card(self, rect):
        pygame.draw.rect(self.screen, (30, 72, 81), rect.move(0, 7), border_radius=22)
        pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=22)
        pygame.draw.rect(self.screen, (91, 150, 151), rect, width=1, border_radius=22)

    def draw_background(self):
        self.screen.blit(self.sky_surface, (0, 0))

        sun = (350, 112)
        pygame.draw.circle(self.screen, (255, 242, 193), sun, 39)
        pygame.draw.circle(self.screen, (255, 249, 218), sun, 31)

        drift = (pygame.time.get_ticks() // 45) % (WIDTH + 140)
        for index, (base_x, y, scale) in enumerate(
            ((48, 125, 1.0), (210, 205, 0.75), (365, 285, 0.9))
        ):
            x = (base_x - drift * (0.25 + index * 0.08)) % (WIDTH + 100) - 50
            cloud_width = round(64 * scale)
            cloud_height = round(22 * scale)
            cloud_color = CLOUD_COLOR
            pygame.draw.ellipse(
                self.screen,
                (180, 211, 210),
                pygame.Rect(round(x), y + 7, cloud_width, cloud_height),
            )
            pygame.draw.ellipse(
                self.screen,
                cloud_color,
                pygame.Rect(round(x + 7), y, cloud_width - 10, cloud_height),
            )
            pygame.draw.circle(
                self.screen,
                cloud_color,
                (round(x + cloud_width * 0.42), y + 2),
                round(13 * scale),
            )
            pygame.draw.circle(
                self.screen,
                cloud_color,
                (round(x + cloud_width * 0.67), y + 4),
                round(10 * scale),
            )

        pygame.draw.polygon(
            self.screen,
            (160, 202, 182),
            [(0, 510), (62, 457), (120, 506), (204, 440), (290, 510), (356, 466), (420, 502), (420, 628), (0, 628)],
        )
        pygame.draw.polygon(
            self.screen,
            (116, 178, 133),
            [(0, 548), (76, 494), (158, 550), (246, 483), (333, 547), (420, 498), (420, 628), (0, 628)],
        )

        ground_top = HEIGHT - GROUND_HEIGHT
        pygame.draw.rect(self.screen, GROUND_DARK, (0, ground_top, WIDTH, GROUND_HEIGHT))
        pygame.draw.rect(self.screen, GROUND_COLOR, (0, ground_top + 7, WIDTH, GROUND_HEIGHT - 7))
        pygame.draw.line(self.screen, (159, 207, 116), (0, ground_top + 7), (WIDTH, ground_top + 7), 3)

        for x in range(-8, WIDTH + 12, 24):
            pygame.draw.line(
                self.screen,
                (126, 190, 101),
                (x, ground_top + 15),
                (x + 5, ground_top + 25),
                2,
            )
        for x in range(16, WIDTH, 52):
            pygame.draw.ellipse(
                self.screen,
                (69, 142, 83),
                pygame.Rect(x, ground_top + 48 + (x % 3) * 4, 17, 7),
            )

    def draw(self):
        self.draw_background()
        for pipe in self.pipes:
            pipe.draw(self.screen)

        self.bird.draw(self.screen)

        if self.state == "name_entry":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((9, 29, 42, 55))
            self.screen.blit(overlay, (0, 0))

            panel = pygame.Rect(24, 205, WIDTH - 48, 260)
            self.draw_card(panel)

            title = self.title_font.render("Yumcook's Game", True, (246, 251, 243))
            self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 255)))
            prompt = self.message_font.render("What's your name?", True, (190, 220, 216))
            self.screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, 310)))

            name_box = pygame.Rect(58, 340, WIDTH - 116, 48)
            pygame.draw.rect(self.screen, (239, 247, 236), name_box, border_radius=12)
            pygame.draw.rect(self.screen, (147, 203, 151), name_box, width=2, border_radius=12)
            displayed_name = self.name_input or "Type your name..."
            name_color = INK if self.name_input else (113, 145, 145)
            name_text = self.input_font.render(displayed_name, True, name_color)
            self.screen.blit(name_text, name_text.get_rect(midleft=(name_box.x + 12, name_box.centery)))

            hint = self.hint_font.render("TYPE YOUR NAME, THEN PRESS ENTER", True, (190, 220, 216))
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 414)))

        if self.state == "level_select":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((9, 29, 42, 55))
            self.screen.blit(overlay, (0, 0))

            panel = pygame.Rect(24, 145, WIDTH - 48, 440)
            self.draw_card(panel)

            welcome = self.subtitle_font.render(
                f"HELLO, {self.player_name}!", True, (169, 222, 203)
            )
            welcome_rect = welcome.get_rect(center=(WIDTH // 2, 215))
            self.screen.blit(welcome, welcome_rect)

            title = self.title_font.render("Yumcook's Game", True, (246, 251, 243))
            title_rect = title.get_rect(center=(WIDTH // 2, 255))
            self.screen.blit(title, title_rect)

            prompt = self.message_font.render("CHOOSE YOUR DIFFICULTY", True, (244, 207, 135))
            self.screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, 305)))

            descriptions = {
                "Normal": "Wide gaps  |  Gentle pace",
                "Medium": "Closer gaps  |  Faster pipes",
                "Hard": "Narrow gaps  |  Quick reflexes",
            }
            for index, (difficulty_name, button) in enumerate(self.difficulty_buttons()):
                pygame.draw.rect(self.screen, (13, 36, 48), button.move(0, 4), border_radius=14)
                pygame.draw.rect(self.screen, (49, 100, 84), button, border_radius=14)
                pygame.draw.rect(self.screen, (99, 158, 120), button, width=1, border_radius=14)
                label = self.message_font.render(
                    f"{index + 1}  {difficulty_name}", True, (247, 250, 239)
                )
                self.screen.blit(label, label.get_rect(center=(button.centerx, button.centery - 10)))
                detail = self.small_font.render(
                    descriptions[difficulty_name], True, (190, 218, 196)
                )
                self.screen.blit(detail, detail.get_rect(center=(button.centerx, button.centery + 12)))

            best = self.hint_font.render(
                f"Personal best: {self.player_record['best_score']}",
                True,
                (190, 220, 216),
            )
            self.screen.blit(best, best.get_rect(center=(WIDTH // 2, 550)))
            hint = self.hint_font.render(
                "CLICK A LEVEL OR PRESS 1, 2, OR 3", True, (190, 220, 216)
            )
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 580)))

        if self.state == "game_over":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 28, 35, 155))
            self.screen.blit(overlay, (0, 0))
            panel = pygame.Rect(34, 160, WIDTH - 68, 300)
            self.draw_card(panel)
            text = self.title_font.render("Run complete", True, (246, 251, 243))
            score_text = self.font.render(f"{self.score}", True, (255, 224, 152))
            greeting = self.message_font.render(
                f"Nice flying, {self.player_name}!", True, (169, 222, 203)
            )
            self.screen.blit(greeting, greeting.get_rect(center=(WIDTH // 2, 205)))
            self.screen.blit(text, text.get_rect(center=(WIDTH // 2, 254)))
            self.screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, 312)))
            if self.score_save_error:
                status = self.hint_font.render(
                    "Score could not be saved.", True, (255, 190, 170)
                )
            else:
                best_score = self.player_record["best_score"]
                status = self.hint_font.render(
                    f"Personal best: {best_score}", True, (190, 220, 216)
                )
            self.screen.blit(status, status.get_rect(center=(WIDTH // 2, 359)))
            hint = self.hint_font.render(
                "SPACE OR CLICK TO PICK A NEW LEVEL", True, (190, 220, 216)
            )
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 414)))

        if self.state in {"playing", "game_over"}:
            score_box = pygame.Rect(WIDTH // 2 - 44, 18, 88, 62)
            pygame.draw.rect(self.screen, (30, 72, 81), score_box.move(0, 4), border_radius=18)
            pygame.draw.rect(self.screen, PANEL_COLOR, score_box, border_radius=18)
            pygame.draw.rect(self.screen, (120, 174, 158), score_box, width=1, border_radius=18)
            score_text = self.font.render(str(self.score), True, (255, 232, 174))
            self.screen.blit(score_text, score_text.get_rect(center=score_box.center))

            mode_box = pygame.Rect(16, 22, 126, 34)
            pygame.draw.rect(self.screen, (22, 54, 65), mode_box, border_radius=12)
            mode_text = self.hint_font.render(
                self.difficulty.upper(), True, (228, 241, 220)
            )
            self.screen.blit(mode_text, mode_text.get_rect(center=mode_box.center))

        pygame.display.flip()

    def run(self):
        running = True
        last_time = pygame.time.get_ticks() / 1000.0

        while running:
            now = pygame.time.get_ticks() / 1000.0
            dt = now - last_time
            last_time = now

            for event in pygame.event.get():
                if not self.handle_event(event):
                    running = False

            self.update(dt)
            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
