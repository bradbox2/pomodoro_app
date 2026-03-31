import pygame
import pygame.gfxdraw
import random
import math

# Zen mode

# --- 1. 初始化 ---
pygame.init()
WIDTH, HEIGHT = 800, 600
CENTER = (WIDTH // 2, HEIGHT // 2)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pomodoro Focus - Zen Mode")
clock = pygame.time.Clock()

# --- 2. 视觉配置 (专注模式) ---

# 背景：纯白
BG_COLOR = (255, 255, 255)

# CMYK 配色 (保持配色，但通过透明度降低干扰)
PARTICLE_COLORS = [
    (0, 174, 239),   # Cyan
    (236, 0, 140),   # Magenta
    (220, 210, 0),   # Yellow (稍微调暗一点，避免在白底上太刺眼)
    (120, 120, 240)  # Soft Purple
]

# 文字颜色 (保持您要求的调换方案)
COLOR_MIN = (0, 110, 190)   # 分钟：深海蓝 (沉稳)
COLOR_SEC = (200, 40, 110)  # 秒钟：深玫红 (醒目但不刺眼)
COLOR_COLON = (200, 200, 200) # 冒号：极淡的灰 (弱化存在感)

# 字体
try:
    FONT_BIG = pygame.font.SysFont("impact", 100)
    FONT_COLON = pygame.font.SysFont("impact", 90)
except:
    FONT_BIG = pygame.font.SysFont("arial", 100, bold=True)
    FONT_COLON = pygame.font.SysFont("arial", 90, bold=True)

# --- 3. 极简预渲染 ---
def create_soft_texture(radius, color):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    # [优化点] Alpha 从 80 降到 40
    # 让粒子变成淡淡的背景氛围，不再抢眼
    pygame.draw.circle(surf, (*color, 40), (radius, radius), radius)
    return surf

particle_textures = []
for c in PARTICLE_COLORS:
    # 只保留中等大小，去掉过大或过小的噪点
    particle_textures.append(create_soft_texture(15, c))
    particle_textures.append(create_soft_texture(25, c))

# --- 4. 慢速粒子类 ---
class ZenParticle:
    def __init__(self):
        self.reset()
        # 初始随机分布
        angle = random.uniform(0, math.pi * 2)
        self.angle = angle
        self.update_pos()

    def reset(self):
        self.img = random.choice(particle_textures)
        self.angle = random.uniform(0, math.pi * 2)
        self.orbit_radius = random.uniform(110, 170)
        
        # [优化点] 速度极慢 (Slow Motion)
        # 就像灰尘在阳光下漂浮的感觉
        self.orbit_speed = random.uniform(0.001, 0.004) * random.choice([-1, 1])
        
        self.y_offset = 0
        # 垂直浮动也非常微弱
        self.y_speed = random.uniform(0.05, 0.15) * random.choice([-1, 1])
        self.y_limit = random.randint(15, 40)

    def update_pos(self):
        self.x = CENTER[0] + math.cos(self.angle) * self.orbit_radius
        self.y = CENTER[1] + math.sin(self.angle) * self.orbit_radius + self.y_offset

    def update(self):
        self.angle += self.orbit_speed
        self.y_offset += self.y_speed
        
        # 缓动边缘
        if abs(self.y_offset) > self.y_limit:
            self.y_speed *= -1
            
        self.update_pos()

    def draw(self, surface):
        w, h = self.img.get_size()
        surface.blit(self.img, (int(self.x - w/2), int(self.y - h/2)))

# [优化点] 粒子数量减少至 35 (原80)
# 足够营造氛围，对笔记本电池极其友好
particles = [ZenParticle() for _ in range(35)]

# --- 5. 主循环 ---
running = True
while running:
    # 保持 60 帧以获得丝滑的移动，但因为计算量极小，不费电
    clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 1. 绘制背景
    screen.fill(BG_COLOR)

    # 2. 绘制粒子
    for p in particles:
        p.update()
        p.draw(screen)

    # 3. UI 容器 (更加隐形)
    # 实心白圆 (遮挡背景)
    pygame.draw.circle(screen, BG_COLOR, CENTER, 90)
    
    # [优化点] 装饰环变淡
    # 几乎看不见的淡灰色，只在潜意识里提供边界感
    pygame.gfxdraw.aacircle(screen, CENTER[0], CENTER[1], 90, (240, 240, 240))
    
    # 4. 文字渲染
    ticks = pygame.time.get_ticks()
    # 模拟 25 分钟倒计时
    remaining_sec = 25 * 60 - (ticks // 1000)
    if remaining_sec < 0: remaining_sec = 0
    
    m = remaining_sec // 60
    s = remaining_sec % 60
    str_min = f"{m:02d}"
    str_sec = f"{s:02d}"

    surf_min = FONT_BIG.render(str_min, True, COLOR_MIN)
    surf_colon = FONT_COLON.render(":", True, COLOR_COLON)
    surf_sec = FONT_BIG.render(str_sec, True, COLOR_SEC)

    # 动态居中计算
    total_width = surf_min.get_width() + surf_colon.get_width() + surf_sec.get_width()
    total_height = surf_min.get_height()

    start_x = CENTER[0] - total_width // 2
    draw_y = CENTER[1] - total_height // 2 - 5

    # 绘制文字
    screen.blit(surf_min, (start_x, draw_y))
    screen.blit(surf_colon, (start_x + surf_min.get_width(), draw_y - 5))
    screen.blit(surf_sec, (start_x + surf_min.get_width() + surf_colon.get_width(), draw_y))

    pygame.display.flip()

pygame.quit()