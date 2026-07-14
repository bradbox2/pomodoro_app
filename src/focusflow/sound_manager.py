# sound_manager.py
import pygame
import os
import random

class SoundManager:
    """
    专门负责音频播放的服务类。
    """
    def __init__(self, sound_dir):
        self.sound_dir = sound_dir
        self.music_dir = os.path.join(self.sound_dir, "music")
        
        # 1. 自定义事件ID
        self.MUSIC_END_EVENT = pygame.USEREVENT + 1 

        # 2. 初始化
        try:
            # Pygame 事件队列需要 display 模块初始化才能工作
            if not pygame.display.get_init():
                pygame.display.init()

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            
            # 设置结束事件
            pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)
            
        except Exception as e:
            print(f"SoundManager Init Error: {e}")

        # 3. 资源预加载
        self.dida_sound = None
        self.end_sound = None
        self._load_fixed_sounds()
        
        # 4. 状态标记
        self.current_mode = "mute"
        self.last_music = None 

    def _load_fixed_sounds(self):
        dida_path = os.path.join(self.sound_dir, "dida.mp3")
        if not os.path.exists(dida_path):
            dida_path = os.path.join(self.sound_dir, "dida.wav")
        
        if os.path.exists(dida_path):
            try:
                self.dida_sound = pygame.mixer.Sound(dida_path)
                self.dida_sound.set_volume(0.6)
            except Exception as e:
                print(f"Failed to load dida: {e}")

        dong_path = os.path.join(self.sound_dir, "dong.mp3")
        if os.path.exists(dong_path):
            try:
                self.end_sound = pygame.mixer.Sound(dong_path)
            except:
                pass

    def play_mode(self, mode):
        """切换播放模式"""
        # 1. 切换前先彻底停止当前的，并清理事件
        self.stop_bg_sound() 
        
        # 2. 更新状态
        self.current_mode = mode

        if mode == 'dida':
            if self.dida_sound:
                self.dida_sound.play(loops=-1)
        
        elif mode == 'music':
            self._play_random_music()
            
        elif mode == 'mute':
            pass 
    
    def pause_sound(self):
        """暂停当前声音（保持模式）"""
        if self.current_mode == 'dida':
            if self.dida_sound:
                self.dida_sound.stop()
        elif self.current_mode == 'music':
            pygame.mixer.music.pause()
    
    def resume_sound(self):
        """恢复之前的声音"""
        if self.current_mode == 'dida':
            if self.dida_sound:
                # Sound objects don't support pause well, just restart check
                self.dida_sound.play(loops=-1)
        elif self.current_mode == 'music':
            # Simply unpause. If it wasn't playing, unpause does nothing.
            # If it was paused, it resumes.
            pygame.mixer.music.unpause()
            
            # Fallback: if music is NOT busy (stopped) and we expect it to be playing,
            # we might want to restart? But user specifically requested RESUME.
            # If standard unpause fails to produce sound (e.g. it was fully stopped), 
            # we should leave it or logic might restart song. 
            # For now, blindly unpause is safer for "resume" behavior.
            if not pygame.mixer.music.get_busy():
                 # Only if really stopped, maybe play? 
                 # But let's respect "resume" strictly.
                 pass

    def _play_random_music(self):
        """内部方法：随机播放一首"""
        if not os.path.exists(self.music_dir): return
        mp3s = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
        if not mp3s: return
            
        # 避免立即重复播放同一首 (如果只有一首则无法避免)
        candidates = mp3s
        if self.last_music and len(mp3s) > 1:
            candidates = [m for m in mp3s if m != self.last_music]
        
        chosen = random.choice(candidates)
        self.last_music = chosen # 记录本次播放

        full_path = os.path.join(self.music_dir, chosen)
        
        try:
            pygame.mixer.music.load(full_path)
            # loops=0: 播完一次后触发 MUSIC_END_EVENT
            pygame.mixer.music.play(loops=0)
            print(f"Playing: {chosen}")
        except Exception as e:
            print(f"Music Error: {e}")

    def check_music_events(self):
        """
        检查事件队列，只在真正处于 music 模式时才响应
        """
        # 如果当前不仅不是 music 模式，直接把事件队列清空并返回
        # 这一步是为了双重保险，防止堆积的事件在切换模式后触发
        if self.current_mode != 'music':
            pygame.event.clear(self.MUSIC_END_EVENT)
            return

        for event in pygame.event.get():
            if event.type == self.MUSIC_END_EVENT:
                # 只有当前确实是 music 模式，且音乐确实停止了，才切下一首
                if self.current_mode == 'music':
                    print("Song finished naturally, next song...")
                    self._play_random_music()

    def play_end_sound(self):
        """播放结束音"""
        # 播放结束音时，我们也希望背景音立刻停止
        self.stop_bg_sound()
        if self.end_sound:
            self.end_sound.play()

    def stop_bg_sound(self):
        """
        【关键修复】停止背景音。
        """
        # 1. 先将状态改为 mute，这样即使触发了事件，check_music_events 也会忽略它
        self.current_mode = "mute"
        
        # 2. 停止音乐
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        # 3. 【核心】pygame.mixer.music.stop() 会产生一个 MUSIC_END_EVENT。
        # 我们必须手动把这个“假”信号从队列里清除掉，防止它触发切歌。
        pygame.event.clear(self.MUSIC_END_EVENT)

        # 4. 停止滴答声
        if self.dida_sound:
            self.dida_sound.stop()