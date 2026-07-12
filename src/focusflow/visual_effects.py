import pygame
import pygame.gfxdraw
import math
import random
from abc import ABC, abstractmethod

# --- Base Effect Class ---
class BaseVisualEffect(ABC):
    def __init__(self, width, height, bg_color):
        self.width = width
        self.height = height
        self.bg_color = bg_color
        
    @abstractmethod
    def update(self):
        """Update particle states"""
        pass
        
    @abstractmethod
    def draw(self, screen, time_text):
        """Draw everything to surface"""
        pass

    @abstractmethod
    def draw_minimal(self, screen, time_text):
        """Draw only background and text (no animation)"""
        pass
        
    def set_bg_color(self, color_hex):
        """Update background color dynamically"""
        self.bg_color = color_hex # Expect hex string "#RRGGBB"

    # Helper to parse hex to RGB
    def _hex_to_rgb(self, hex_color):
        if not hex_color: return (0, 0, 0)
        try:
            return tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (0, 0, 0)

# --- Shared Assets Helpers ---
def create_soft_particle(radius, color, alpha=100):
    if not pygame.get_init(): return None
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*color, 255), (radius, radius), 2)
    pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius // 2)
    pygame.draw.circle(surf, (*color, 30), (radius, radius), radius)
    return surf

def create_smooth_disk(inner_r, outer_r=None):
    if not pygame.get_init(): return None
    if outer_r is None:
        outer_r = int(inner_r * 2.2) 
    surf = pygame.Surface((outer_r * 2, outer_r * 2), pygame.SRCALPHA)
    center = outer_r
    for r in range(outer_r, inner_r, -1):
        prog = 1 - (r - inner_r) / (outer_r - inner_r)
        if prog < 0.3:
            color = (100 + prog*100, 50, 100)
            alpha = int(50 * prog)
        elif prog < 0.8:
            color = (255, 100 + int(100*(prog-0.3)*2), 50)
            alpha = int(100 * prog)
        else:
            color = (255, 255, 200)
            alpha = int(180 * prog)
        pygame.draw.circle(surf, (*color, alpha), (center, center), r)
    return surf

def create_zen_texture(radius, color):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    # Alpha 40 for subtle Zen effect
    pygame.draw.circle(surf, (*color, 40), (radius, radius), radius)
    return surf


# --- Black Hole Effect (Dark Mode) ---
class BlackHoleEffect(BaseVisualEffect):
    def __init__(self, width, height, bg_color):
        super().__init__(width, height, bg_color)
        self.HOLE_RADIUS = 66
        self.DISK_OUTER_RADIUS = 110
        self.font_large = pygame.font.SysFont("Impact", 80)
        
        # Assets
        self.p_gold = create_soft_particle(6, (255, 200, 100))
        self.p_blue = create_soft_particle(6, (100, 200, 255))
        self.p_white = create_soft_particle(5, (200, 200, 200))
        self.textures = [self.p_gold, self.p_gold, self.p_blue, self.p_white]
        
        self.disk_img = create_smooth_disk(self.HOLE_RADIUS, self.DISK_OUTER_RADIUS)
        if self.disk_img:
            self.disk_rect = self.disk_img.get_rect(center=(width//2, height//2))
            
        self.stars = []
        for _ in range(150):
            self.stars.append(self.spawn_star(init=True))
            
    def spawn_star(self, init=False):
        min_dist = self.HOLE_RADIUS + 5
        max_dist = max(self.width, self.height) * 1.2 if init else max(self.width, self.height)
        return {
            'dist': random.uniform(min_dist, max_dist),
            'angle': random.uniform(0, math.pi * 2),
            'base_speed': random.uniform(0.2, 0.5),
            'texture': random.choice(self.textures),
            'size_var': random.uniform(0.6, 1.0)
        }

    def update(self):
        cx, cy = self.width // 2, self.height // 2
        for s in self.stars:
            inward_speed = s['base_speed'] + (100 / s['dist']) * 0.5
            s['dist'] -= inward_speed
            
            rotation_speed = 0.002 + (50 / s['dist']) * 0.005 
            s['angle'] += rotation_speed
            
            if s['dist'] < self.HOLE_RADIUS:
                new_s = self.spawn_star(init=False)
                s.update(new_s)

    def draw(self, screen, time_text):
        # 1. Background
        screen.fill(self._hex_to_rgb(self.bg_color))
        
        # 2. Disk
        if self.disk_img:
            screen.blit(self.disk_img, self.disk_rect, special_flags=pygame.BLEND_ADD)
            
        # 3. Stars
        cx, cy = self.width // 2, self.height // 2
        for s in self.stars:
            x = cx + math.cos(s['angle']) * s['dist']
            y = cy + math.sin(s['angle']) * s['dist']
            
            if s['texture']:
                tex = s['texture']
                sz = int(tex.get_width() * s['size_var'])
                if sz > 0:
                    screen.blit(tex, (int(x - sz/2), int(y - sz/2)), special_flags=pygame.BLEND_ADD)

        # 4. Mask & Ring
        pygame.draw.circle(screen, (0, 0, 0), (cx, cy), self.HOLE_RADIUS)
        pygame.draw.circle(screen, (200, 150, 100), (cx, cy), self.HOLE_RADIUS, 1)

        # 5. Text
        text_surf = self.font_large.render(time_text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(self.width // 2, self.height // 2))
        shadow_surf = self.font_large.render(time_text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(self.width // 2 + 2, self.height // 2 + 2))
        
        screen.blit(shadow_surf, shadow_rect)
        screen.blit(text_surf, text_rect)

    def draw_minimal(self, screen, time_text):
        # 1. Background
        screen.fill(self._hex_to_rgb(self.bg_color))
        
        # 2. Text (Same as draw but without disk/stars/mask)
        text_surf = self.font_large.render(time_text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(self.width // 2, self.height // 2))
        shadow_surf = self.font_large.render(time_text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(self.width // 2 + 2, self.height // 2 + 2))
        
        screen.blit(shadow_surf, shadow_rect)
        screen.blit(text_surf, text_rect)


# --- Zen Focus Effect (Light Mode) ---
class ZenFocusEffect(BaseVisualEffect):
    def __init__(self, width, height, bg_color):
        super().__init__(width, height, bg_color)
        self.CENTER = (width // 2, height // 2)
        
        # Zen Config
        self.PARTICLE_COLORS = [
            (0, 174, 239),   # Cyan
            (236, 0, 140),   # Magenta
            (220, 210, 0),   # Yellow
            (120, 120, 240)  # Soft Purple
        ]
        
        self.COLOR_MIN = (0, 110, 190)   # Deep Blue
        self.COLOR_SEC = (200, 40, 110)  # Deep Rose
        self.COLOR_COLON = (200, 200, 200) # Light Grey
        
        # Fonts
        try:
            self.FONT_BIG = pygame.font.SysFont("impact", 80) # 80 to match widget size
            self.FONT_COLON = pygame.font.SysFont("impact", 70)
        except:
            self.FONT_BIG = pygame.font.SysFont("arial", 80, bold=True)
            self.FONT_COLON = pygame.font.SysFont("arial", 70, bold=True)
            
        # Pre-render textures
        self.particle_textures = []
        for c in self.PARTICLE_COLORS:
            self.particle_textures.append(create_zen_texture(15, c))
            self.particle_textures.append(create_zen_texture(25, c))
            
        # Init Particles
        self.particles = [self._create_zen_particle() for _ in range(35)]
        
    def _create_zen_particle(self):
        p = type('obj', (object,), {})() # Quick struct
        p.img = random.choice(self.particle_textures)
        p.angle = random.uniform(0, math.pi * 2)
        p.orbit_radius = random.uniform(110, 170)
        p.orbit_speed = random.uniform(0.001, 0.004) * random.choice([-1, 1])
        p.y_offset = 0
        p.y_speed = random.uniform(0.05, 0.15) * random.choice([-1, 1])
        p.y_limit = random.randint(15, 40)
        
        # Initialize positions locally to ensure they exist before first draw
        p.x = self.CENTER[0] + math.cos(p.angle) * p.orbit_radius
        p.y = self.CENTER[1] + math.sin(p.angle) * p.orbit_radius + p.y_offset
        return p

    def update(self):
         for p in self.particles:
            p.angle += p.orbit_speed
            p.y_offset += p.y_speed
            if abs(p.y_offset) > p.y_limit:
                p.y_speed *= -1
            
            p.x = self.CENTER[0] + math.cos(p.angle) * p.orbit_radius
            p.y = self.CENTER[1] + math.sin(p.angle) * p.orbit_radius + p.y_offset

    def draw(self, screen, time_text):
        # 1. Background
        bg_rgb = self._hex_to_rgb(self.bg_color)
        screen.fill(bg_rgb)
        
        # 2. Draw Particles
        for p in self.particles:
            w, h = p.img.get_size()
            screen.blit(p.img, (int(p.x - w/2), int(p.y - h/2)))
            
        # 3. UI Container (Solid Circle to mask text background)
        # Use same BG color to blend in
        pygame.draw.circle(screen, bg_rgb, self.CENTER, 90)
        # Subtle ring
        pygame.gfxdraw.aacircle(screen, self.CENTER[0], self.CENTER[1], 90, (200, 200, 200))
        
        # 4. Text Rendering (Split Style)
        # Parse time_text "MM:SS"
        try:
            parts = time_text.split(':')
            if len(parts) == 2:
                str_min, str_sec = parts[0], parts[1]
            else:
                str_min, str_sec = "00", "00"
        except:
             str_min, str_sec = "00", "00"

        surf_min = self.FONT_BIG.render(str_min, True, self.COLOR_MIN)
        surf_colon = self.FONT_COLON.render(":", True, self.COLOR_COLON)
        surf_sec = self.FONT_BIG.render(str_sec, True, self.COLOR_SEC)

        total_width = surf_min.get_width() + surf_colon.get_width() + surf_sec.get_width()
        total_height = surf_min.get_height()

        start_x = self.CENTER[0] - total_width // 2
        draw_y = self.CENTER[1] - total_height // 2 - 5

        screen.blit(surf_min, (start_x, draw_y))
        screen.blit(surf_colon, (start_x + surf_min.get_width(), draw_y - 5))
        screen.blit(surf_sec, (start_x + surf_min.get_width() + surf_colon.get_width(), draw_y))

    def draw_minimal(self, screen, time_text):
        # 1. Background
        bg_rgb = self._hex_to_rgb(self.bg_color)
        screen.fill(bg_rgb)
        
        # 2. UI Container (Static Circle)
        pygame.draw.circle(screen, bg_rgb, self.CENTER, 90)
        pygame.gfxdraw.aacircle(screen, self.CENTER[0], self.CENTER[1], 90, (200, 200, 200))

        # 3. Text Rendering (Same as draw)
        try:
            parts = time_text.split(':')
            if len(parts) == 2:
                str_min, str_sec = parts[0], parts[1]
            else:
                str_min, str_sec = "00", "00"
        except:
             str_min, str_sec = "00", "00"

        surf_min = self.FONT_BIG.render(str_min, True, self.COLOR_MIN)
        surf_colon = self.FONT_COLON.render(":", True, self.COLOR_COLON)
        surf_sec = self.FONT_BIG.render(str_sec, True, self.COLOR_SEC)

        total_width = surf_min.get_width() + surf_colon.get_width() + surf_sec.get_width()
        total_height = surf_min.get_height()

        start_x = self.CENTER[0] - total_width // 2
        draw_y = self.CENTER[1] - total_height // 2 - 5

        screen.blit(surf_min, (start_x, draw_y))
        screen.blit(surf_colon, (start_x + surf_min.get_width(), draw_y - 5))
        screen.blit(surf_sec, (start_x + surf_min.get_width() + surf_colon.get_width(), draw_y))
