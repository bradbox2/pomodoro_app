import pygame
import sys
import random

# 初始化Pygame
pygame.init()

# 设置屏幕尺寸
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pomodoro Timer")

# 颜色定义
WHITE = (255, 255, 255)
ORANGE = (255, 100, 0)
DARK_BLUE = (0, 0, 139)
LIGHT_BLUE = (173, 216, 230)
BLACK = (0, 0, 0)
LIGHT_GRAY = (169, 169, 169)

# 字体设置
font = pygame.font.Font(None, 80)
button_font = pygame.font.Font(None, 36)

# 计时器变量
countdown_time = 25 * 60  # 初始倒计时 25分钟
time_left = countdown_time
clock = pygame.time.Clock()

# 粒子效果类
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.randint(3, 6)
        self.color = random.choice([WHITE, LIGHT_BLUE])
        self.speed_x = random.uniform(-1, 1)
        self.speed_y = random.uniform(-1, 1)

    def move(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.size *= 0.98  # 粒子逐渐变小

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.size))

# 创建按钮
start_button_rect = pygame.Rect(300, 500, 200, 50)
complete_button_rect = pygame.Rect(500, 500, 200, 50)

# 绘制番茄计时器
def draw_timer():
    # 绘制动态星空背景
    screen.fill(DARK_BLUE)
    for _ in range(50):
        pygame.draw.circle(screen, WHITE, (random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)), 2)

    # 绘制番茄计时器（圆形）
    pygame.draw.circle(screen, ORANGE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50), 120)
    pygame.draw.circle(screen, LIGHT_BLUE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50), 120)

    # 计时器数字显示
    minutes = time_left // 60
    seconds = time_left % 60
    time_text = font.render(f"{minutes:02}:{seconds:02}", True, WHITE)
    screen.blit(time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))

    # 绘制水波纹（动态渐变）
    water_surface_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 50, 240, 120)
    pygame.draw.rect(screen, LIGHT_BLUE, water_surface_rect)

# 绘制按钮
def draw_buttons():
    # Start按钮
    pygame.draw.rect(screen, ORANGE, start_button_rect)
    start_text = button_font.render("Start", True, WHITE)
    screen.blit(start_text, (start_button_rect.centerx - start_text.get_width() // 2, start_button_rect.centery - start_text.get_height() // 2))

    # Complete按钮
    pygame.draw.rect(screen, LIGHT_GRAY, complete_button_rect)
    complete_text = button_font.render("Complete", True, WHITE)
    screen.blit(complete_text, (complete_button_rect.centerx - complete_text.get_width() // 2, complete_button_rect.centery - complete_text.get_height() // 2))

# 处理按钮悬停效果
def handle_button_hover():
    mouse_pos = pygame.mouse.get_pos()
    if start_button_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, (255, 150, 0), start_button_rect)  # 更亮的橙色
    else:
        pygame.draw.rect(screen, ORANGE, start_button_rect)

    if complete_button_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, (150, 150, 150), complete_button_rect)  # 更亮的灰色
    else:
        pygame.draw.rect(screen, LIGHT_GRAY, complete_button_rect)

# 粒子效果更新
def update_particles(particles):
    for particle in particles[:]:
        particle.move()
        particle.draw(screen)
        if particle.size < 0.5:
            particles.remove(particle)

# 主循环
running = True
timer_running = False
particles = []

while running:
    screen.fill((0, 0, 0, 0))  # 半透明背景
    draw_timer()
    draw_buttons()
    handle_button_hover()

    # 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if start_button_rect.collidepoint(event.pos):  # 点击“Start”按钮
                if not timer_running:
                    timer_running = True
            if complete_button_rect.collidepoint(event.pos):  # 点击“Complete”按钮
                time_left = countdown_time
                timer_running = False

    # 计时器更新
    if timer_running:
        if time_left > 0:
            time_left -= 1
        pygame.time.delay(1000)  # 每秒更新一次

    # 粒子效果
    if timer_running:
        for _ in range(5):
            particles.append(Particle(start_button_rect.centerx, start_button_rect.centery))

    update_particles(particles)

    pygame.display.flip()
    clock.tick(60)  # 设置帧率为60帧

pygame.quit()
sys.exit()
