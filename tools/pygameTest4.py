import customtkinter as ctk
import math

# ==========================================
# 1. 游戏风格进度条组件 (核心组件)
# ==========================================
class GameFocusBar(ctk.CTkCanvas):
    def __init__(self, master, width=400, height=40, target_val=100, **kwargs):
        # 初始化 Canvas，移除边框高亮
        super().__init__(master, width=width, height=height, highlightthickness=0, **kwargs)
        
        # --- 核心数据 ---
        self.w = width
        self.h = height
        self.target_val = target_val    # 目标值 (例如：预计专注60分钟)
        self.current_val = 0            # 实际逻辑值
        self.display_val = 0            # 动画渲染值 (用于平滑过渡)
        
        # --- 配色方案 (配置字典) ---
        self.colors = {
            "Light": {
                "bg": "#e0e0e0",             # 空槽背景
                "border": "#bbbbbb",         # 边框
                "fill_normal": "#007AFF",    # 正常进度 (iOS蓝)
                "fill_over": "#FF3B30",      # 超额警示 (红色)
                "text": "#333333",           # 文字颜色
                "segment": "#ffffff"         # 分隔线颜色
            },
            "Dark": {
                "bg": "#2b2b2b",             # 空槽背景
                "border": "#3a3a3a",         # 边框
                "fill_normal": "#00e5ff",    # 正常进度 (赛博青)
                "fill_over": "#ff3333",      # 超额警示 (霓虹红)
                "text": "#ffffff",           # 文字颜色
                "segment": "#000000"         # 分隔线颜色
            }
        }

        # 绑定事件：窗口大小改变时重绘
        self.bind("<Configure>", self._on_resize)
        self.update_view()

    def set_progress(self, current, target=None):
        """
        更新进度接口
        :param current: 当前完成数量/时间
        :param target: (可选) 新的目标值
        """
        self.current_val = current
        if target is not None:
            self.target_val = target
        
        # 触发动画循环
        self._animate()

    def _animate(self):
        """简单的缓动动画 (Lerp)"""
        # 计算差值
        diff = self.current_val - self.display_val
        
        # 如果差值非常小，直接对齐并停止动画 (避免无限循环)
        if abs(diff) < 0.1:
            self.display_val = self.current_val
            self.update_view()
            return

        # 缓动系数 0.15，数值越大动画越快，越小越平滑
        self.display_val += diff * 0.15
        self.update_view()
        
        # 16ms 后继续下一帧 (约60FPS)
        self.after(16, self._animate)

    def _get_theme_color(self, key):
        """获取当前模式下的颜色"""
        mode = ctk.get_appearance_mode() # "Light" or "Dark"
        return self.colors.get(mode, self.colors["Dark"])[key]

    def _draw_hud_shape(self, x1, y1, x2, y2, cut_size=10):
        """生成带斜角的坐标列表 (游戏 HUD 风格)"""
        # 形状：矩形但右下角被切掉
        # 只有当高度足够时才切角，防止报错
        real_cut = min(cut_size, (y2 - y1) // 2)
        
        return [
            x1, y1,                 # 左上
            x2, y1,                 # 右上
            x2, y2 - real_cut,      # 右下(切角起点)
            x2 - real_cut, y2,      # 右下(切角终点)
            x1, y2                  # 左下
        ]

    def update_view(self):
        """核心绘制逻辑"""
        try:
            self.delete("all") # 清空画布
        except:
            return # 防止销毁后报错
        
        # 1. 获取当前颜色
        bg_col = self._get_theme_color("bg")
        border_col = self._get_theme_color("border")
        text_col = self._get_theme_color("text")
        seg_col = self._get_theme_color("segment")
        
        # 判断是否超额
        is_overload = self.display_val > self.target_val
        fill_col = self._get_theme_color("fill_over" if is_overload else "fill_normal")

        # 2. 绘制背景槽 (空条)
        # 背景需要根据当前画布大小自适应 (防止 resize 时变形)
        w, h = self.winfo_width(), self.winfo_height()
        # 如果还没渲染出来(初始化时)，用传入的默认宽高
        if w <= 1: w, h = self.w, self.h
        
        pad_x, pad_y = 2, 2
        cut = h // 3 # 斜角大小随高度变化
        
        bg_coords = self._draw_hud_shape(pad_x, pad_y, w-pad_x, h-pad_y, cut)
        self.create_polygon(bg_coords, fill=bg_col, outline=border_col, width=2)

        # 3. 绘制进度条 (填充)
        if self.target_val > 0 and self.display_val > 0:
            # 计算进度比例 (最大限制为 1.0，即填满整个槽，超额时只变色不爆框)
            ratio = min(1.0, self.display_val / self.target_val)
            fill_width = (w - 2 * pad_x) * ratio
            
            # 只有当宽度足够时才绘制
            if fill_width > 5:
                # 只有当填充满时，才显示右侧的斜角，否则是垂直边缘
                if ratio >= 0.99:
                    fill_coords = self._draw_hud_shape(pad_x+2, pad_y+2, pad_x+fill_width-2, h-pad_y-2, cut)
                else:
                    # 未满时，右边是直的 (带一点倾斜更好看)
                    slant = 5 # 内部小倾斜
                    fill_coords = [
                        pad_x+2, pad_y+2,
                        pad_x+fill_width, pad_y+2,
                        pad_x+fill_width-slant, h-pad_y-2,
                        pad_x+2, h-pad_y-2
                    ]
                
                self.create_polygon(fill_coords, fill=fill_col, outline="")
                
                # 4. 绘制分段线 (装饰效果，增加科技感)
                # 每 10% 画一条细线
                for i in range(1, 10):
                    seg_x = pad_x + ((w - 2 * pad_x) * (i/10))
                    if seg_x < (pad_x + fill_width - 5): # 只在填充区域内画
                        # 稍微倾斜的分隔线
                        self.create_line(seg_x + 2, pad_y+2, seg_x - 2, h-pad_y-2, fill=seg_col, width=1, stipple="gray50")

        # 5. 绘制文字信息 (HUD 数据)
        # 尝试加载字体，如果失败使用默认
        font_name = "Arial"
        # 检查系统中是否有 Impact (Windows常见)
        try:
            if "Impact" in ctk.FontManager.load_font_dict():
                font_name = "Impact"
        except:
            pass
            
        font_style = (font_name, 14)
        
        if is_overload:
            over_val = int(self.display_val - self.target_val)
            text_str = f"WARNING: +{over_val} OVER TARGET"
        else:
            text_str = f"{int(self.display_val)} / {self.target_val}"
            
        # 文字居中
        self.create_text(w/2, h/2, text=text_str, fill=text_col, font=font_style)

    def _on_resize(self, event):
        """窗口大小改变时重绘"""
        self.update_view()


# ==========================================
# 2. 测试主程序 (独立运行入口)
# ==========================================
class StandaloneTestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 窗口设置
        self.title("Game Focus Bar - Component Test")
        self.geometry("600x450")
        ctk.set_appearance_mode("Dark") # 默认深色
        
        # 布局配置
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 主容器
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- 标题 ---
        self.lbl_title = ctk.CTkLabel(self.frame, text="POMODORO HUD UI", font=("Arial", 20, "bold"))
        self.lbl_title.pack(pady=(20, 10))
        
        # --- 实例化进度条组件 ---
        # 目标值设为 60
        self.hud_bar = GameFocusBar(self.frame, width=500, height=50, target_val=60)
        self.hud_bar.pack(fill="x", padx=30, pady=20)
        
        # --- 控制区域 ---
        self.ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=30, pady=20)
        
        # 滑块说明
        self.lbl_info = ctk.CTkLabel(self.ctrl_frame, text="Drag to Simulate Progress (Target: 60)")
        self.lbl_info.pack(pady=5)
        
        # 模拟滑块：范围 0 到 100 (故意超过 60 以测试变色)
        self.slider = ctk.CTkSlider(
            self.ctrl_frame, 
            from_=0, 
            to=100, 
            number_of_steps=100, 
            command=self.on_slider_change
        )
        self.slider.set(0)
        self.slider.pack(fill="x", pady=10)
        
        # 主题切换按钮
        self.btn_theme = ctk.CTkButton(
            self.ctrl_frame, 
            text="Toggle Light/Dark Mode", 
            command=self.toggle_theme,
            height=40
        )
        self.btn_theme.pack(pady=20)
        
        # 说明文字
        instructions = (
            "Test Guide:\n"
            "1. Drag slider to see smooth animation.\n"
            "2. Drag past 60 to see 'Red Alert' warning state.\n"
            "3. Click Toggle Theme to test auto-adaptation.\n"
            "4. Resize window to test responsiveness."
        )
        self.lbl_instr = ctk.CTkLabel(self.frame, text=instructions, text_color="gray", justify="left")
        self.lbl_instr.pack(side="bottom", pady=20)

    def on_slider_change(self, value):
        # 将滑块的值传递给进度条
        self.hud_bar.set_progress(value)

    def toggle_theme(self):
        # 切换深浅模式
        current = ctk.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        
        # 强制重绘组件以应用新颜色
        # (因为 Canvas 绘图不是原生组件，需要手动触发一次 update)
        self.hud_bar.update_view()

if __name__ == "__main__":
    app = StandaloneTestApp()
    app.mainloop()