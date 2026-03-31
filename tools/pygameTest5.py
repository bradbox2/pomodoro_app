import customtkinter as ctk
import pygame
import pygame.gfxdraw
import random
import math
import sys
import ctypes

# --- 0. Windows High-DPI 修复 (防止模糊/坐标偏移) ---
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# ==========================================
# 1. 游戏风格进度条组件 (HUD UI) - [已修复报错]
# ==========================================
class GameFocusBar(ctk.CTkCanvas):
    def __init__(self, master, width=400, height=40, target_val=100, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, **kwargs)
        self.w = width
        self.h = height
        self.target_val = target_val
        self.current_val = 0
        self.display_val = 0
        
        # 配色配置
        self.colors = {
            "Light": { "bg": "#e0e0e0", "border": "#bbbbbb", "fill": "#007AFF", "text": "#333333", "seg": "#ffffff" },
            "Dark":  { "bg": "#2b2b2b", "border": "#3a3a3a", "fill": "#00e5ff", "text": "#ffffff", "seg": "#000000" }
        }
        self.bind("<Configure>", self._on_resize)
        self.update_view()

    def set_progress(self, current):
        self.current_val = current
        self._animate()

    def _animate(self):
        diff = self.current_val - self.display_val
        if abs(diff) < 0.1:
            self.display_val = self.current_val
            self.update_view()
            return
        self.display_val += diff * 0.2 # 动画速度
        self.update_view()
        self.after(16, self._animate)

    def _get_theme_color(self, key):
        mode = ctk.get_appearance_mode()
        return self.colors.get(mode, self.colors["Dark"])[key]

    def _draw_hud_shape(self, x1, y1, x2, y2, cut_size=10):
        real_cut = min(cut_size, (y2 - y1) // 2)
        return [x1, y1, x2, y1, x2, y2 - real_cut, x2 - real_cut, y2, x1, y2]

    def update_view(self):
        try: self.delete("all")
        except: return
        
        bg_c = self._get_theme_color("bg")
        bd_c = self._get_theme_color("border")
        fill_c = self._get_theme_color("fill")
        txt_c = self._get_theme_color("text")
        seg_c = self._get_theme_color("seg")
        
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: w, h = self.w, self.h
        
        pad = 2
        cut = h // 3
        
        # 绘制背景
        self.create_polygon(self._draw_hud_shape(pad, pad, w-pad, h-pad, cut), fill=bg_c, outline=bd_c, width=2)

        # 绘制填充
        if self.target_val > 0 and self.display_val > 0:
            ratio = min(1.0, self.display_val / self.target_val)
            fw = (w - 2 * pad) * ratio
            if fw > 5:
                shape = self._draw_hud_shape(pad+2, pad+2, pad+fw-2, h-pad-2, cut) if ratio >= 0.99 else \
                        [pad+2, pad+2, pad+fw, pad+2, pad+fw-5, h-pad-2, pad+2, h-pad-2]
                self.create_polygon(shape, fill=fill_c, outline="")
                
                # 分隔线
                for i in range(1, 10):
                    sx = pad + ((w - 2 * pad) * (i/10))
                    if sx < (pad + fw - 5):
                        self.create_line(sx+2, pad+2, sx-2, h-pad-2, fill=seg_c, width=1, stipple="gray50")

        # --- 修复部分 START ---
        # 移除了导致报错的 ctk.FontManager 检查
        # 直接尝试使用 Impact，如果系统没有，Tkinter 会自动回退到默认字体，不会报错
        font_config = ("Impact", 14) 
        # --- 修复部分 END ---

        self.create_text(w/2, h/2, text=f"{int(self.display_val)} MIN", fill=txt_c, font=font_config)

    def _on_resize(self, event):
        self.update_view()

# ==========================================
# 2. Pygame 渲染器: Ethereal Eclipse (空灵日食)
# ==========================================
class ZenFocusRenderer:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.screen = None
        self.clock = None
        self.running = False
        
        # Zen Dark Mode 配置
        self.bg_color = (8, 10, 16) # 午夜蓝
        self.void_radius = 120      # 黑洞半径
        self.particle_colors = [(100, 255, 255), (150, 100, 255), (200, 220, 255)]
        
        self.particle_imgs = []
        self.corona_surf = None
        self.corona_rect = None
        self.particles = []

    def _init_assets(self):
        # 1. 粒子光斑
        def create_glow(radius, color, alpha_f=1.0):
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, int(100 * alpha_f)), (radius, radius), radius // 3)
            pygame.draw.circle(s, (*color, int(30 * alpha_f)), (radius, radius), radius)
            return s
        
        self.particle_imgs = [create_glow(8, c, 0.8) for c in self.particle_colors] + \
                             [create_glow(15, c, 0.5) for c in self.particle_colors]

        # 2. 日冕光环 (Corona)
        def create_corona(inner_r):
            size = int(inner_r * 4.5)
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            for _ in range(120):
                ang = random.uniform(0, math.pi * 2)
                dst = inner_r + random.uniform(-10, 40)
                br = random.randint(20, 50)
                bx = c + math.cos(ang) * dst
                by = c + math.sin(ang) * dst
                col = random.choice([(50, 100, 200), (0, 150, 200), (100, 50, 180)])
                pygame.draw.circle(s, (*col, random.randint(10, 30)), (int(bx), int(by)), br)
            return s

        self.corona_surf = create_corona(self.void_radius)
        self.corona_rect = self.corona_surf.get_rect(center=(self.width//2, self.height//2))
        
        # 3. 初始化粒子
        self.particles = [self._create_mote() for _ in range(150)]

    def _create_mote(self):
        return {
            'img': random.choice(self.particle_imgs),
            'angle': random.uniform(0, math.pi * 2),
            'dist': random.uniform(self.void_radius + 50, 450),
            'speed': random.uniform(0.002, 0.005) * random.choice([-1, 1]),
            'ps': random.uniform(0.1, 0.3), 'po': random.uniform(0, 100) # pulse speed/offset
        }

    def _update_mote(self, m, timer, center):
        m['angle'] += m['speed']
        wobble = math.sin(timer * m['ps'] + m['po']) * 20
        curr_dist = m['dist'] + wobble
        m['x'] = center[0] + math.cos(m['angle']) * curr_dist
        m['y'] = center[1] + math.sin(m['angle']) * curr_dist

    def run(self, duration_minutes):
        pygame.init()
        
        # 获取屏幕尺寸，创建一个无边框的窗口覆盖全屏
        info = pygame.display.Info()
        w, h = info.current_w, info.current_h
        
        try:
            self.screen = pygame.display.set_mode((w, h), pygame.NOFRAME)
        except:
            # 保底方案
            self.screen = pygame.display.set_mode((1280, 720))
            
        self.width, self.height = self.screen.get_size()
        pygame.display.set_caption("ZEN FOCUS")
        pygame.mouse.set_visible(False)
        
        self.clock = pygame.time.Clock()
        self._init_assets()
        
        center = (self.width // 2, self.height // 2)
        start_ticks = pygame.time.get_ticks()
        total_sec = duration_minutes * 60
        
        # 字体加载 (增加保底)
        try: font_t = pygame.font.SysFont("arial", 100)
        except: font_t = pygame.font.Font(None, 100)
        try: font_s = pygame.font.SysFont("arial", 24)
        except: font_s = pygame.font.Font(None, 24)

        self.running = True
        completed = False

        while self.running:
            self.clock.tick(60)
            now = pygame.time.get_ticks()
            timer = now * 0.001
            
            # 事件
            for e in pygame.event.get():
                if e.type == pygame.QUIT: self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: self.running = False

            # 逻辑
            elapsed = (now - start_ticks) / 1000
            rem = max(0, total_sec - elapsed)
            if rem <= 0:
                completed = True
                pygame.time.wait(2000)
                self.running = False

            # 绘图
            self.screen.fill(self.bg_color)
            
            # 1. 日冕
            scale = 1.0 + math.sin(timer * 0.8) * 0.03
            try:
                if self.corona_rect.width > 0:
                    sw, sh = int(self.corona_rect.w * scale), int(self.corona_rect.h * scale)
                    sc = pygame.transform.smoothscale(self.corona_surf, (sw, sh))
                    self.screen.blit(sc, sc.get_rect(center=center), special_flags=pygame.BLEND_ADD)
            except: pass 

            # 2. 粒子
            for m in self.particles:
                self._update_mote(m, timer, center)
                if 0 < m['x'] < self.width and 0 < m['y'] < self.height:
                    self.screen.blit(m['img'], (int(m['x']), int(m['y'])), special_flags=pygame.BLEND_ADD)

            # 3. 黑洞与视界
            pygame.draw.circle(self.screen, self.bg_color, center, self.void_radius)
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], self.void_radius, (100, 200, 255))
            pygame.gfxdraw.aacircle(self.screen, center[0], center[1], self.void_radius+1, (50, 100, 200))

            # 4. 文字
            mins, secs = int(rem // 60), int(rem % 60)
            t_str = f"{mins:02d}:{secs:02d}"
            
            # 简单的发光文字
            t_surf = font_t.render(t_str, True, (220, 240, 255))
            t_rect = t_surf.get_rect(center=center)
            # 悬浮动画
            t_rect.y += math.sin(timer * 2) * 4
            self.screen.blit(t_surf, t_rect)

            tip = font_s.render("Press ESC to exit Zen Mode", True, (80, 80, 100))
            self.screen.blit(tip, (self.width//2 - tip.get_width()//2, self.height - 50))

            pygame.display.flip()

        pygame.quit()
        return completed

# ==========================================
# 3. 主程序 App (CustomTkinter)
# ==========================================
class PomodoroApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Zen Pomodoro Ultimate")
        self.geometry("450x400")
        
        self.renderer = ZenFocusRenderer()
        
        # 布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        ctk.CTkLabel(self.main_frame, text="ZEN FOCUS", font=("Impact", 24)).pack(pady=(20, 10))
        
        # 游戏风格进度条
        self.hud_bar = GameFocusBar(self.main_frame, height=50, target_val=60)
        self.hud_bar.pack(fill="x", padx=20, pady=10)
        
        # 滑块
        self.slider = ctk.CTkSlider(self.main_frame, from_=1, to=60, number_of_steps=59, command=self.on_slide)
        self.slider.set(25)
        self.slider.pack(fill="x", padx=40, pady=(10, 5))
        
        ctk.CTkLabel(self.main_frame, text="Drag to set duration", text_color="gray", font=("Arial", 10)).pack()

        # 启动按钮
        self.btn_start = ctk.CTkButton(
            self.main_frame, text="ENTER THE VOID", height=50,
            fg_color="#00e5ff", text_color="black", hover_color="#00b8cc",
            font=("Arial", 15, "bold"), command=self.start_zen
        )
        self.btn_start.pack(pady=40)
        
        # 初始化一下Bar的显示
        self.on_slide(25)

    def on_slide(self, val):
        self.hud_bar.set_progress(val)

    def start_zen(self):
        mins = int(self.slider.get())
        
        # 1. 隐藏主界面
        self.withdraw()
        
        # 2. 运行 Pygame (阻塞直到退出)
        try:
            self.renderer.run(mins)
        except Exception as e:
            print(f"Error: {e}")
        
        # 3. 恢复主界面
        self.deiconify()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = PomodoroApp()
    app.mainloop()