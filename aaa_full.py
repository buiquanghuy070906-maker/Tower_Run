import pygame
import sys
import os
import random
import math

# -------------------------
# Config
# -------------------------
WIDTH, HEIGHT = 900, 700
FPS = 60
WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
GREEN = (70, 200, 120)
SPRITE_W, SPRITE_H = 160, 160

# -------------------------
# File helpers
# -------------------------
def find_best_file(prefix, exts=("png","jpg","jpeg","gif","bmp","webp")):
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    search_dirs = [base_dir, os.path.join(base_dir, "assets")]
    if os.getcwd() not in search_dirs:
        search_dirs.append(os.getcwd())
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        try:
            for fname in sorted(os.listdir(d)):
                low = fname.lower()
                if low.startswith(prefix.lower()):
                    for ext in exts:
                        if low.endswith("." + ext.lower()):
                            return os.path.join(d, fname)
                    if "." in fname:
                        return os.path.join(d, fname)
        except Exception:
            continue
    return None

def try_load_image_fuzzy(prefix, size):
    p = find_best_file(prefix)
    if not p:
        return None
    try:
        surf = pygame.image.load(p).convert_alpha()
        surf = pygame.transform.scale(surf, size)
        print(f"[image] Loaded {os.path.basename(p)} for '{prefix}'")
        return surf
    except Exception as e:
        print(f"[image] Failed to load {p}: {e}")
        return None

def try_load_avatar_by_prefix(base_prefix, size):
    p = find_best_file("avatar" + base_prefix)
    if not p:
        p = find_best_file(base_prefix)
    if not p:
        return None
    try:
        surf = pygame.image.load(p).convert_alpha()
        surf = pygame.transform.scale(surf, size)
        return surf
    except Exception:
        return None

# -------------------------
# Font loader
# -------------------------
def get_font(size, force_ttf_filename=None, prefer_family="arial"):
    if not pygame.font.get_init():
        pygame.font.init()
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    candidates = []
    if force_ttf_filename:
        candidates.append(os.path.join(base_dir, force_ttf_filename))
        candidates.append(os.path.join(base_dir, "assets", force_ttf_filename))
    candidates += [
        os.path.join(base_dir, "NotoSans-Regular.ttf"),
        os.path.join(base_dir, "DejaVuSans.ttf"),
        os.path.join(base_dir, "LiberationSans-Regular.ttf"),
        os.path.join(base_dir, "Arial.ttf"),
        os.path.join(base_dir, "assets", "NotoSans-Regular.ttf"),
        os.path.join(base_dir, "assets", "DejaVuSans.ttf"),
    ]
    for p in candidates:
        try:
            if os.path.isfile(p):
                return pygame.font.Font(p, size)
        except Exception:
            pass
    try:
        return pygame.font.SysFont(prefer_family, size)
    except Exception:
        return pygame.font.Font(None, size)

# -------------------------
# Vector sprite fallback
# -------------------------
class AnimatedSprite:
    def __init__(self, frames, frame_time=150):
        self.frames = frames
        self.frame_time = frame_time
        self.current = 0
        self.timer = 0
        self.playing = True
    def update(self, dt):
        if not self.playing:
            return
        self.timer += dt
        if self.timer >= self.frame_time:
            self.timer -= self.frame_time
            self.current = (self.current + 1) % len(self.frames)
    def draw(self, surface, pos, is_flipped=False):
        f = self.frames[self.current]
        if is_flipped:
            try:
                f = pygame.transform.flip(f, True, False)
            except Exception:
                pass
        r = f.get_rect(center=pos)
        surface.blit(f, r)
    def reset(self):
        self.current = 0
        self.timer = 0

def make_frames(color, pose='idle'):
    frames = []
    for i in range(4):
        surf = pygame.Surface((SPRITE_W, SPRITE_H), pygame.SRCALPHA)
        surf.fill((0,0,0,0))
        cx, cy = SPRITE_W//2, SPRITE_H//2
        pygame.draw.ellipse(surf, (0,0,0,30), (cx-50, cy+40, 100, 18))
        pygame.draw.circle(surf, color, (cx, cy-10), 36)
        eye_offset = -8 if i%2==0 else -6
        pygame.draw.circle(surf, BLACK, (cx-12, cy-18+eye_offset), 5)
        pygame.draw.circle(surf, BLACK, (cx+12, cy-18-eye_offset), 5)
        if pose == 'idle':
            arm_y = 10 + (i%2)*4
            pygame.draw.rect(surf, (80,50,30), (cx-36, cy+8, 10, 30))
            pygame.draw.rect(surf, (80,50,30), (cx+26, cy+arm_y, 10, 30))
        elif pose == 'attack':
            swing = -20 + i*12
            pygame.draw.rect(surf, (80,50,30), (cx-36, cy+8, 10, 30))
            pygame.draw.rect(surf, (80,50,30), (cx+16+swing, cy-10, 12, 36))
            pygame.draw.rect(surf, (180,180,200), (cx+34+swing, cy-6, 40, 6))
        elif pose == 'hurt':
            pygame.draw.circle(surf, (220,60,60), (cx, cy-10), 36, 4)
            pygame.draw.rect(surf, (80,50,30), (cx-36, cy+8, 10, 30))
            pygame.draw.rect(surf, (80,50,30), (cx+26, cy+8, 10, 30))
        frames.append(surf)
    return frames

# -------------------------
# Floating Damage Text Class
# -------------------------
class FloatingText:
    def __init__(self, x, y, value, color, duration=1000, size=22, offset_y=-40):
        self.x = x
        self.y = y + offset_y
        self.value = str(value)
        self.base_color = color if isinstance(color, tuple) else (255,255,255)
        self.color = self.base_color
        self.duration = duration
        self.timer = 0
        self.font = get_font(size)
        self.y_speed = -0.04
    def update(self, dt):
        self.timer += dt
        self.y += self.y_speed * dt
        alpha = max(0, 255 - int(255 * (self.timer / self.duration)))
        if len(self.base_color) == 4:
            self.color = self.base_color[:3] + (alpha,)
        else:
            self.color = self.base_color + (alpha,)
    def draw(self, surface):
        alpha = max(0, 255 - int(255 * (self.timer / self.duration)))
        r,g,b = self.base_color[:3]
        text_surf = self.font.render(self.value, True, (0,0,0))
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (self.x - text_surf.get_width()//2 + 2, self.y + 2))
        text_surf = self.font.render(self.value, True, (r,g,b))
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (self.x - text_surf.get_width()//2, self.y))
    def is_expired(self):
        return self.timer >= self.duration

# -------------------------
# Character
# -------------------------
class Character:
    def __init__(self, name, color, pos, image_surface=None, prefix=None):
        self.name = name
        self.max_hp = 100
        self.hp = 100
        self.color = color
        self.pos = list(pos)
        self.image = image_surface
        self.prefix = prefix
        self.anim_idle = AnimatedSprite(make_frames(color, 'idle'), frame_time=200)
        self.anim_attack = AnimatedSprite(make_frames(color, 'attack'), frame_time=120)
        self.anim_hurt = AnimatedSprite(make_frames(color, 'hurt'), frame_time=180)
        self.anim_defend = AnimatedSprite(make_frames(color, 'idle'), frame_time=200)
        self.state = 'idle'
        self.anim_timer = 0
        self.attack_duration = 500
        self.hurt_duration = 600
        self.offset_x = 0
        self.max_mp = 30
        self.mp = 0
        self.is_flipped = False
        self.special_skill = None
        self.max_rage = 100
        self.rage = 0
        self.status_effects = {'poison':0,'stun':0,'vulnerability':0,'invulnerable':0}
        self.crit_chance = 0.1
        self.dodge_chance = 0.05
        self.is_defending = False
        self.defend_damage_reduction = 0.3
        self.counter_attack_ready = False
        self.class_type = None
    def update(self, dt):
        self.anim_idle.update(dt)
        self.anim_attack.update(dt)
        self.anim_hurt.update(dt)
        self.anim_defend.update(dt)
        if self.anim_timer > 0:
            self.anim_timer = max(0, self.anim_timer - dt)
            if self.image is not None and self.state == 'attack':
                prog = 1.0 - (self.anim_timer / self.attack_duration)
                swing = int(18 * math.sin(prog * math.pi))
                self.offset_x = swing
            elif self.image is not None and self.state == 'hurt':
                prog = 1.0 - (self.anim_timer / self.hurt_duration)
                self.offset_x = int(6 * math.sin(prog * 6.28 * 4))
            else:
                self.offset_x = 0
        if self.anim_timer == 0 and self.state in ('attack','hurt','defend'):
            self.state = 'idle'
            self.offset_x = 0
    def draw(self, surface):
        x,y = self.pos
        if self.image is not None:
            img = self.image
            if self.is_flipped:
                try:
                    img = pygame.transform.flip(img, True, False)
                except Exception:
                    pass
            rect = img.get_rect(center=(x + self.offset_x, y))
            surface.blit(img, rect)
        else:
            if self.state == 'idle':
                self.anim_idle.draw(surface, self.pos, self.is_flipped)
            elif self.state == 'attack':
                self.anim_attack.draw(surface, self.pos, self.is_flipped)
            elif self.state == 'hurt':
                self.anim_hurt.draw(surface, self.pos, self.is_flipped)
            elif self.state == 'defend':
                self.anim_defend.draw(surface, self.pos, self.is_flipped)
    def play_attack(self, duration=None):
        self.state = 'attack'
        self.anim_timer = duration if duration is not None else self.attack_duration
        self.anim_attack.reset()
    def play_hurt(self, duration=None):
        self.state = 'hurt'
        self.anim_timer = duration if duration is not None else self.hurt_duration
        self.anim_hurt.reset()
    def play_defend(self, duration=None):
        self.state = 'defend'
        self.anim_timer = duration if duration is not None else 400
        self.anim_defend.reset()
    def is_alive(self):
        return self.hp > 0
    def is_stunned(self):
        return self.status_effects.get('stun',0) > 0
    def apply_turn_start_effects(self, player_ref, enemy_ref, add_floating_text_func):
        for k in ('stun','vulnerability','poison','burn','slow','atk_down','atk_up','def_up','iron_skin'):
            if self.status_effects.get(k,0) > 0:
                self.status_effects[k] -= 1
        if self.status_effects.get('invulnerable',0) > 0:
            self.status_effects['invulnerable'] = max(0, self.status_effects['invulnerable'] - 1)
        if self.status_effects.get('poison',0) > 0:
            poison_dmg = max(1, math.ceil(self.max_hp * 0.03))
            self.hp = max(0, self.hp - poison_dmg)
            add_floating_text_func(self, poison_dmg, (190,80,255), True, size=20)
            if not self.is_alive():
                return 'dead_by_dot'
        if self.status_effects.get('burn',0) > 0:
            burn_dmg = 15
            self.hp = max(0, self.hp - burn_dmg)
            add_floating_text_func(self, burn_dmg, (255,100,20), True, size=20)
            if not self.is_alive():
                return 'dead_by_dot'
        return 'continue'

# -------------------------
# UI helpers
# -------------------------
def draw_rounded_rect(surface, rect, color, radius=8, border=0, border_color=(0,0,0)):
    x,y,w,h = rect
    temp = pygame.Surface((w,h), pygame.SRCALPHA)
    pygame.draw.rect(temp, color, (0,0,w,h), border_radius=radius)
    if border > 0:
        pygame.draw.rect(temp, border_color, (0,0,w,h), border, border_radius=radius)
    surface.blit(temp, (x,y))

def draw_text_center(surface, text, font, pos, color=WHITE):
    s = font.render(text, True, color)
    surface.blit(s, (pos[0]-s.get_width()//2, pos[1]-s.get_height()//2))

def draw_hp_bar_colored(surface, x, y, w, h, current, maximum, color):
    pygame.draw.rect(surface, (30,30,34), (x,y,w,h), border_radius=6)
    if maximum <= 0:
        filled = 0
    else:
        filled = int(w * (max(0, current) / maximum))
    grad = pygame.Surface((filled, h), pygame.SRCALPHA)
    for i in range(filled):
        a = 255 - int(150 * (.0 / max(1, filled)))
        grad.fill((*color, a), (i,0,1,h))
    if filled > 0:
        surface.blit(grad, (x,y))
    pygame.draw.rect(surface, (18,20,22), (x,y,w,h), 2, border_radius=6)

# -------------------------
# Header / Pause (small)
# -------------------------
def draw_pause_button(surface, font):
    btn_w, btn_h = 80, 30
    r = pygame.Rect(WIDTH - btn_w - 10, 10, btn_w, btn_h)
    draw_rounded_rect(surface, (r.x,r.y,r.w,r.h), (40,60,80), radius=6, border=2, border_color=(10,14,18))
    txt = font.render('Pause', True, WHITE)
    surface.blit(txt, (r.x + (r.width - txt.get_width())//2, r.y + (r.height - txt.get_height())//2))
    return ('Pause', r)

# -------------------------
# Battle panel (Modernized, left/right aligned)
# -------------------------
def draw_battle_panel_lr(surface, font, bigfont, player, enemy, message, state, floor):
    panel_x = 16
    panel_y = 12
    panel_w = WIDTH - 32
    panel_h = 120
    draw_rounded_rect(surface, (panel_x, panel_y, panel_w, panel_h), (18,22,28), radius=10, border=2, border_color=(8,10,14))
    title = bigfont.render(f'FLOOR {floor} - BATTLE', True, (220,220,230))
    surface.blit(title, (WIDTH//2 - title.get_width()//2, panel_y + 8))
    avatar_size = 64
    left_x = panel_x + 18
    avatar_p_rect = pygame.Rect(left_x, panel_y + 36, avatar_size, avatar_size)
    avatar_thumb_p = None
    if player.prefix:
        avatar_thumb_p = try_load_avatar_by_prefix(player.prefix, (avatar_size, avatar_size))
    if avatar_thumb_p:
        surface.blit(avatar_thumb_p, avatar_p_rect.topleft)
    elif player.image:
        thumb = pygame.transform.scale(player.image, (avatar_size, avatar_size))
        surface.blit(thumb, avatar_p_rect.topleft)
    else:
        draw_rounded_rect(surface, (avatar_p_rect.x, avatar_p_rect.y, avatar_p_rect.w, avatar_p_rect.h), (40,160,120), radius=8)
    bars_x = avatar_p_rect.right + 12
    bars_w = 220
    draw_hp_bar_colored(surface, bars_x, panel_y + 38, bars_w, 14, player.hp, player.max_hp, (28,200,40))
    draw_hp_bar_colored(surface, bars_x, panel_y + 56, bars_w, 12, player.mp, player.max_mp, (64,150,255))
    rage_txt = get_font(13).render(f"RAGE {player.rage}/{player.max_rage}", True, (255,200,120))
    surface.blit(rage_txt, (bars_x, panel_y + 74))
    avatar_e_rect = pygame.Rect(panel_x + panel_w - 18 - avatar_size, panel_y + 36, avatar_size, avatar_size)
    avatar_thumb_e = None
    if enemy.prefix:
        avatar_thumb_e = try_load_avatar_by_prefix(enemy.prefix, (avatar_size, avatar_size))
    if avatar_thumb_e:
        t = pygame.transform.flip(avatar_thumb_e, True, False)
        surface.blit(t, avatar_e_rect.topleft)
    elif enemy.image:
        thumb = pygame.transform.scale(enemy.image, (avatar_size, avatar_size))
        thumb = pygame.transform.flip(thumb, True, False)
        surface.blit(thumb, avatar_e_rect.topleft)
    else:
        draw_rounded_rect(surface, (avatar_e_rect.x, avatar_e_rect.y, avatar_e_rect.w, avatar_e_rect.h), (200,80,80), radius=8)
    bars_x_e = avatar_e_rect.left - 12 - 220
    draw_hp_bar_colored(surface, bars_x_e, panel_y + 38, 220, 14, enemy.hp, enemy.max_hp, (28,200,40))
    draw_hp_bar_colored(surface, bars_x_e, panel_y + 56, 220, 12, enemy.mp, enemy.max_mp, (64,150,255))
    status_icon_size = 18
    sx = bars_x + bars_w + 12
    sy = panel_y + 40
    for k,v in player.status_effects.items():
        if v > 0:
            color = (200,200,200)
            if k == 'poison': color = (190,80,255)
            if k == 'stun': color = (255,255,80)
            if k == 'invulnerable': color = (100,180,255)
            draw_rounded_rect(surface, (sx, sy, status_icon_size, status_icon_size), color, radius=6)
            nt = get_font(12).render(str(v), True, BLACK)
            surface.blit(nt, (sx + (status_icon_size - nt.get_width())//2, sy + (status_icon_size - nt.get_height())//2))
            sx += status_icon_size + 6
    sx_e = bars_x_e - 12 - (status_icon_size + 6)*2
    for k,v in enemy.status_effects.items():
        if v > 0:
            color = (200,200,200)
            if k == 'poison': color = (190,80,255)
            if k == 'stun': color = (255,255,80)
            if k == 'invulnerable': color = (100,180,255)
            draw_rounded_rect(surface, (sx_e, sy, status_icon_size, status_icon_size), color, radius=6)
            nt = get_font(12).render(str(v), True, BLACK)
            surface.blit(nt, (sx_e + (status_icon_size - nt.get_width())//2, sy + (status_icon_size - nt.get_height())//2))
            sx_e += status_icon_size + 6
    msg_font = get_font(18)
    msg = msg_font.render(message, True, (200,200,210))
    surface.blit(msg, (WIDTH//2 - msg.get_width()//2, panel_y + panel_h - 28))
    return panel_y + panel_h + 8

# -------------------------
# Battle sprites
# -------------------------
def draw_battle_sprites(surface, player, enemy, status_panel_bottom_y, font, message, floor):
    ground_y = HEIGHT - 150
    actual_floor_num = (floor - 1) % 8 + 1
    bg_prefix = f"floor{actual_floor_num}"
    bg_w = WIDTH
    bg_h = ground_y - status_panel_bottom_y
    bg_surf = try_load_image_fuzzy(bg_prefix, (bg_w, bg_h))
    if bg_surf:
        surface.blit(bg_surf, (0, status_panel_bottom_y))
    else:
        temp = pygame.Surface((WIDTH, bg_h))
        temp.fill((14,18,22))
        surface.blit(temp, (0, status_panel_bottom_y))
        pygame.draw.line(surface, (40,40,50), (0, ground_y), (WIDTH, ground_y), 4)
    player.pos[0] = WIDTH // 4
    player.pos[1] = ground_y - SPRITE_H//2
    enemy.pos[0] = WIDTH * 3 // 4
    enemy.pos[1] = ground_y - SPRITE_H//2
    enemy.is_flipped = True
    shadow_w = 160
    s = pygame.Surface((shadow_w, 26), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0,0,0,120), (0,0,shadow_w,26))
    surface.blit(s, (player.pos[0]-shadow_w//2, ground_y - 18))
    surface.blit(s, (enemy.pos[0]-shadow_w//2, ground_y - 18))
    player.draw(surface)
    enemy.draw(surface)
    msg = font.render(message, True, WHITE)
    surface.blit(msg, (WIDTH//2 - msg.get_width()//2, status_panel_bottom_y + 8))

# -------------------------
# Tower enemy picker (WEAKENED)
# -------------------------
def pick_enemy_for_floor(floor):
    if floor == 1: return ('Goblin', 80, 20, 'goblin')
    if floor == 2: return ('Orc', 120, 30, 'orc')
    if floor == 3: return ('Golem', 160, 12, 'golem')
    if floor == 4: return ('Dino', 260, 100, 'dino')
    if floor == 5: return ('Giant Spider', 320, 50, 'spider')
    if floor == 6: return ('Dark Mage Lord', 420, 65, 'darkmage')
    if floor == 7: return ('Devil', 520, 80, 'devil')
    if floor == 8: return ('Dragon', 650, 100, 'dragon')
    return pick_enemy_for_floor((floor - 1) % 8 + 1)

# -------------------------
# Action button panel
# -------------------------
def draw_action_panel_modern(surface, font, player):
    panel_h = 150
    panel_y = HEIGHT - panel_h
    draw_rounded_rect(surface, (8, panel_y, WIDTH-16, panel_h-8), (18,20,24), radius=14, border=2, border_color=(6,8,10))
    top_btn_w, top_btn_h = 160, 48
    bottom_btn_h = 56
    spacing = 20
    total_w = top_btn_w*3 + spacing*2
    start_x = WIDTH//2 - total_w//2
    top_y = panel_y + 18
    bottom_y = panel_y + 18 + top_btn_h + 12
    skill1 = "Skill1"
    skill2 = "Skill2"
    if player and player.class_type:
        cname = player.class_type.lower()
        if 'warrior' in cname:
            skill1 = "Armor Break (-15 MP)"
            skill2 = "Rage (-15 MP)"
        elif 'mage' in cname:
            skill1 = "Ice Shards (-20 MP)"
            skill2 = "Vacuum (-15 MP)"
        elif 'archer' in cname:
            skill1 = "Triple Shot (-15 MP)"
            skill2 = "Stun Shot (-20 MP)"
        else:
            skill1 = "Taunt (-10 MP)"
            skill2 = "Iron Skin (15 HP)"
    actions_top = [
        ("Attack", (42,120,255)),
        (f"Heal (-15 MP)", (40,200,120)),
        ("Shield", (120,120,140)),
    ]
    ultimate_label = "ULTIMATE"
    actions_bottom = [
        (skill1, (155,89,182)),
        (ultimate_label, (200,80,200)),
        (skill2, (155,89,182))
    ]
    rects = []
    for i,(lbl,col) in enumerate(actions_top):
        r = pygame.Rect(start_x + i*(top_btn_w+spacing), top_y, top_btn_w, top_btn_h)
        draw_rounded_rect(surface, (r.x,r.y,r.w,r.h), col, radius=10)
        overlay = pygame.Surface((r.w, r.h), pygame.SRCALPHA); overlay.fill((6,8,10,140)); surface.blit(overlay, (r.x, r.y))
        pygame.draw.line(surface, (255,255,255,30), (r.x+8, r.y+6), (r.right-8, r.y+6), 2)
        txt = font.render(lbl.split('(')[0].strip(), True, WHITE)
        surface.blit(txt, (r.x + (r.w - txt.get_width())//2, r.y + (r.h - txt.get_height())//2))
        if '(' in lbl:
            cost = lbl.split('(')[1].replace(')','')
            cfont = get_font(14)
            cs = cfont.render(cost, True, (220,220,220))
            surface.blit(cs, (r.right - cs.get_width() - 8, r.bottom - cs.get_height() - 6))
        rects.append((lbl, r))
    left_w = 180; center_w = 220; right_w = 180
    left_x = WIDTH//2 - (left_w + spacing + center_w + spacing + right_w)//2
    r1 = pygame.Rect(left_x, bottom_y, left_w, bottom_btn_h)
    draw_rounded_rect(surface, (r1.x,r1.y,r1.w,r1.h), actions_bottom[0][1], radius=12)
    overlay = pygame.Surface((r1.w,r1.h), pygame.SRCALPHA); overlay.fill((6,8,10,140)); surface.blit(overlay, (r1.x,r1.y))
    t1 = font.render(actions_bottom[0][0].split('(')[0].strip(), True, WHITE)
    surface.blit(t1, (r1.x + (r1.w - t1.get_width())//2, r1.y + (r1.h - t1.get_height())//2))
    if '(' in actions_bottom[0][0]:
        cost = actions_bottom[0][0].split('(')[1].replace(')','')
        cs = get_font(14).render(cost, True, (220,220,220))
        surface.blit(cs, (r1.right - cs.get_width() - 8, r1.bottom - cs.get_height() - 6))
    rects.append((actions_bottom[0][0], r1))
    rcenter = pygame.Rect(r1.right + spacing, bottom_y - 8, center_w, bottom_btn_h + 16)
    center_surf = pygame.Surface((rcenter.w, rcenter.h), pygame.SRCALPHA)
    for i in range(6,0,-1):
        a = int(40 * (i/6))
        pygame.draw.rect(center_surf, (255,120,200,a), (0,0,rcenter.w,rcenter.h), border_radius=14)
    draw_rounded_rect(center_surf, (0,0,rcenter.w,rcenter.h), (120,30,160), radius=14)
    surface.blit(center_surf, (rcenter.x, rcenter.y))
    txt = get_font(20).render("ULTIMATE", True, WHITE)
    surface.blit(txt, (rcenter.x + (rcenter.w - txt.get_width())//2, rcenter.y + (rcenter.h - txt.get_height())//2))
    rects.append((ultimate_label, rcenter))
    r2 = pygame.Rect(rcenter.right + spacing, bottom_y, right_w, bottom_btn_h)
    draw_rounded_rect(surface, (r2.x,r2.y,r2.w,r2.h), actions_bottom[2][1], radius=12)
    overlay = pygame.Surface((r2.w,r2.h), pygame.SRCALPHA); overlay.fill((6,8,10,140)); surface.blit(overlay, (r2.x,r2.y))
    t2 = font.render(actions_bottom[2][0].split('(')[0].strip(), True, WHITE)
    surface.blit(t2, (r2.x + (r2.w - t2.get_width())//2, r2.y + (r2.h - t2.get_height())//2))
    if '(' in actions_bottom[2][0]:
        cost = actions_bottom[2][0].split('(')[1].replace(')','')
        cs = get_font(14).render(cost, True, (220,220,220))
        surface.blit(cs, (r2.right - cs.get_width() - 8, r2.bottom - cs.get_height() - 6))
    rects.append((actions_bottom[2][0], r2))
    charge_w = int((rcenter.w - 12) * (player.rage / max(1, player.max_rage)))
    pygame.draw.rect(surface, (10,10,12), (rcenter.x+6, rcenter.bottom - 12, rcenter.w-12, 8), border_radius=8)
    if charge_w > 0:
        pygame.draw.rect(surface, (255,140,30), (rcenter.x+6, rcenter.bottom - 12, charge_w, 8), border_radius=8)
    return rects

# -------------------------
# Main loop
# -------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    pygame.display.set_caption("Modern Combat UI - Balanced (v3)")
    font = get_font(20)
    bigfont = get_font(34)
    damage_font = get_font(28)
    generic_player_img = try_load_image_fuzzy("player", (SPRITE_W, SPRITE_H))
    generic_enemy_img = try_load_image_fuzzy("enemy", (SPRITE_W, SPRITE_H))
    MAP_IMG = try_load_image_fuzzy("map", (WIDTH, HEIGHT))
    map_entry_rect = pygame.Rect(WIDTH//2 - 80, HEIGHT//2 + 100, 160, 60)
    start_btn = pygame.Rect(WIDTH//2-80, HEIGHT//2-40, 160, 48)
    quit_btn = pygame.Rect(WIDTH//2-80, HEIGHT//2+20, 160, 48)
    guide_btn = pygame.Rect(WIDTH//2-80, HEIGHT//2+80, 160, 48)
    name_box = pygame.Rect(WIDTH//2-200, HEIGHT//2-20, 400, 40)
    pause_btn_rect = pygame.Rect(WIDTH - 80 - 10, 10, 80, 30)
    modal_pause_continue = pygame.Rect(WIDTH//2 - 180, HEIGHT//2 + 40, 160, 48)
    modal_pause_quit = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 + 40, 160, 48)
    menu_state = 'menu'
    input_name = ""
    name_active = False
    classes = ['Warrior','Mage','Tank','Archer']
    class_rects = []
    btn_w = 160
    spacing = 20
    total_w = len(classes) * btn_w + (len(classes) - 1) * spacing
    start_x = WIDTH//2 - total_w//2
    for i, c in enumerate(classes):
        r = pygame.Rect(start_x + i * (btn_w + spacing), HEIGHT//2 + 40, btn_w, 48)
        class_rects.append((c, r))
    action_btn_rects = []
    floating_texts = []
    player = None
    enemy = None
    selected_class = None
    reward_options = [
        ('Max HP +15', (28,200,40)),
        ('Max MP +10', (64,150,255)),
        ('+5% Crit Chance', (243,156,18))
    ]
    reward_rects = []
    for i, (text, color) in enumerate(reward_options):
        r = pygame.Rect(WIDTH//2 - 240 + i*180, HEIGHT//2 + 40, 160, 48)
        reward_rects.append((text, r, color))
    state = 'player_turn'
    player_defending = False
    anim_duration = 600
    floor = 1
    message = "Use mouse or keys to play."
    modal_continue = pygame.Rect(WIDTH//2 - 180, HEIGHT//2 + 40, 160, 48)
    modal_exit = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 + 40, 160, 48)
    modal_retry = pygame.Rect(WIDTH//2 - 180, HEIGHT//2 + 40, 160, 48)

    # BIẾN TOÀN CỤC CHO PENDING ACTIONS
    pending_action = None
    pending_enemy_action = None

    def add_floating_text(target_char, value, color, is_damage, size=22):
        if target_char.pos[0] <= WIDTH//2:
            x, y = target_char.pos[0] + 40, target_char.pos[1] - SPRITE_H//2
        else:
            x, y = target_char.pos[0] - 40, target_char.pos[1] - SPRITE_H//2
        text_value = str(value) if is_damage else "+" + str(value)
        floating_texts.append(FloatingText(x, y, text_value, color, size=size))

    running = True
    while running:
        dt = clock.tick(FPS)
        if menu_state not in ('paused_menu','guide'):
            newft = []
            for ft in floating_texts:
                ft.update(dt)
                if not ft.is_expired():
                    newft.append(ft)
            floating_texts = newft

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if menu_state == 'menu':
                        running = False
                    elif menu_state == 'playing':
                        menu_state = 'paused_menu'
                        message = "Game Paused."
                    elif menu_state == 'paused_menu':
                        menu_state = 'playing'
                        message = "Resumed."
                    elif menu_state == 'guide':
                        menu_state = 'menu'
                    elif menu_state == 'world_map':
                        menu_state = 'choose_class'
                if menu_state == 'enter_name' and name_active:
                    if event.key == pygame.K_BACKSPACE:
                        input_name = input_name[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if input_name.strip() == "":
                            input_name = "Player"
                        menu_state = 'choose_class'
                        name_active = False
                    else:
                        ch = event.unicode
                        if ch and len(input_name) < 20:
                            input_name += ch
                elif menu_state == 'playing' and player and enemy:
                    if state == 'player_turn' and not player.is_stunned():
                        action_label = None
                        if event.key == pygame.K_a:
                            action_label = 'Attack'
                        elif event.key == pygame.K_d:
                            action_label = 'Shield'
                        elif event.key == pygame.K_h:
                            action_label = 'Heal (-15 MP)'
                        elif event.key == pygame.K_u:
                            action_label = 'ULTIMATE'
                        if action_label == 'Attack':
                            dmg = random.randint(15,28)  # BUFFED
                            player.play_attack(duration=anim_duration)
                            state = 'player_anim'
                            pending_action = ('attack', dmg)
                            message = f"You attack! Deal {dmg} damage..."
                        elif action_label == 'Shield':
                            player_defending = True
                            mp_gain = 5
                            player.mp = min(player.max_mp, player.mp + mp_gain)
                            add_floating_text(player, mp_gain, (64,150,255), False)
                            message = f"You brace your shield and recovered {mp_gain} MP."
                            state = 'enemy_turn'
                        elif action_label == 'Heal (-15 MP)':
                            cost = 15
                            if player.mp >= cost:
                                player.mp -= cost
                                heal = random.randint(20,30)
                                player.hp = min(player.max_hp, player.hp + heal)
                                add_floating_text(player, heal, (46,204,113), False)
                                message = f"You healed {heal} HP (-{cost} MP)."
                                state = 'enemy_turn'
                            else:
                                message = "Not enough MP for Heal."
                        elif action_label == 'ULTIMATE':
                            if player.rage >= player.max_rage:
                                cname = (player.class_type or "").lower()
                                if 'warrior' in cname:
                                    cost = 30
                                    if player.mp >= cost:
                                        player.mp -= cost
                                    dmg = random.randint(200,250)
                                    player.rage = 0
                                    enemy.hp = max(0, enemy.hp - dmg)
                                    enemy.play_hurt(duration=500)
                                    add_floating_text(enemy, dmg, (255,40,40), True, size=36)
                                    if enemy.hp == 0:
                                        heal_amt = int(player.max_hp * 0.5)
                                        player.hp = min(player.max_hp, player.hp + heal_amt)
                                        add_floating_text(player, heal_amt, (46,204,113), False, size=26)
                                        message = f"Decapitate! Killed target. Recovered {heal_amt} HP."
                                    else:
                                        message = f"Decapitate! Dealt {dmg} damage."
                                elif 'mage' in cname:
                                    cost = 35
                                    if player.mp >= cost:
                                        player.mp -= cost
                                    dmg = random.randint(120,150)
                                    player.rage = 0
                                    enemy.hp = max(0, enemy.hp - dmg)
                                    enemy.status_effects['burn'] = 3
                                    add_floating_text(enemy, dmg, (255,90,0), True, size=34)
                                    add_floating_text(enemy, "BURN", (255,120,60), False, size=18)
                                    message = f"Inferno! {dmg} damage and Burn."
                                elif 'tank' in cname:
                                    cost = 30
                                    if player.mp >= cost:
                                        player.mp -= cost
                                    player.rage = 0
                                    player.status_effects['invulnerable'] = 1
                                    player.status_effects['reflect_pct'] = 0.5
                                    add_floating_text(player, "ABS GUARD", (100,180,255), False, size=24)
                                    message = "Absolute Guard! Invulnerable and reflect 50%."
                                elif 'archer' in cname:
                                    cost = 40
                                    if player.mp >= cost:
                                        player.mp -= cost
                                    dmg = random.randint(150,200)
                                    player.rage = 0
                                    enemy.hp = max(0, enemy.hp - dmg)
                                    enemy.play_hurt(duration=500)
                                    enemy.status_effects['slow'] = max(enemy.status_effects.get('slow',0), 2)
                                    add_floating_text(enemy, dmg, (255,200,80), True, size=34)
                                    add_floating_text(enemy, "SLOW", (200,200,255), False, size=18)
                                    message = f"Rain of Arrows! {dmg} damage and Slow for 2 turns."
                                else:
                                    message = "Ultimate used!"
                                state = 'enemy_turn'
                            else:
                                message = "Ultimate not ready."
                    elif event.key == pygame.K_r and menu_state in ('run_complete','defeat'):
                        floor = 1
                        if player:
                            player.hp = player.max_hp
                            player.mp = player.max_mp
                            player.status_effects = {'poison':0,'stun':0,'vulnerability':0,'invulnerable':0}
                            player.rage = 0
                        message = f"New run. Current Floor is {floor}. Click entry point."
                        menu_state = 'world_map'
                        floating_texts = []
                        state = 'player_turn'
                        player_defending = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if menu_state == 'playing' and pause_btn_rect.collidepoint(mx,my):
                    menu_state = 'paused_menu'
                    message = "Game Paused."
                    continue
                if menu_state == 'menu':
                    if start_btn.collidepoint(mx,my):
                        menu_state = 'enter_name'
                        input_name = ""
                        name_active = True
                        message = "Enter name then choose class."
                    elif quit_btn.collidepoint(mx,my):
                        running = False
                    elif guide_btn.collidepoint(mx,my):
                        menu_state = 'guide'
                        message = "Game Guide: ESC to return."
                elif menu_state == 'enter_name':
                    name_active = name_box.collidepoint(mx,my)
                elif menu_state == 'choose_class':
                    for c,r in class_rects:
                        if r.collidepoint(mx,my):
                            selected_class = c
                            if selected_class == 'Warrior':
                                p_hp, p_mp = 150, 30
                            elif selected_class == 'Mage':
                                p_hp, p_mp = 90, 100
                            elif selected_class == 'Archer':
                                p_hp, p_mp = 110, 50
                            else:
                                p_hp, p_mp = 180, 20
                            p_prefix = selected_class.lower()
                            if p_prefix == 'tank':
                                p_prefix = 'tanker'
                            player_img = try_load_image_fuzzy(p_prefix, (SPRITE_W, SPRITE_H)) or generic_player_img
                            player = Character(input_name or 'Player', GREEN, (0,0), image_surface=player_img, prefix=p_prefix)
                            player.max_hp = player.hp = p_hp
                            player.max_mp = player.mp = p_mp
                            player.class_type = selected_class
                            if selected_class == 'Warrior':
                                player.crit_chance = 0.15
                            elif selected_class == 'Tank':
                                player.dodge_chance = 0.1
                            floor = 1
                            state = 'player_turn'
                            player_defending = False
                            message = f"You are at Floor {floor} entrance. Click entry point."
                            menu_state = 'world_map'
                            floating_texts = []
                elif menu_state == 'world_map':
                    if map_entry_rect.collidepoint(mx, my) and player:
                        e_name, e_hp, e_mp, e_prefix = pick_enemy_for_floor(floor)
                        enemy_img = try_load_image_fuzzy(e_prefix, (SPRITE_W, SPRITE_H)) or generic_enemy_img
                        enemy = Character(e_name, (200,60,80), (0,0), image_surface=enemy_img, prefix=e_prefix)
                        enemy.max_hp = enemy.hp = int(e_hp * (1 + (floor-1)*0.12))  # NERFED SCALING
                        enemy.max_mp = enemy.mp = e_mp
                        state = 'player_turn'
                        player_defending = False
                        message = f"Floor {floor}: {enemy.name}! Choose action."
                        menu_state = 'playing'
                        floating_texts = []
                    else:
                        message = f"Click Entry Point to start Floor {floor}."
                elif menu_state == 'playing':
                    for label, rect in action_btn_rects:
                        if rect.collidepoint(mx,my) and state == 'player_turn' and not player.is_stunned():
                            if label.startswith('Attack'):
                                dmg = random.randint(15,28)  # BUFFED
                                player.play_attack(duration=anim_duration)
                                state = 'player_anim'
                                pending_action = ('attack', dmg)
                                message = f"You attack! Deal {dmg} damage..."
                            elif label.startswith('Heal'):
                                cost = 15
                                if player.mp >= cost:
                                    player.mp -= cost
                                    heal = random.randint(20,30)
                                    player.hp = min(player.max_hp, player.hp + heal)
                                    add_floating_text(player, heal, (46,204,113), False)
                                    message = f"You healed {heal} HP (-{cost} MP)."
                                    state = 'enemy_turn'
                                else:
                                    message = "Not enough MP for Heal."
                            elif label.startswith('Shield'):
                                player_defending = True
                                mp_gain = 5
                                player.mp = min(player.max_mp, player.mp + mp_gain)
                                add_floating_text(player, mp_gain, (64,150,255), False)
                                message = f"You brace your shield and recovered {mp_gain} MP."
                                state = 'enemy_turn'
                            elif label.startswith('Armor Break') or label.startswith('Ice Shards') or label.startswith('Taunt') or label.startswith('Vacuum') or label.startswith('Rage') or label.startswith('Iron Skin') or label.startswith('Triple Shot') or label.startswith('Stun Shot'):
                                cname = (player.class_type or "").lower()
                                if "warrior" in cname and label.startswith("Armor Break"):
                                    cost = 15
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        dmg = random.randint(80,105)  # BUFFED
                                        player.play_attack(duration=anim_duration)
                                        state = 'player_anim'
                                        pending_action = ('attack', dmg)
                                        enemy.status_effects['vulnerability'] = max(enemy.status_effects.get('vulnerability',0), 2)
                                        message = f"Armor Break! {dmg} damage and DEF down for 2 turns."
                                    else:
                                        message = "Not enough MP for Armor Break."
                                elif "warrior" in cname and label.startswith("Rage"):
                                    cost = 15
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        rage_gain = 40
                                        player.rage = min(player.max_rage, player.rage + rage_gain)
                                        message = f"Rage! Gained {rage_gain} Rage (+{player.rage}/{player.max_rage}). Enemy turn."
                                        state = 'enemy_turn'
                                    else:
                                        message = "Not enough MP for Rage."
                                elif "mage" in cname and label.startswith("Ice Shards"):
                                    cost = 20
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        dmg = random.randint(48,72)  # BUFFED
                                        player.play_attack(duration=anim_duration)
                                        state = 'player_anim'
                                        pending_action = ('attack', dmg)
                                        enemy.status_effects['slow'] = max(enemy.status_effects.get('slow',0), 1)
                                        message = f"Ice Shards! {dmg} damage and Slow."
                                    else:
                                        message = "Not enough MP for Ice Shards."
                                elif "tank" in cname and label.startswith("Taunt"):
                                    cost = 10
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        player.status_effects['def_up'] = player.status_effects.get('def_up',0) + 2
                                        enemy.status_effects['taunted_by'] = 2
                                        add_floating_text(player, "TAUNT", (100,180,255), False, size=18)
                                        message = "Taunt: enemies forced to target you and +DEF."
                                        state = 'enemy_turn'
                                    else:
                                        message = "Not enough MP for Taunt."
                                elif "mage" in cname and label.startswith("Vacuum"):
                                    cost = 15
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        dmg = random.randint(60,85)  # BUFFED
                                        player.play_attack(duration=anim_duration)
                                        state = 'player_anim'
                                        pending_action = ('attack', dmg)
                                        enemy.status_effects['atk_down'] = max(enemy.status_effects.get('atk_down',0), 2)
                                        message = f"Vacuum! {dmg} damage and ATK down."
                                    else:
                                        message = "Not enough MP for Vacuum."
                                elif "tank" in cname and label.startswith("Iron Skin"):
                                    hp_cost = 15
                                    if player.hp > hp_cost:
                                        player.hp = max(0, player.hp - hp_cost)
                                        player.status_effects['iron_skin'] = 1
                                        player.status_effects['atk_up'] = max(player.status_effects.get('atk_up',0), 1)
                                        add_floating_text(player, "IRON SKIN", (180,180,255), False, size=18)
                                        message = f"Iron Skin used! Block next hit and +ATK for 1 turn."
                                        state = 'enemy_turn'
                                    else:
                                        message = "Not enough HP for Iron Skin."
                                elif "archer" in cname and label.startswith("Triple Shot"):
                                    cost = 15
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        dmg = random.randint(18,30) * 3  # BUFFED
                                        player.play_attack(duration=anim_duration)
                                        state = 'player_anim'
                                        pending_action = ('attack', dmg)
                                        message = f"Triple Shot! {dmg} total damage (3 hits)."
                                    else:
                                        message = "Not enough MP for Triple Shot."
                                elif "archer" in cname and label.startswith("Stun Shot"):
                                    cost = 20
                                    if player.mp >= cost:
                                        player.mp -= cost
                                        dmg = random.randint(24,36)  # BUFFED
                                        player.play_attack(duration=anim_duration)
                                        state = 'player_anim'
                                        pending_action = ('attack', dmg)
                                        enemy.status_effects['stun'] = max(enemy.status_effects.get('stun',0), 1)
                                        message = f"Stun Shot! {dmg} damage and 1 turn Stun."
                                    else:
                                        message = "Not enough MP for Stun Shot."
                            elif label == 'ULTIMATE':
                                if player.rage >= player.max_rage:
                                    cname = (player.class_type or "").lower()
                                    cost = 30
                                    if 'mage' in cname: cost = 35
                                    elif 'archer' in cname: cost = 40
                                    elif 'tank' in cname: cost = 30
                                    if player.mp >= cost:
                                        player.mp -= cost
                                    player.rage = 0
                                    if 'warrior' in cname:
                                        dmg = random.randint(200,250)
                                        enemy.hp = max(0, enemy.hp - dmg)
                                        enemy.play_hurt(duration=500)
                                        add_floating_text(enemy, dmg, (255,40,40), True, size=36)
                                        if enemy.hp == 0:
                                            heal_amt = int(player.max_hp * 0.5)
                                            player.hp = min(player.max_hp, player.hp + heal_amt)
                                            add_floating_text(player, heal_amt, (46,204,113), False, size=26)
                                            message = f"Decapitate! Killed target. Recovered {heal_amt} HP."
                                        else:
                                            message = f"Decapitate! Dealt {dmg} damage."
                                    elif 'mage' in cname:
                                        dmg = random.randint(120,150)
                                        enemy.hp = max(0, enemy.hp - dmg)
                                        enemy.status_effects['burn'] = 3
                                        add_floating_text(enemy, dmg, (255,90,0), True, size=34)
                                        add_floating_text(enemy, "BURN", (255,120,60), False, size=18)
                                        message = f"Inferno! {dmg} damage and Burn."
                                    elif 'tank' in cname:
                                        player.status_effects['invulnerable'] = 1
                                        player.status_effects['reflect_pct'] = 0.5
                                        add_floating_text(player, "ABS GUARD", (100,180,255), False, size=24)
                                        message = "Absolute Guard! Invulnerable and reflect 50%."
                                    elif 'archer' in cname:
                                        dmg = random.randint(150,200)
                                        enemy.hp = max(0, enemy.hp - dmg)
                                        enemy.play_hurt(duration=500)
                                        enemy.status_effects['slow'] = max(enemy.status_effects.get('slow',0), 2)
                                        add_floating_text(enemy, dmg, (255,200,80), True, size=34)
                                        add_floating_text(enemy, "SLOW", (200,200,255), False, size=18)
                                        message = f"Rain of Arrows! {dmg} damage and Slow for 2 turns."
                                    state = 'enemy_turn'
                                else:
                                    message = "Ultimate not ready."
                elif menu_state == 'paused_menu':
                    if modal_pause_continue.collidepoint(mx,my):
                        menu_state = 'playing'
                        message = "Resumed."
                    elif modal_pause_quit.collidepoint(mx,my):
                        menu_state = 'menu'
                        floating_texts = []
                elif menu_state == 'floor_cleared':
                    reward_chosen = False
                    for text, r, color in reward_rects:
                        if r.collidepoint(mx,my):
                            if text == 'Max HP +15':
                                player.max_hp += 15
                                player.hp += 15
                            elif text == 'Max MP +10':
                                player.max_mp += 10
                                player.mp += 10
                            elif text == '+5% Crit Chance':
                                player.crit_chance = min(0.5, player.crit_chance + 0.05)
                            reward_chosen = True
                            break
                    if reward_chosen:
                        if floor < 8:
                            floor += 1
                            e_name, e_hp, e_mp, e_prefix = pick_enemy_for_floor(floor)
                            enemy_img = try_load_image_fuzzy(e_prefix, (SPRITE_W, SPRITE_H)) or generic_enemy_img
                            enemy = Character(e_name, (200,60,80), (0,0), image_surface=enemy_img, prefix=e_prefix)
                            enemy.max_hp = enemy.hp = int(e_hp * (1 + (floor-1)*0.12))  # NERFED
                            enemy.max_mp = enemy.mp = e_mp
                            message = f"You are now at Floor {floor} entrance. Click entry point."
                            menu_state = 'world_map'
                            state = 'player_turn'
                            player_defending = False
                            floating_texts = []
                        else:
                            menu_state = 'run_complete'
                elif menu_state == 'run_complete':
                    if modal_continue.collidepoint(mx,my):
                        if player:
                            player.hp = player.max_hp
                            player.mp = player.max_mp
                            player.status_effects = {'poison':0,'stun':0,'vulnerability':0,'invulnerable':0}
                            player.rage = 0
                        floor = 1
                        menu_state = 'world_map'
                        message = f"Floor {floor} entrance. Click entry point."
                        floating_texts = []
                    elif modal_exit.collidepoint(mx,my):
                        menu_state = 'menu'
                        floating_texts = []
                elif menu_state == 'defeat':
                    if modal_retry.collidepoint(mx,my):
                        if player:
                            player.hp = player.max_hp
                            player.mp = player.max_mp
                            player.status_effects = {'poison':0,'stun':0,'vulnerability':0,'invulnerable':0}
                            player.rage = 0
                        floor = 1
                        menu_state = 'world_map'
                        state = 'player_turn'
                        player_defending = False
                        floating_texts = []

        # Gameplay updates
        if menu_state == 'playing' and player and enemy:
            player.update(dt)
            enemy.update(dt)
            if state == 'player_turn':
                player_defending = False
                result = enemy.apply_turn_start_effects(player, enemy, add_floating_text)
                if result == 'dead_by_dot':
                    menu_state = 'floor_cleared'
                    message = f"Enemy was defeated by DOT! You cleared floor {floor}!"
                    continue
                if enemy.is_stunned():
                    message = f"{enemy.name} is stunned! Enemy skips turn."
            if state == 'player_anim':
                if player.anim_timer == 0:
                    if pending_action is None:
                        state = 'enemy_turn'
                        continue
                    action, dmg = pending_action
                    pending_action = None
                    if action == 'attack':
                        is_crit = random.random() < player.crit_chance
                        is_miss = random.random() < enemy.dodge_chance
                        if is_miss:
                            final_dmg = 0
                            add_floating_text(enemy, "DODGED", (255,255,255), True, size=30)
                            message = f"You missed! Enemy turn."
                        else:
                            final_dmg = dmg
                            if is_crit:
                                final_dmg = int(dmg * 1.5)
                                add_floating_text(enemy, "CRIT! " + str(final_dmg), (255,180,0), True, size=36)
                            else:
                                add_floating_text(enemy, final_dmg, (255,20,20), True)
                            enemy.hp = max(0, enemy.hp - final_dmg)
                            enemy.play_hurt(duration=500)
                            message = f"Dealt {final_dmg} damage. Enemy turn."
                            gain = max(1, int(final_dmg * 0.10))
                            player.rage = min(player.max_rage, player.rage + gain)
                        if enemy.hp <= 0:
                            if floor >= 8:
                                menu_state = 'run_complete'
                                message = "You cleared the tower! Continue or Exit."
                            else:
                                menu_state = 'floor_cleared'
                                message = f"You cleared floor {floor}! Choose reward!"
                            continue
                    state = 'enemy_turn'
            elif state == 'enemy_turn':
                if not enemy.is_alive():
                    if floor >= 8:
                        menu_state = 'run_complete'
                        message = "You cleared the tower! Continue or Exit."
                    else:
                        menu_state = 'floor_cleared'
                        message = f"You cleared floor {floor}! Choose reward!"
                    continue
                result = player.apply_turn_start_effects(player, enemy, add_floating_text)
                if result == 'dead_by_dot':
                    menu_state = 'defeat'
                    message = "You were defeated by DOT. Retry or Exit?"
                    floating_texts = []
                    continue
                if enemy.is_stunned():
                    message = f"{enemy.name} is stunned! Enemy skips turn."
                    state = 'player_turn'
                    continue
                # WEAKENED ENEMY AI
                if enemy.prefix == 'dragon' and enemy.mp >= 30 and random.random() < 0.5:
                    enemy.mp -= 30
                    dmg = random.randint(28,42)
                    enemy.play_attack(duration=anim_duration)
                    state = 'enemy_anim'
                    pending_enemy_action = ('attack', dmg, 'poison')
                    message = "Dragon breathes POISON fire!"
                    continue
                elif enemy.prefix == 'golem' and enemy.mp >= 14 and random.random() < 0.4:
                    enemy.mp -= 14
                    dmg = random.randint(17,24)
                    status = 'stun' if random.random() < 0.4 else None
                    enemy.play_attack(duration=anim_duration)
                    state = 'enemy_anim'
                    pending_enemy_action = ('attack', dmg, status)
                    message = "Golem uses Rock Smash!"
                    continue
                elif enemy.prefix == 'orc' and enemy.mp >= 10 and random.random() < 0.3:
                    enemy.mp -= 10
                    dmg = random.randint(10,17)
                    enemy.play_attack(duration=anim_duration)
                    state = 'enemy_anim'
                    pending_enemy_action = ('attack', dmg, 'vulnerability')
                    message = "Orc throws a Debilitating Axe!"
                    continue
                dmg_mult = 1.0
                if player.status_effects.get('vulnerability',0) > 0:
                    dmg_mult = 1.2
                choice = random.random()
                if choice < 0.7:
                    dmg = int(random.randint(6,13) * dmg_mult)
                    enemy.play_attack(duration=anim_duration)
                    state = 'enemy_anim'
                    pending_enemy_action = ('attack', dmg)
                    message = "Enemy attacks..."
                else:
                    heal = random.randint(6,10)
                    enemy.hp = min(enemy.max_hp, enemy.hp + heal)
                    add_floating_text(enemy, heal, (46,204,113), False)
                    message = f"Enemy healed {heal} HP."
                    state = 'player_turn'
            elif state == 'enemy_anim':
                if enemy.anim_timer == 0:
                    if pending_enemy_action is None:
                        state = 'player_turn'
                        continue
                    action = pending_enemy_action[0]
                    dmg = pending_enemy_action[1]
                    status_effect = pending_enemy_action[2] if len(pending_enemy_action) > 2 else None
                    pending_enemy_action = None
                    if action == 'attack':
                        final = dmg
                        is_dodge = random.random() < player.dodge_chance
                        if is_dodge:
                            final = 0
                            add_floating_text(player, "DODGE", (255,255,255), True, size=30)
                            message = f"{enemy.name} missed!"
                        else:
                            if player_defending == True:
                                final = int(dmg * player.defend_damage_reduction)
                            elif player.status_effects.get('invulnerable',0) > 0:
                                reflect = player.status_effects.get('reflect_pct', 0)
                                if reflect > 0:
                                    refd = int(final * reflect)
                                    enemy.hp = max(0, enemy.hp - refd)
                                    add_floating_text(enemy, refd, (255,160,80), True)
                                final = 0
                                message = "Your shield reflected damage!"
                            if player.status_effects.get('iron_skin',0) > 0:
                                player.status_effects['iron_skin'] = max(0, player.status_effects.get('iron_skin',0)-1)
                                final = 0
                                add_floating_text(player, "BLOCKED", (180,180,255), False, size=18)
                            if final > 0:
                                player.play_hurt(duration=480)
                                player.hp = max(0, player.hp - final)
                                add_floating_text(player, final, (255,80,80), True)
                                mp_recover = 5
                                player.mp = min(player.max_mp, player.mp + mp_recover)
                                add_floating_text(player, mp_recover, (64,150,255), False)
                                if player.hp <= 0:
                                    menu_state = 'defeat'
                                    message = "You were defeated! Retry or Exit?"
                                    floating_texts = []
                                    state = 'player_turn'
                                    continue
                            if status_effect:
                                if status_effect == 'poison':
                                    player.status_effects['poison'] = max(player.status_effects.get('poison',0), 2)
                                elif status_effect == 'stun':
                                    player.status_effects['stun'] = max(player.status_effects.get('stun',0), 1)
                                elif status_effect == 'vulnerability':
                                    player.status_effects['vulnerability'] = max(player.status_effects.get('vulnerability',0), 2)
                            message = f"{enemy.name} dealt {final} damage."
                        player_defending = False
                    state = 'player_turn'

        # Draw
        screen.fill((8,10,12))
        if menu_state in ('playing', 'paused_menu'):
            status_bottom = draw_battle_panel_lr(screen, font, bigfont, player if player else Character("P",GREEN,(0,0)), enemy if enemy else Character("E",(200,60,80),(0,0)), message, state, floor) if player and enemy else 140
            if player and enemy:
                draw_battle_sprites(screen, player, enemy, status_bottom, font, message, floor)
            draw_pause_button(screen, font)
            if menu_state == 'playing' and player:
                action_btn_rects = draw_action_panel_modern(screen, font, player)
            if menu_state == 'paused_menu':
                msg = bigfont.render("PAUSED", True, WHITE)
                screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 80))
                draw_rounded_rect(screen, (modal_pause_continue.x-4, modal_pause_continue.y-4, modal_pause_continue.w+8, modal_pause_continue.h+8), (28,30,34), radius=8, border=2, border_color=(6,6,8))
                draw_text_center(screen, "Continue", font, (modal_pause_continue.centerx, modal_pause_continue.centery), color=WHITE)
                draw_rounded_rect(screen, (modal_pause_quit.x-4, modal_pause_quit.y-4, modal_pause_quit.w+8, modal_pause_quit.h+8), (28,30,34), radius=8, border=2, border_color=(6,6,8))
                draw_text_center(screen, "Exit", font, (modal_pause_quit.centerx, modal_pause_quit.centery), color=WHITE)
        elif menu_state == 'world_map':
            if MAP_IMG:
                screen.blit(MAP_IMG, (0, 0))
            else:
                screen.fill((40, 50, 60))
                draw_text_center(screen, "World Map Placeholder (map.png)", bigfont, (WIDTH//2, HEIGHT//2 - 100))
            draw_rounded_rect(screen, (map_entry_rect.x, map_entry_rect.y, map_entry_rect.w, map_entry_rect.h), GREEN, radius=10, border=3, border_color=(20, 80, 40))
            draw_text_center(screen, f"Floor {floor} Entry", font, (map_entry_rect.centerx, map_entry_rect.centery), color=BLACK)
            if player:
                draw_rounded_rect(screen, (10, 10, 240, 60), (18,22,28), radius=8, border=2, border_color=(8,10,14))
                draw_text_center(screen, f"{player.name} ({player.class_type})", font, (130, 25), WHITE)
                draw_hp_bar_colored(screen, 15, 40, 230, 10, player.hp, player.max_hp, (28,200,40))
                draw_hp_bar_colored(screen, 15, 53, 230, 8, player.mp, player.max_mp, (64,150,255))
            draw_rounded_rect(screen, (WIDTH//2 - 200, HEIGHT - 60, 400, 40), (18,22,28), radius=8, border=2, border_color=(8,10,14))
            draw_text_center(screen, message, font, (WIDTH//2, HEIGHT - 40), WHITE)
        if menu_state == 'menu':
            title = bigfont.render("TOWER RUN", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
            draw_rounded_rect(screen, (start_btn.x-4, start_btn.y-4, start_btn.w+8, start_btn.h+8), (30,30,34), radius=8, border=2, border_color=(6,6,8))
            draw_text_center(screen, "Start", font, (start_btn.centerx, start_btn.centery), color=WHITE)
            draw_rounded_rect(screen, (quit_btn.x-4, quit_btn.y-4, quit_btn.w+8, quit_btn.h+8), (30,30,34), radius=8, border=2, border_color=(6,6,8))
            draw_text_center(screen, "Quit", font, (quit_btn.centerx, quit_btn.centery), color=WHITE)
            draw_rounded_rect(screen, (guide_btn.x-4, guide_btn.y-4, guide_btn.w+8, guide_btn.h+8), (30,30,34), radius=8, border=2, border_color=(6,6,8))
            draw_text_center(screen, "Guide", font, (guide_btn.centerx, guide_btn.centery), color=WHITE)
        elif menu_state == 'enter_name':
            prompt = font.render("Enter your name:", True, WHITE)
            screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 - 80))
            draw_rounded_rect(screen, (name_box.x-4, name_box.y-4, name_box.w+8, name_box.h+8), (26,28,32), radius=6, border=2, border_color=(6,6,8))
            name_s = font.render(input_name or "Player", True, WHITE)
            screen.blit(name_s, (name_box.x + 8, name_box.y + 8))
        elif menu_state == 'choose_class':
            prompt = font.render("Choose class:", True, WHITE)
            screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 - 80))
            for c,r in class_rects:
                draw_rounded_rect(screen, (r.x-4, r.y-4, r.w+8, r.h+8), (26,28,32), radius=8, border=2, border_color=(6,6,8))
                draw_text_center(screen, c, font, (r.centerx, r.centery), color=WHITE)
        elif menu_state == 'floor_cleared':
            msg = bigfont.render(f"Floor {floor} Cleared!", True, WHITE)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 80))
            sub = font.render("Choose your reward:", True, WHITE)
            screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 - 40))
            for text, r, color in reward_rects:
                draw_rounded_rect(screen, (r.x-4, r.y-4, r.w+8, r.h+8), (28,30,34), radius=8, border=2, border_color=(6,6,8))
                draw_text_center(screen, text, font, (r.centerx, r.centery), color=WHITE)
        elif menu_state == 'run_complete':
            msg = bigfont.render("You cleared the Tower!", True, WHITE)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 80))
            draw_rounded_rect(screen, (modal_continue.x-4, modal_continue.y-4, modal_continue.w+8, modal_continue.h+8), (28,30,34), radius=8, border=2, border_color=(6,6,8))
            draw_text_center(screen, "Restart", font, (modal_continue.centerx, modal_continue.centery), color=WHITE)
            draw_rounded_rect(screen, (modal_exit.x-4, modal_exit.y-4, modal_exit.w+8, modal_exit.h+8), (28,30,34), radius=8, border=2, border_color=(6,6,8))
            draw_text_center(screen, "Exit", font, (modal_exit.centerx, modal_exit.centery), color=WHITE)
        elif menu_state == 'defeat':
            msg = bigfont.render("You were defeated", True, WHITE)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 80))
            draw_rounded_rect(screen, (modal_retry.x-4, modal_retry.y-4, modal_retry.w+8, modal_retry.h+8), (28,30,34), radius=8, border=2, border_color=(6,6,8))
            draw_text_center(screen, "Retry", font, (modal_retry.centerx, modal_retry.centery), color=WHITE)
        elif menu_state == 'guide':
            lines = [
                "Guide:",
                "A / Click Attack: Basic attack",
                "Heal: costs MP",
                "Shield: defend and recover MP (reduces 70% dmg)",
                "Bottom row: Skill1, ULTIMATE, Skill2",
                "ESC to return"
            ]
            for i,l in enumerate(lines):
                s = font.render(l, True, WHITE)
                screen.blit(s, (80, 120 + i*28))
        for ft in floating_texts:
            ft.draw(screen)
        pygame.display.flip()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()