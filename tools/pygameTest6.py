import customtkinter as ctk
import pygame
import pygame.gfxdraw
import random
import math
import sys
import ctypes
import win32gui
import win32con
import win32api

# --- Windows DPI 适配 ---
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# ==========================================
# 1. Mini Zen Widget (伴随模式渲染器)
# ==========================================
class MiniZenWidget:
    def __init__(self):
        self.width = 300  # 小部件宽度
        self.height = 160 # 小部件高度
        self.screen = None
        self.running = False
        self.hwnd = None  # 窗口句柄
        
        # 视觉配置 (Mini版)
        self.bg_color = (8, 10, 16)
        self.particle_colors = [(100, 255, 255), (150, 100, 255), (200, 220, 255)]
        self.void_radius = 45 # 缩小黑洞半径以适应小窗口

    def _init_assets(self):
        # 1. 简化的粒子 (为了小窗口清晰度，减少光晕层数)
        def create_glow(radius, color):
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, 200), (radius, radius), radius // 2)
            pygame.draw.circle(s, (*color, 50), (radius, radius), radius)
            return s
        
        self.particle_imgs = [create_glow(4, c) for c in self.particle_colors] + \
                             [create_glow(8, c) for c in self.particle_colors]

        # 2. 简化的日冕
        def create_corona(inner_r):
            size = int(inner_r * 4.0)
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            for _ in range(80): # 减少数量
                ang = random.uniform(0, math.pi * 2)
                dst = inner_r + random.uniform(-5, 15)
                br = random.randint(10, 25)
                bx = c + math.cos(ang) * dst
                by = c + math.sin(ang) * dst
                col = random.choice([(50, 100, 200), (0, 150, 200)])
                pygame.draw.circle(s, (*col, 30), (int(bx), int(by)), br)
            return s

        self.corona_surf = create_corona(self.void_radius)
        self.corona_rect = self.corona_surf.get_rect(center=(self.width//4 + 20, self.height//2)) # 偏左放置

        # 3. 粒子对象
        self.particles = [self._create_mote() for _ in range(60)] # 减少数量

    def _create_mote(self):
        return {
            'img': random.choice(self.particle_imgs),
            'angle': random.uniform(0, math.pi * 2),
            'dist': random.uniform(self.void_radius + 10, 120),
            'speed': random.uniform(0.005, 0.01) * random.choice([-1, 1]),
            'x': 0, 'y': 0
        }

    def _update_mote(self, m, center):
        m['angle'] += m['speed']
        m['x'] = center[0] + math.cos(m['angle']) * m['dist']
        m['y'] = center[1] + math.sin(m['angle']) * m['dist']

    def _set_window_style(self):
        """设置窗口：置顶 + 工具栏样式(不显示在任务栏)"""
        self.hwnd = pygame.display.get_wm_info()["window"]
        
        # 获取屏幕尺寸，默认放在右下角
        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)
        start_x = screen_w - self.width - 20
        start_y = screen_h - self.height - 60 # 避开任务栏
        
        # 移动窗口并置顶
        win32gui.SetWindowPos(
            self.hwnd, 
            win32con.HWND_TOPMOST, 
            start_x, start_y, 
            0, 0, 
            win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
        )

    def run(self, duration_minutes):
        pygame.init()
        
        # 创建无边框小窗口
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        pygame.display.set_caption("ZEN WIDGET")
        
        # 设置置顶和位置
        try: self._set_window_style()
        except Exception as e: print(f"WinAPI Error: {e}")
        
        clock = pygame.time.Clock()
        self._init_assets()
        
        # 布局重心：偏左，给右边留出时间显示
        center = (self.width // 4 + 20, self.height // 2)
        
        start_ticks = pygame.time.get_ticks()
        total_sec = duration_minutes * 60
        
        # 字体
        try: font_t = pygame.font.SysFont("impact", 48)
        except: font_t = pygame.font.Font(None, 60)
        try: font_s = pygame.font.SysFont("arial", 12)
        except: font_s = pygame.font.Font(None, 14)

        self.running = True
        completed = False

        while self.running:
            clock.tick(30) # 降低帧率省电
            now = pygame.time.get_ticks()
            
            # --- 事件处理 (含拖拽逻辑) ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # 左键按下：开始拖拽
                        # 魔法代码：欺骗 Windows 以为我们在拖动标题栏
                        win32gui.ReleaseCapture()
                        win32gui.SendMessage(self.hwnd, win32con.WM_NCLBUTTONDOWN, win32con.HTCAPTION, 0)
                    elif event.button == 3: # 右键按下：退出
                        self.running = False

            # --- 逻辑更新 ---
            elapsed = (now - start_ticks) / 1000
            rem = max(0, total_sec - elapsed)
            if rem <= 0:
                completed = True
                pygame.time.wait(1000)
                self.running = False

            # --- 绘图 ---
            self.screen.fill(self.bg_color)
            
            # 1. 绘制左侧装饰 (黑洞与粒子)
            self.screen.blit(self.corona_surf, self.corona_rect, special_flags=pygame.BLEND_ADD)
            
            for m in self.particles:
                self._update_mote(m, center)
                if 0 < m['x'] < self.width and 0 < m['y'] < self.height:
                    self.screen.blit(m['img'], (int(m['x']), int(m['y'])), special_flags=pygame.BLEND_ADD)
            
            pygame.draw.circle(self.screen, self.bg_color, center, self.void_radius)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], self.void_radius, (100, 200, 255))

            # 2. 绘制右侧文字
            mins, secs = int(rem // 60), int(rem % 60)
            t_str = f"{mins:02d}:{secs:02d}"
            
            # 时间
            txt = font_t.render(t_str, True, (220, 240, 255))
            self.screen.blit(txt, (140, 45)) # 固定在右侧
            
            # 提示小字
            tip = font_s.render("Right-Click to Expand", True, (80, 80, 100))
            self.screen.blit(tip, (145, 100))
            
            # 绘制边框 (增加精致感)
            pygame.draw.rect(self.screen, (40, 50, 70), (0, 0, self.width, self.height), 1)

            pygame.display.flip()

        pygame.quit()
        return completed

# ==========================================
# 2. 主程序 (CustomTkinter)
# ==========================================
class PomodoroApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Zen Pomodoro - Companion Mode")
        self.geometry("400x350")
        
        self.mini_widget = MiniZenWidget()
        
        # UI
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(self.frame, text="WORK SESSION", font=("Impact", 24)).pack(pady=20)
        
        self.slider = ctk.CTkSlider(self.frame, from_=1, to=60, number_of_steps=59)
        self.slider.set(25)
        self.slider.pack(fill="x", padx=40, pady=20)
        
        # 按钮
        self.btn_mini = ctk.CTkButton(
            self.frame, text="START COMPANION WIDGET", height=50,
            fg_color="#00e5ff", text_color="black", font=("Arial", 14, "bold"),
            command=self.start_mini_mode
        )
        self.btn_mini.pack(pady=20)
        
        ctk.CTkLabel(self.frame, text="Widget will appear at bottom-right\nDrag to move • Right-Click to exit", 
                     text_color="gray", font=("Arial", 11)).pack(side="bottom", pady=10)

    def start_mini_mode(self):
        mins = int(self.slider.get())
        
        # 1. 隐藏主窗口
        self.withdraw()
        
        # 2. 运行小部件 (阻塞)
        try:
            self.mini_widget.run(mins)
        except Exception as e:
            print(f"Widget Error: {e}")
            
        # 3. 恢复主窗口
        self.deiconify()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = PomodoroApp()
    app.mainloop()