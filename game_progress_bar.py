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
            "light": {
                "bg": "#e0e0e0",             # 空槽背景
                "border": "#bbbbbb",         # 边框
                "fill_normal": "#007AFF",    # 正常进度 (iOS蓝)
                "fill_over": "#FF3B30",      # 超额警示 (红色)
                "text": "#333333",           # 文字颜色
                "segment": "#ffffff"         # 分隔线颜色
            },
            "dark": {
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
        try:
            from ctk_theme_config import ThemeManager
            mode = ThemeManager.get_mode() # "light" or "dark" (lowercase)
        except ImportError:
            mode = ctk.get_appearance_mode().lower()

        # Fallback if mode not found
        if mode not in self.colors: mode = "dark"
        return self.colors[mode][key]

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
        # 如果还没渲染出来(初始化时)，用传入的默认宽高
        if w <= 1: w, h = self.w, self.h
        
        # "Minimize Border": Minimal padding
        pad_x, pad_y = 1, 1 
        cut = int(h / 3) # 斜角大小随高度变化
        
        bg_coords = self._draw_hud_shape(pad_x, pad_y, w-pad_x, h-pad_y, cut)
        # Border width reduced to 1
        self.create_polygon(bg_coords, fill=bg_col, outline=border_col, width=1)

        # 3. 绘制进度条 (填充)
        if self.target_val > 0 and self.display_val > 0:
            # 计算进度比例 (最大限制为 1.0，即填满整个槽，超额时只变色不爆框)
            ratio = min(1.0, self.display_val / self.target_val)
            fill_width = (w - 2 * pad_x) * ratio
            
            # 只有当宽度足够时才绘制
            if fill_width > 3:
                # 只有当填充满时，才显示右侧的斜角，否则是垂直边缘
                if ratio >= 0.99:
                    fill_coords = self._draw_hud_shape(pad_x+1, pad_y+1, pad_x+fill_width-1, h-pad_y-1, cut)
                else:
                    # 未满时，右边是直的 (带一点倾斜更好看)
                    slant = 3 # 内部小倾斜
                    fill_coords = [
                        pad_x+1, pad_y+1,
                        pad_x+fill_width, pad_y+1,
                        pad_x+fill_width-slant, h-pad_y-1,
                        pad_x+1, h-pad_y-1
                    ]
                
                self.create_polygon(fill_coords, fill=fill_col, outline="")
                
                # 4. 绘制分段线 (装饰效果，增加科技感)
                # 每 10% 画一条细线
                for i in range(1, 10):
                    seg_x = pad_x + ((w - 2 * pad_x) * (i/10))
                    if seg_x < (pad_x + fill_width - 3): # 只在填充区域内画
                        # 稍微倾斜的分隔线
                        self.create_line(seg_x, pad_y+1, seg_x - 1, h-pad_y-1, fill=seg_col, width=1, stipple="gray50")

        # 5. 绘制文字信息 (HUD 数据)
        # 尝试加载字体，如果失败使用默认
        font_name = "Arial"
        # 检查系统中是否有 Impact (Windows常见)
        try:
            if "Impact" in ctk.FontManager.load_font_dict():
                font_name = "Impact"
        except:
            pass
            
        font_style = (font_name, 11) # Reduced font size for smaller bar
        
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
