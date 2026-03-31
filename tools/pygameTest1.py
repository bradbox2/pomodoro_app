import pygame
import random
import math

# --- 1. 初始化设置 ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cyber Breathing - Low Power Mode")
clock = pygame.time.Clock()

# --- 2. 预渲染优化 (Pre-rendering) ---
# 我们只生成一张高质量的光晕图，后续重复利用
# 这比每一帧实时画圆要省电得多
def create_glow_texture(radius, color):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    # 画几层不同透明度的圆来模拟高斯模糊
    for i in range(radius, 0, -2):
        alpha = int(100 * (i / radius)**3) # 指数级衰减，中心亮边缘淡
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), i)
    return surf

# 预生成两种颜色的“大”粒子 (青色和紫色)
# 使用 convert_alpha() 是 Pygame 性能优化的关键
glow_cyan = create_glow_texture(60, (0, 255, 255))
glow_purple = create_glow_texture(70, (150, 0, 255))

# --- 3. 粒子类 ---
class Orb:
    def __init__(self):
        self.reset()
        # 让粒子初始位置随机分布，不要一开始都聚在一起
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.timer = random.uniform(0, math.pi * 2) # 用于呼吸效果的随机相位

    def reset(self):
        self.x = random.randint(0, WIDTH)
        self.y = HEIGHT + 100 # 从屏幕下方生成
        self.speed = random.uniform(0.5, 1.5) # 极慢的速度，省电且优雅
        self.radius_scale = random.uniform(0.5, 1.0)
        self.texture = glow_cyan if random.random() > 0.5 else glow_purple
        self.timer = random.uniform(0, 100)

    def update(self):
        self.y -= self.speed
        self.timer += 0.05
        
        # 左右微微摆动 (正弦波)
        self.x += math.sin(self.timer) * 0.5
        
        # 如果飘出屏幕上方，重置到底部
        if self.y < -100:
            self.reset()

    def draw(self, surface):
        # 呼吸效果：根据时间改变大小
        pulse = 1.0 + math.sin(self.timer) * 0.2
        
        # 这种缩放稍微有点费CPU，但因为粒子总数少(50个)，完全可控
        # 如果追求极致省电，可以去掉 pygame.transform.scale，只改变透明度
        current_size = int(self.texture.get_width() * self.radius_scale * pulse)
        scaled_img = pygame.transform.scale(self.texture, (current_size, current_size))
        
        # 关键：BLEND_ADD 让重叠部分变亮，产生"高级感"
        draw_x = int(self.x - current_size / 2)
        draw_y = int(self.y - current_size / 2)
        surface.blit(scaled_img, (draw_x, draw_y), special_flags=pygame.BLEND_ADD)

# --- 4. 主循环 ---
# 限制粒子数量为 50 个。这在任何双核笔记本上都能跑满 60帧。
particles = [Orb() for _ in range(50)]

running = True
while running:
    # 限制 60 FPS，这对省电至关重要
    clock.tick(60) 
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 背景不使用纯黑，使用极深的蓝紫色，提升质感
    screen.fill((10, 10, 20))

    for p in particles:
        p.update()
        p.draw(screen)

    # 可选：显示帧率监控性能
    # pygame.display.set_caption(f"FPS: {clock.get_fps():.2f}")

    pygame.display.flip()

pygame.quit()