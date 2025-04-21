# character.py
# 角色实体类，用于管理玩家和AI的移动、动画和交互

from typing import Tuple, Dict, List
from .sprite_models import SpriteAnimation, IsometricProjection

class Character:
    """角色实体类，支持2.5D像素风格的移动和动画"""
    
    def __init__(self, name: str, position: Tuple[int, int, int], sprite_config: Dict):
        self.name = name
        self.position = list(position)  # [x, y, z]
        self.velocity = [0, 0, 0]  # 移动速度向量
        self.facing = 0  # 朝向角度（0-360度）
        self.state = 'idle'  # 当前状态
        
        # 角色属性
        self.level = 1
        self.experience = 0
        self.health = 100
        self.stamina = 100
        self.inventory = []
        
        # 动画系统
        self.sprite = SpriteAnimation(
            sprite_config['spritesheet'],
            sprite_config['frame_size'],
            frames_per_state=8  # 更多帧数以实现更流畅的动画
        )
        
        # 扩展动画状态
        self.sprite.animation_states.update({
            'walk': slice(8, 16),
            'run': slice(16, 24),
            'interact': slice(24, 32),
            'combat': slice(32, 40)
        })
        
        # 碰撞检测
        self.collision_radius = 16
        
    def update(self, delta_time: float):
        """更新角色状态"""
        # 更新位置
        for i in range(3):
            self.position[i] += self.velocity[i] * delta_time
        
        # 更新动画
        if any(self.velocity):
            self.state = 'walk' if sum(abs(v) for v in self.velocity) < 5 else 'run'
        else:
            self.state = 'idle'
        
        self.sprite.update_animation(self.state)
        
        # 恢复体力
        if self.stamina < 100:
            self.stamina = min(100, self.stamina + 5 * delta_time)
    
    def move(self, direction: Tuple[float, float]):
        """移动角色"""
        speed = 5.0 if self.state == 'run' else 3.0
        self.velocity[0] = direction[0] * speed
        self.velocity[1] = direction[1] * speed
        
        # 更新朝向
        if any(direction):
            self.facing = math.degrees(math.atan2(direction[1], direction[0])) % 360
    
    def interact(self, target):
        """与目标互动"""
        self.state = 'interact'
        self.sprite.update_animation('interact')
    
    def enter_combat(self):
        """进入战斗状态"""
        self.state = 'combat'
        self.sprite.update_animation('combat')
    
    def get_screen_position(self) -> Tuple[int, int]:
        """获取屏幕坐标"""
        return IsometricProjection.to_screen(*self.position)
    
    def collides_with(self, other) -> bool:
        """检测与其他实体的碰撞"""
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < (self.collision_radius + other.collision_radius)