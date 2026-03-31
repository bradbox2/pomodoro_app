# pygame_pomodoro_ui_example.py
# 使用Pygame制作界面，与Tkinter最大的不同在于：您不再是“放置”组件，而是在一块画布上“绘制”一切。这给了您无限的自由度。
#  Pygame不能直接显示文字。您需要先用 pygame.font.Font() 创建一个字体对象，然后调用它的 .render() 方法将文字渲染成一个可以“画”在屏幕上的图形。这虽然比Tkinter复杂，但也意味着您可以对文字的位置、颜色、大小、甚至旋转进行像素级的精确控制




import pygame
import sys
import os

# --- Initialization ---
pygame.init()
pygame.font.init()

# --- Screen Settings ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 520
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("FocusFlow (Pygame UI Demo)")

# --- Colors ---
WHITE = (255, 255, 255)
TEXT_COLOR = (42, 157, 143)
SHADOW_COLOR = (231, 111, 81, 150) # With alpha for transparency

# --- Font Loading ---
# Try to load a cool font, fall back to default if not found
try:
    # It's better to provide a path to a .ttf file in your project
    # For this example, we'll try a common system font.
    timer_font = pygame.font.SysFont("Arial Black", 60)
    button_font = pygame.font.SysFont("Arial", 20, bold=True)
except:
    timer_font = pygame.font.Font(None, 80)
    button_font = pygame.font.Font(None, 30)

# --- Asset Loading ---
# In a real project, put these in your images folder
# For this demo, we create placeholder surfaces
try:
    # This assumes you have a 'background.png' in an 'images' folder
    # background_image = pygame.image.load(os.path.join("images", "background.png")).convert()
    # As a fallback, we'll just create a color
    background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    background.fill((255, 253, 247)) # A light yellow, similar to YELLOW in your config
except:
    background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    background.fill((255, 253, 247))


class CoolPygameButton:
    """A custom, beautiful button class for Pygame."""
    def __init__(self, x, y, width, height, text, command):
        self.rect = pygame.Rect(x, y, width, height)
        self.shadow_rect = pygame.Rect(x + 4, y + 4, width, height)
        self.text = text
        self.command = command
        self.is_hovered = False
        self.is_pressed = False

        # Colors
        self.normal_color = (231, 111, 81) # A nice orange-red
        self.hover_color = (244, 162, 97) # A lighter orange
        self.pressed_color = (233, 196, 106) # A sandy yellow
        
        self.text_surface = button_font.render(self.text, True, WHITE)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered and event.button == 1:
                self.is_pressed = True
        
        if event.type == pygame.MOUSEBUTTONUP:
            if self.is_hovered and self.is_pressed and event.button == 1:
                if self.command:
                    self.command()
            self.is_pressed = False
            
    def draw(self, surface):
        # Draw shadow
        pygame.draw.rect(surface, SHADOW_COLOR, self.shadow_rect, border_radius=15)

        # Determine button color
        color = self.normal_color
        if self.is_hovered:
            color = self.hover_color
        if self.is_pressed:
            color = self.pressed_color
        
        # Determine position based on press state
        top = self.rect.top
        text_center = self.text_rect.center
        if self.is_pressed and self.is_hovered:
            top += 2
            text_center = (self.text_rect.centerx, self.text_rect.centery + 2)


        current_rect = pygame.Rect(self.rect.left, top, self.rect.width, self.rect.height)
        pygame.draw.rect(surface, color, current_rect, border_radius=12)
        
        # Draw text
        text_surface = button_font.render(self.text, True, WHITE)
        surface.blit(text_surface, text_surface.get_rect(center=text_center))

# --- Button and Timer Setup ---
def start_button_action():
    print("Start Button Clicked!")

def analysis_button_action():
    print("Analysis Button Clicked!")

start_button = CoolPygameButton(
    (SCREEN_WIDTH - 240) // 2, 350, 110, 50, "Start", start_button_action
)
analysis_button = CoolPygameButton(
    (SCREEN_WIDTH - 240) // 2 + 130, 350, 110, 50, "Analysis", analysis_button_action
)

buttons = [start_button, analysis_button]
timer_text = "25:00"

# --- Main Game Loop ---
running = True
while running:
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        for button in buttons:
            button.handle_event(event)

    # Drawing
    screen.blit(background, (0, 0))

    # Draw Title
    title_surf = timer_font.render("FocusFlow", True, TEXT_COLOR)
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 80)))

    # Draw Timer Text
    timer_surf = timer_font.render(timer_text, True, TEXT_COLOR)
    timer_rect = timer_surf.get_rect(center=(SCREEN_WIDTH // 2, 220))
    screen.blit(timer_surf, timer_rect)
    
    # Draw Buttons
    for button in buttons:
        button.draw(screen)

    # Update the display
    pygame.display.flip()

pygame.quit()
sys.exit()

