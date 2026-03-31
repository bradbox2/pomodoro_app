import pygame
import pygame.gfxdraw
import random
import math

# --- 1. 初始化 ---
pygame.init()
WIDTH, HEIGHT = 800, 600
CENTER = (WIDTH // 2, HEIGHT // 2)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zen Focus - Ethereal Eclipse")
clock = pygame.time.Clock()

# --- 2. 视觉配置 (Zen Dark Mode) ---

# 背景：不是纯黑，而是极深的午夜蓝，减少视觉疲劳
BG_COLOR = (8, 10, 16) 

# 粒子配色：冷色调的萤火虫 (青、紫、白)
# 这种配色比之前的黄红更冷静，适合专注
PARTICLE_COLORS = [
    (100, 255, 255), # Cyan Glow
    (150, 100, 255), # Purple Haze
    (200, 220, 255)  # Starlight
]

# 黑洞半径
VOID_RADIUS = 110

# --- 3. 高级美术资源预渲染 ---

def create_glow_blob(radius, color, alpha_factor=1.0):
    """创建柔和的光斑（模拟气体）"""
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    
    # 核心层
    inner_alpha = int(100 * alpha_factor)
    pygame.draw.circle(surf, (*color, inner_alpha), (radius, radius), radius // 3)
    
    # 外围光晕 (多次叠加模拟高斯模糊)
    outer_alpha = int(30 * alpha_factor)
    pygame.draw.circle(surf, (*color, outer_alpha), (radius, radius), radius)
    
    return surf

# 预生成粒子贴图
particle_imgs = []
for c in PARTICLE_COLORS:
    particle_imgs.append(create_glow_blob(8, c, 0.8))  # 小光点
    particle_imgs.append(create_glow_blob(15, c, 0.5)) # 中光斑

# 预生成“日冕”光环 (The Corona)
# 这是一个巨大的静态图，由数百个半透明光斑堆叠而成，看起来像气体
def create_corona_ring(inner_r):
    size = int(inner_r * 4.5)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    
    # 随机堆叠光斑，制造有机的“气体感”
    # 颜色偏向青色和紫色
    for _ in range(120):
        angle = random.uniform(0, math.pi * 2)
        # 光斑分布在黑洞边缘附近
        dist = inner_r + random.uniform(-10, 40)
        
        blob_r = random.randint(20, 50)
        
        x = center + math.cos(angle) * dist
        y = center + math.sin(angle) * dist
        
        # 随机颜色
        base_color = random.choice([(50, 100, 200), (0, 150, 200), (100, 50, 180)])
        alpha = random.randint(10, 30) # 非常淡
        
        pygame.draw.circle(surf, (*base_color, alpha), (int(x), int(y)), blob_r)
        
    return surf

corona_surf = create_corona_ring(VOID_RADIUS)
corona_rect = corona_surf.get_rect(center=CENTER)

# --- 4. 粒子系统 (漂流逻辑) ---
class VoidMote:
    def __init__(self):
        self.reset()
        # 初始随机分布
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(VOID_RADIUS + 20, 400)
        self.x = CENTER[0] + math.cos(angle) * dist
        self.y = CENTER[1] + math.sin(angle) * dist
        
    def reset(self):
        self.img = random.choice(particle_imgs)
        self.angle = random.uniform(0, math.pi * 2)
        self.dist = random.uniform(VOID_RADIUS + 50, 450)
        
        # 极慢的轨道漂流
        self.orbit_speed = random.uniform(0.002, 0.005) * random.choice([-1, 1])
        # 微微的径向呼吸 (靠近又远离)
        self.pulse_speed = random.uniform(0.1, 0.3)
        self.pulse_offset = random.uniform(0, 100)
        
    def update(self):
        # 1. 公转
        self.angle += self.orbit_speed
        
        # 2. 呼吸式径向移动 (不再是单纯的吸入)
        # 粒子在轨道上会有轻微的“沉浮”，像海浪
        wobble = math.sin(pygame.time.get_ticks() * 0.001 * self.pulse_speed + self.pulse_offset) * 20
        current_dist = self.dist + wobble
        
        self.x = CENTER[0] + math.cos(self.angle) * current_dist
        self.y = CENTER[1] + math.sin(self.angle) * current_dist

    def draw(self, surface):
        surface.blit(self.img, (int(self.x), int(self.y)), special_flags=pygame.BLEND_ADD)

# 粒子数量：150个 (足够丰富但省电)
motes = [VoidMote() for _ in range(150)]

# --- 5. 主循环 ---
timer = 0
running = True
while running:
    clock.tick(60)
    timer += 0.02 # 用于呼吸动画
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 1. 背景
    screen.fill(BG_COLOR)

    # 2. 绘制日冕光环 (Breathing Corona)
    # 让光环有轻微的缩放呼吸效果，增加生命力
    scale = 1.0 + math.sin(timer) * 0.02
    scaled_corona = pygame.transform.smoothscale(corona_surf, (int(corona_rect.width * scale), int(corona_rect.height * scale)))
    scaled_rect = scaled_corona.get_rect(center=CENTER)
    
    # 使用 BLEND_ADD 让光环发光
    screen.blit(scaled_corona, scaled_rect, special_flags=pygame.BLEND_ADD)

    # 3. 绘制漂流粒子
    for m in motes:
        m.update()
        m.draw(screen)

    # 4. 绘制黑洞实体 (The Void)
    # 这是一个覆盖在所有东西上面的纯色圆，创造出"空"的感觉
    pygame.draw.circle(screen, BG_COLOR, CENTER, VOID_RADIUS)
    
    # 5. 事件视界 (Event Horizon) - 关键的美化细节
    # 在黑洞边缘画一个非常细、非常亮的环，强调边缘
    # 模拟光的衍射
    pygame.gfxdraw.aacircle(screen, CENTER[0], CENTER[1], VOID_RADIUS, (100, 200, 255))
    pygame.gfxdraw.aacircle(screen, CENTER[0], CENTER[1], VOID_RADIUS + 1, (50, 100, 200))
    
    # [可选] 倒计时文字区域
    # 这里只画一个占位符，你的文字代码可以放在这里
    # 建议使用白色或淡青色文字
    
    pygame.display.flip()

pygame.quit()