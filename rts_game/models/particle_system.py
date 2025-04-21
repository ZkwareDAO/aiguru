# particle_system.py
# 粒子效果系统

import pygame
import random
from typing import List, Tuple, Dict, Any

class Particle:
    """单个粒子类"""
    def __init__(self, position: Tuple[int, int], velocity: Tuple[float, float], 
                 color: Tuple[int, int, int], size: int, life: int):
        self.position = list(position)  # 位置 [x, y]
        self.velocity = list(velocity)  # 速度 [vx, vy]
        self.color = color              # 颜色 (r, g, b)
        self.size = size                # 大小
        self.life = life                # 生命周期
        self.max_life = life            # 最大生命周期
    
    def update(self):
        """更新粒子状态"""
        # 更新位置
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]
        
        # 应用重力或其他物理效果
        self.velocity[1] += 0.1  # 简单重力
        
        # 减少生命周期
        self.life -= 1
        
        # 随着生命周期减少，粒子变小
        self.size = max(1, int(self.size * (self.life / self.max_life)))
    
    def draw(self, surface: pygame.Surface, camera_offset: Tuple[int, int]):
        """绘制粒子"""
        # 计算屏幕位置
        screen_x = int(self.position[0] + camera_offset[0])
        screen_y = int(self.position[1] + camera_offset[1])
        
        # 根据生命周期调整透明度
        alpha = int(255 * (self.life / self.max_life))
        
        # 创建临时表面以支持透明度
        particle_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, (*self.color, alpha), (self.size, self.size), self.size)
        
        # 绘制到主表面
        surface.blit(particle_surface, (screen_x - self.size, screen_y - self.size))

class ParticleSystem:
    """粒子系统类，管理多个粒子效果"""
    def __init__(self):
        self.particle_groups: Dict[str, List[Particle]] = {}
    
    def create_particles(self, group_id: str, position: Tuple[int, int], 
                         count: int, color: Tuple[int, int, int], 
                         size_range: Tuple[int, int], life_range: Tuple[int, int],
                         velocity_range: Tuple[float, float]):
        """创建一组粒子"""
        if group_id not in self.particle_groups:
            self.particle_groups[group_id] = []
        
        for _ in range(count):
            # 随机化粒子参数
            size = random.randint(size_range[0], size_range[1])
            life = random.randint(life_range[0], life_range[1])
            
            # 随机方向的速度
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(velocity_range[0], velocity_range[1])
            velocity = (speed * math.cos(angle), speed * math.sin(angle))
            
            # 创建粒子并添加到组
            particle = Particle(position, velocity, color, size, life)
            self.particle_groups[group_id].append(particle)
    
    def update(self):
        """更新所有粒子组"""
        for group_id in list(self.particle_groups.keys()):
            # 更新每个粒子
            self.particle_groups[group_id] = [p for p in self.particle_groups[group_id] if p.life > 0]
            for particle in self.particle_groups[group_id]:
                particle.update()
            
            # 如果组为空，删除它
            if not self.particle_groups[group_id]:
                del self.particle_groups[group_id]
    
    def draw(self, surface: pygame.Surface, camera_offset: Tuple[int, int]):
        """绘制所有粒子"""
        for group_id, particles in self.particle_groups.items():
            for particle in particles:
                particle.draw(surface, camera_offset)

# 预定义的粒子效果
def create_build_effect(particle_system: ParticleSystem, position: Tuple[int, int]):
    """创建建筑施工效果"""
    particle_system.create_particles(
        f"build_{position[0]}_{position[1]}",
        position,
        count=20,
        color=(150, 150, 150),  # 灰色粉尘
        size_range=(2, 4),
        life_range=(30, 60),
        velocity_range=(0.5, 1.5)
    )

def create_resource_gather_effect(particle_system: ParticleSystem, position: Tuple[int, int], resource_type: str):
    """创建资源收集效果"""
    # 根据资源类型选择颜色
    color = {
        'gold': (255, 215, 0),    # 金色
        'wood': (139, 69, 19),    # 棕色
        'stone': (169, 169, 169), # 灰色
        'food': (0, 128, 0)       # 绿色
    }.get(resource_type, (255, 255, 255))
    
    particle_system.create_particles(
        f"gather_{resource_type}_{position[0]}_{position[1]}",
        position,
        count=15,
        color=color,
        size_range=(1, 3),
        life_range=(20, 40),
        velocity_range=(0.3, 1.0)
    )

def create_combat_effect(particle_system: ParticleSystem, position: Tuple[int, int], effect_type: str):
    """创建战斗效果"""
    if effect_type == 'hit':
        # 击中效果
        particle_system.create_particles(
            f"hit_{position[0]}_{position[1]}",
            position,
            count=15,
            color=(255, 0, 0),  # 红色
            size_range=(2, 4),
            life_range=(10, 20),
            velocity_range=(1.0, 2.0)
        )
        # 添加溅血效果
        particle_system.create_particles(
            f"blood_{position[0]}_{position[1]}",
            position,
            count=8,
            color=(139, 0, 0),  # 深红色
            size_range=(1, 2),
            life_range=(15, 25),
            velocity_range=(0.8, 1.5)
        )
    elif effect_type == 'magic':
        # 魔法效果
        particle_system.create_particles(
            f"magic_{position[0]}_{position[1]}",
            position,
            count=30,
            color=(0, 191, 255),  # 蓝色
            size_range=(2, 4),
            life_range=(40, 60),
            velocity_range=(0.2, 0.8)
        )
        # 添加魔法光环
        particle_system.create_particles(
            f"magic_aura_{position[0]}_{position[1]}",
            position,
            count=20,
            color=(147, 112, 219),  # 紫色
            size_range=(1, 3),
            life_range=(30, 50),
            velocity_range=(0.1, 0.4)
        )
    elif effect_type == 'explosion':
        # 爆炸效果
        particle_system.create_particles(
            f"explosion_{position[0]}_{position[1]}",
            position,
            count=50,
            color=(255, 165, 0),  # 橙色
            size_range=(4, 8),
            life_range=(15, 30),
            velocity_range=(2.0, 4.0)
        )
        # 添加烟雾效果
        particle_system.create_particles(
            f"smoke_{position[0]}_{position[1]}",
            position,
            count=30,
            color=(128, 128, 128),  # 灰色
            size_range=(3, 6),
            life_range=(40, 60),
            velocity_range=(0.5, 1.0)
        )
    elif effect_type == 'heal':
        # 治疗效果
        particle_system.create_particles(
            f"heal_{position[0]}_{position[1]}",
            position,
            count=25,
            color=(124, 252, 0),  # 亮绿色
            size_range=(2, 4),
            life_range=(30, 50),
            velocity_range=(0.3, 0.8)
        )
    elif effect_type == 'buff':
        # 增益效果
        particle_system.create_particles(
            f"buff_{position[0]}_{position[1]}",
            position,
            count=20,
            color=(255, 215, 0),  # 金色
            size_range=(1, 3),
            life_range=(40, 60),
            velocity_range=(0.2, 0.6)
        )

import math  # 添加缺少的导入