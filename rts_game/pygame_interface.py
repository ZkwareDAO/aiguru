# pygame_interface.py
# Pygame界面实现

import pygame
import sys
import os
import time
import math
import opensimplex
from game import Game
from models.player import Player
from models.faction import Faction
from models.city import City
from models.building import Building, Farm, Mine, LumberMill, Barracks, Castle
from models.sprite_models import SpriteAnimation, IsometricProjection, BUILDING_SPRITES, UNIT_SPRITES, TERRAIN_SPRITES
from models.particle_system import ParticleSystem, create_build_effect, create_resource_gather_effect, create_combat_effect

# 初始化pygame
pygame.init()

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# 势力颜色映射
FACTION_COLORS = {
    0: (255, 0, 0),    # 红色
    1: (0, 0, 255),    # 蓝色
    2: (0, 255, 0),    # 绿色
    3: (255, 255, 0),  # 黄色
    4: (255, 0, 255),  # 紫色
    5: (0, 255, 255),  # 青色
    6: (128, 0, 0),    # 深红色
    7: (0, 0, 128),    # 深蓝色
}

class PygameInterface:
    """Pygame界面类，负责游戏的图形界面和交互"""
    
    def __init__(self, game):
        self.game = game
        self.screen = pygame.display.set_mode((1024, 768))
        self.clock = pygame.time.Clock()
        self.sprites = {
            'buildings': {},
            'units': {},
            'terrain': {}
        }
        self.load_sprites()
        self.camera_offset = [0, 0]
        self.tile_size = 32
        pygame.display.set_caption("个体化RTS游戏")
        
        # 教学系统相关属性
        self.tutorial_active = True
        self.current_step = 0
        self.tutorial_steps = [
            {'text': '欢迎来到战略游戏！使用WASD移动视角', 'pos': (100, 100)},
            {'text': '点击建筑查看详细信息，右键进行建造', 'pos': (100, 150)},
            {'text': '拖动鼠标框选多个单位进行编队', 'pos': (100, 200)}
        ]
        self.guide_font = pygame.font.Font(None, 28)
        self.highlight_rect = None
        
        # 游戏状态
        self.running = True
        self.selected_city = None
        self.selected_player = self.game.players[0]  # 设置默认玩家
        
        # 地图参数
        self.map_width = 800
        self.map_height = 600
        self.map_offset_x = 20
        self.map_offset_y = 20
        self.city_radius = 15
        
        # 界面元素
        self.font = pygame.font.SysFont(None, 24)
        self.title_font = pygame.font.SysFont(None, 32)
        
        # 粒子系统
        self.particle_system = ParticleSystem()
    
    def generate_perlin_noise(self, width, height):
        """生成柏林噪声地图"""
        scale = 10.0
        octaves = 6
        persistence = 0.5
        lacunarity = 2.0
        
        noise_map = [[0.0]*height for _ in range(width)]
        seed = int(time.time())
        generator = opensimplex.OpenSimplex(seed)
        
        for i in range(width):
            for j in range(height):
                noise_val = 0.0
                amplitude = 1.0
                frequency = 1.0
                
                for _ in range(octaves):
                    sample_x = i / scale * frequency
                    sample_y = j / scale * frequency
                    
                    noise_val += amplitude * generator.noise2(sample_x, sample_y)
                    amplitude *= persistence
                    frequency *= lacunarity
                
                noise_map[i][j] = noise_val
        
        return noise_map

    def generate_terrain_surface(self):
        """生成动态地形表面"""
        map_width = 800
        map_height = 600
        self.terrain_surface = pygame.Surface((map_width, map_height)).convert_alpha()
        self.terrain_surface.fill((0,0,0,0))
    
        # 使用Perlin噪声生成地形高度图
        noise_map = self.generate_perlin_noise(map_width//self.tile_size + 1, map_height//self.tile_size + 1)
    
        # 加载多种地形精灵
        grass_anim = self.sprites['terrain']['grass']
        water_anim = self.sprites['terrain']['water']
        mountain_anim = self.sprites['terrain']['mountain']
    
        for x in range(len(noise_map)):
            for y in range(len(noise_map[x])):
                height = noise_map[x][y]
    
                # 根据高度选择地形类型
                if height < 0.3:
                    anim = water_anim
                elif height > 0.7:
                    anim = mountain_anim
                else:
                    anim = grass_anim
    
                # 动态选择地形变种
                variant = int((height * 100) % anim.animation_states['idle'].stop)
                frame = anim.frames[variant]
    
                screen_pos = IsometricProjection.to_screen(x, y)
                self.terrain_surface.blit(frame, screen_pos)

    def load_sprites(self):
        """加载所有精灵资源"""
        # 加载建筑精灵
        for building_type, config in BUILDING_SPRITES.items():
            self.sprites['buildings'][building_type] = SpriteAnimation(
                config['spritesheet'],
                config['frame_size'],
                config['animations']
            )

        # 加载单位精灵
        for unit_type, config in UNIT_SPRITES.items():
            self.sprites['units'][unit_type] = SpriteAnimation(
                config['spritesheet'],
                config['frame_size'],
                config['animations']
            )

        # 加载地形精灵
        for terrain_type, config in TERRAIN_SPRITES.items():
            self.sprites['terrain'][terrain_type] = SpriteAnimation(
                config['spritesheet'],
                config['frame_size'],
                config['animations']
            )

    def load_resources(self):
        """加载游戏资源"""
        self.generate_terrain_surface()
        # 加载其他资源（音效等）
        # 这里保留未来扩展空间
    
    def run(self):
        """运行游戏主循环"""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            pygame.time.delay(30)  # 简单的帧率控制
        
        pygame.quit()
        sys.exit()
    
    def handle_events(self):
        """处理用户输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 处理教学步骤点击
                if self.tutorial_active and event.button == 1:
                    self.current_step += 1
                    if self.current_step >= len(self.tutorial_steps):
                        self.tutorial_active = False
                
                # 处理鼠标点击
                if event.button == 1:  # 左键点击
                    self.handle_mouse_click(event.pos)
            
            elif event.type == pygame.KEYDOWN:
                # 处理键盘输入
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    # 进入下一回合
                    if not self.game.game_over:
                        self.game.turn += 1
                        self.game.process_turn()
                        if self.game.turn >= self.game.max_turns:
                            self.game.end_game()
    
    def handle_mouse_click(self, pos):
        """处理鼠标点击事件"""
        # 检查是否点击了城池
        for city in self.game.cities:
            city_pos = self.map_to_screen(city.location)
            distance = ((pos[0] - city_pos[0]) ** 2 + (pos[1] - city_pos[1]) ** 2) ** 0.5
            if distance <= self.city_radius:
                self.selected_city = city
                return
        
        # 如果点击了空白区域，取消选择
        self.selected_city = None
    
    def render(self):
        """渲染游戏画面"""
        self.draw_objects()
        self.draw_ui()
        pygame.display.flip()

    def update(self):
        """更新游戏状态"""
        # 处理相机移动
        self.handle_camera()
        
        # 更新精灵动画
        self.update_animations()
        
        # 更新粒子系统
        self.particle_system.update()
        
        # 更新游戏逻辑
        # 这里可以添加其他游戏状态的更新逻辑
    
    def update_animations(self):
        """更新所有精灵动画"""
        current_time = pygame.time.get_ticks()
        
        # 更新建筑动画
        for building_type, animation in self.sprites['buildings'].items():
            config = BUILDING_SPRITES.get(building_type, {})
            animation_speed = config.get('animation_speed', 10)
            
            if current_time - animation.last_update > 1000 // animation_speed:
                animation.current_frame = (animation.current_frame + 1) % len(animation.frames)
                animation.last_update = current_time
        
        # 更新单位动画
        for unit_type, animation in self.sprites['units'].items():
            config = UNIT_SPRITES.get(unit_type, {})
            animation_speed = config.get('animation_speed', 12)
            
            if current_time - animation.last_update > 1000 // animation_speed:
                animation.current_frame = (animation.current_frame + 1) % len(animation.frames)
                animation.last_update = current_time

    def draw_objects(self):
        # 清空屏幕并设置基础环境光
        self.screen.fill((30, 30, 30))
        
        # 使用预生成的静态地形表面
        if not hasattr(self, 'terrain_surface'):
            self.generate_terrain_surface()
        self.screen.blit(self.terrain_surface, (0, 0))
        
        # 绘制势力范围（带有脉动效果）
        pulse = (math.sin(pygame.time.get_ticks() * 0.003) + 1) * 0.5  # 0到1的脉动值
        for faction in self.game.factions:
            for coord in faction.territory:
                screen_pos = self.map_to_screen(coord)
                base_alpha = 80 if faction == self.selected_player.faction else 40
                alpha = int(base_alpha * (0.8 + 0.2 * pulse))
                color = (*FACTION_COLORS[faction.id], alpha)
                pygame.draw.circle(self.screen, color, screen_pos, 18, 4)
        
        # 绘制动态边界效果（带有闪烁）
        if pygame.time.get_ticks() % 1000 < 500:
            for border in self.game.get_territory_borders():
                for point in border:
                    pos = self.map_to_screen(point)
                    glow_alpha = int(180 * pulse)
                    pygame.draw.circle(self.screen, (255,255,255,glow_alpha), pos, 3)
        
        # 分层渲染列表（使用改进的深度排序）
        render_list = []
        
        # 收集所有动态对象并计算其深度值
        for city in self.game.cities:
            # 主城堡
            base_x, base_y = city.location
            screen_pos = IsometricProjection.to_screen(
                base_x, base_y, 
                BUILDING_SPRITES['castle']['elevation']
            )
            # 使用改进的深度计算（考虑x、y、z坐标）
            depth = base_x + base_y * 2 + BUILDING_SPRITES['castle']['elevation'] * 0.5
            render_list.append({
                'depth': depth,
                'type': 'building',
                'key': 'castle',
                'pos': (screen_pos[0] + self.camera_offset[0], 
                       screen_pos[1] + self.camera_offset[1]),
                'base_pos': (base_x, base_y)
            })
            
            # 添加城市的其他建筑
            if hasattr(city, 'buildings') and city.buildings:
                for i, building in enumerate(city.buildings):
                    offset_x = base_x + (i % 3) - 1
                    offset_y = base_y + (i // 3) + 1
                    
                    building_type = building.__class__.__name__.lower()
                    if building_type in self.sprites['buildings']:
                        screen_pos = IsometricProjection.to_screen(
                            offset_x, offset_y, 
                            BUILDING_SPRITES[building_type]['elevation']
                        )
                        depth = offset_x + offset_y * 2 + BUILDING_SPRITES[building_type]['elevation'] * 0.5
                        render_list.append({
                            'depth': depth,
                            'type': 'building',
                            'key': building_type,
                            'pos': (screen_pos[0] + self.camera_offset[0], 
                                   screen_pos[1] + self.camera_offset[1]),
                            'base_pos': (offset_x, offset_y)
                        })
        
        # 使用改进的深度排序
        render_list.sort(key=lambda x: x['depth'])
        
        # 创建光照表面
        light_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        
        # 渲染对象并添加动态光影
        for item in render_list:
            obj_type = item['type']
            obj_key = item['key']
            pos = item['pos']
            base_pos = item['base_pos']
            
            if obj_type == 'building':
                animation = self.sprites['buildings'][obj_key]
                animation.update_animation('idle')
                current_frame = animation.current_frame % len(animation.frames)
                frame = animation.frames[current_frame]
                
                # 添加动态阴影
                shadow_pos = (pos[0] + 10, pos[1] + 5)  # 阴影偏移
                shadow_surface = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
                shadow_surface.fill((0, 0, 0, 40))  # 半透明黑色
                self.screen.blit(shadow_surface, shadow_pos)
                
                # 绘制建筑
                self.screen.blit(frame, pos)
                
                # 添加环境光效果
                day_cycle = (pygame.time.get_ticks() % 24000) / 24000  # 24秒一个昼夜循环
                ambient_light = 0.7 + 0.3 * math.sin(day_cycle * 2 * math.pi)
                light_color = (255, 255, 200, int(40 * ambient_light))
                pygame.draw.circle(light_surface, light_color, 
                                 (pos[0] + frame.get_width()//2, 
                                  pos[1] + frame.get_height()//2), 
                                 100)
                
                # 为特定建筑添加资源收集效果
                if self.game.turn % 30 == 0:
                    if obj_key == 'farm':
                        create_resource_gather_effect(self.particle_system, pos, 'food')
                    elif obj_key == 'mine':
                        create_resource_gather_effect(self.particle_system, pos, 'gold')
                    elif obj_key == 'lumbermill':
                        create_resource_gather_effect(self.particle_system, pos, 'wood')
            
            elif obj_type == 'unit':
                animation = self.sprites['units'][obj_key]
                animation.update_animation('idle')
                current_frame = animation.current_frame % len(animation.frames)
                frame = animation.frames[current_frame]
                
                # 添加单位阴影
                shadow_pos = (pos[0] + 5, pos[1] + 3)
                shadow_surface = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
                shadow_surface.fill((0, 0, 0, 30))
                self.screen.blit(shadow_surface, shadow_pos)
                
                # 绘制单位
                self.screen.blit(frame, pos)
        
        # 应用光照效果
        self.screen.blit(light_surface, (0, 0))
        
        # 渲染粒子效果
        self.particle_system.draw(self.screen, self.camera_offset)
        
        pygame.display.flip()
        
    def handle_camera(self):
        keys = pygame.key.get_pressed()
        move_speed = 5
        
        if keys[pygame.K_LEFT]:
            self.camera_offset[0] += move_speed
        if keys[pygame.K_RIGHT]:
            self.camera_offset[0] -= move_speed
        if keys[pygame.K_UP]:
            self.camera_offset[1] += move_speed
        if keys[pygame.K_DOWN]:
            self.camera_offset[1] -= move_speed
    
    def draw_map(self):
        """绘制游戏地图"""
        # 绘制地图边框
        pygame.draw.rect(self.screen, BLACK, 
                         (self.map_offset_x, self.map_offset_y, 
                          self.map_width, self.map_height), 2)
        
        # 绘制城池
        for city in self.game.cities:
            self.draw_city(city)
    
    def draw_city(self, city):
        """绘制城池"""
        # 计算城池在屏幕上的位置
        screen_pos = self.map_to_screen(city.location)
        
        # 确定城池颜色（根据所属势力）
        if city.owner:
            faction_index = self.game.factions.index(city.owner) if city.owner in self.game.factions else 0
            color = FACTION_COLORS.get(faction_index, GRAY)
        else:
            color = GRAY
        
        # 绘制城池圆形
        pygame.draw.circle(self.screen, color, screen_pos, self.city_radius)
        pygame.draw.circle(self.screen, BLACK, screen_pos, self.city_radius, 2)
        
        # 如果是选中的城池，绘制高亮边框
        if city == self.selected_city:
            pygame.draw.circle(self.screen, YELLOW, screen_pos, self.city_radius + 3, 2)
        
        # 绘制城池名称
        name_text = self.font.render(city.name, True, BLACK)
        self.screen.blit(name_text, (screen_pos[0] - name_text.get_width() // 2, 
                                     screen_pos[1] + self.city_radius + 5))
    
    def draw_ui(self):
        """绘制用户界面元素"""
        # 绘制顶部状态栏
        self._draw_status_bar()
        
        # 绘制侧边栏
        self._draw_sidebar()
        
        # 绘制选中城池信息
        if self.selected_city:
            self._draw_selected_city_info()
        
        # 绘制教学提示层
        if self.tutorial_active:
            self._draw_tutorial_overlay()

    def _draw_tutorial_overlay(self):
        """绘制教学提示覆盖层"""
        if self.current_step >= len(self.tutorial_steps):
            return

        # 创建半透明背景
        overlay = pygame.Surface((1024, 768), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))

        # 绘制当前步骤文字
        step = self.tutorial_steps[self.current_step]
        text_surface = self.guide_font.render(step['text'], True, (255, 255, 255))
        overlay.blit(text_surface, step['pos'])

        # 绘制下一步提示
        prompt_text = "点击继续"
        prompt_surface = self.guide_font.render(prompt_text, True, (200, 200, 200))
        overlay.blit(prompt_surface, (400, 650))

        # 绘制到主屏幕
        self.screen.blit(overlay, (0, 0))

    def _draw_status_bar(self):
        """绘制顶部状态栏"""
        status_bar = pygame.Surface((1024, 30), pygame.SRCALPHA)
        status_bar.fill((0, 0, 0, 128))
        
        # 显示当前回合数
        turn_text = self.font.render(f'回合: {self.game.turn}', True, WHITE)
        status_bar.blit(turn_text, (10, 5))
        
        # 显示游戏模式
        mode_text = self.font.render('模式: 战略视图' if self.game.strategic_view else '模式: 战术视图', True, WHITE)
        status_bar.blit(mode_text, (300, 5))
        
        self.screen.blit(status_bar, (0, 0))
    def _draw_tutorial_overlay(self):
        """绘制教学提示层"""
        if self.current_step >= len(self.tutorial_steps):
            return
        
        # 绘制半透明背景
        tutorial_bg = pygame.Surface((600, 250), pygame.SRCALPHA)
        tutorial_bg.fill((0, 0, 0, 200))
        self.screen.blit(tutorial_bg, (50, 500))
        
        # 绘制当前步骤文字
        step = self.tutorial_steps[self.current_step]
        text_surface = self.guide_font.render(step['text'], True, (255, 255, 255))
        self.screen.blit(text_surface, step['pos'])
        
        # 绘制下一步提示
        prompt_text = "点击继续"
        prompt_surface = self.guide_font.render(prompt_text, True, (200, 200, 200))
        self.screen.blit(prompt_surface, (500, 650))
        if self.tutorial_active and self.current_step < len(self.tutorial_steps):
            # 创建半透明背景
            overlay = pygame.Surface((1024, 768), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            
            # 绘制教学步骤
            step = self.tutorial_steps[self.current_step]
            text_surf = self.guide_font.render(step['text'], True, (255, 255, 255))
            overlay.blit(text_surf, step['pos'])
            
            # 绘制高亮区域
            if self.highlight_rect:
                pygame.draw.rect(overlay, (255, 255, 0, 64), self.highlight_rect)
                pygame.draw.rect(overlay, (255, 255, 0), self.highlight_rect, 2)
            
            self.screen.blit(overlay, (0, 0))
    
    def _draw_selected_city_info(self):
        """绘制选中城池的详细信息"""
        if not self.selected_city:
            return
        
        # 信息框基本参数
        info_width = 300
        info_height = 200
        pos = (self.screen.get_width() - info_width - 20, 100)
        
        # 绘制背景框
        pygame.draw.rect(self.screen, (40, 40, 40), (pos[0], pos[1], info_width, info_height))
        pygame.draw.rect(self.screen, WHITE, (pos[0], pos[1], info_width, info_height), 2)
        
        # 显示城池名称
        name_surface = self.title_font.render(self.selected_city.name, True, WHITE)
        self.screen.blit(name_surface, (pos[0]+10, pos[1]+10))
        
        # 显示资源信息
        resources_y = pos[1] + 50
        for resource, amount in self.selected_city.resources.items():
            text = f"{resource}: {amount}"
            res_surface = self.font.render(text, True, WHITE)
            self.screen.blit(res_surface, (pos[0]+10, resources_y))
            resources_y += 30
        
        # 显示所属势力
        faction_text = f"所属: {self.selected_city.owner.name}"
        faction_surface = self.font.render(faction_text, True, FACTION_COLORS[self.selected_city.owner.id % 8])
        self.screen.blit(faction_surface, (pos[0]+10, pos[1]+160))

    def _draw_sidebar(self):
        """绘制右侧信息侧边栏"""
        sidebar_width = 250
        sidebar_rect = pygame.Rect(774, 0, sidebar_width, 768)
        pygame.draw.rect(self.screen, (50, 50, 50), sidebar_rect)
        
        # 绘制侧边栏标题
        title_surface = self.title_font.render("游戏信息", True, WHITE)
        self.screen.blit(title_surface, (784, 20))
    
    def map_to_screen(self, map_pos):
        """将地图坐标转换为屏幕坐标"""
        screen_x = self.map_offset_x + (map_pos[0] / 100) * self.map_width
        screen_y = self.map_offset_y + (map_pos[1] / 100) * self.map_height
        return (int(screen_x), int(screen_y))


def main():
    """主函数"""
    # 创建游戏实例
    max_turns = 50  # 默认回合数
    game = Game(max_turns=max_turns)
    
    # 创建人类玩家
    human_player = game.create_human_player("玩家")
    
    # 创建AI玩家
    for i in range(3):  # 默认3个AI
        ai_name = f"AI-{i+1}"
        game.create_ai_player(ai_name)
    
    # 初始化游戏
    game.initialize_game()
    
    # 创建并运行Pygame界面
    interface = PygameInterface(game)
    interface.run()


if __name__ == "__main__":
    main()