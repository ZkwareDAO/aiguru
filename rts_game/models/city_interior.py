# city_interior.py
# 城池内部空间系统

from typing import Dict, List, Tuple
from .sprite_models import SpriteAnimation, IsometricProjection

class InteriorBuilding:
    """城池内部建筑"""
    def __init__(self, name: str, building_type: str, position: Tuple[int, int], sprite_config: Dict):
        self.name = name
        self.type = building_type
        self.position = position
        self.sprite = SpriteAnimation(
            sprite_config['spritesheet'],
            sprite_config['frame_size']
        )
        self.interaction_radius = 32
        self.is_occupied = False

class NPC:
    """城池内的NPC"""
    def __init__(self, name: str, npc_type: str, position: Tuple[int, int], sprite_config: Dict):
        self.name = name
        self.type = npc_type
        self.position = position
        self.sprite = SpriteAnimation(
            sprite_config['spritesheet'],
            sprite_config['frame_size']
        )
        self.dialog_options = []
        self.shop_inventory = []
        self.daily_schedule = {}

class CityInterior:
    """城池内部空间管理器"""
    def __init__(self, city_name: str, size: Tuple[int, int]):
        self.city_name = city_name
        self.size = size
        self.buildings = []
        self.npcs = []
        self.interaction_points = []
        self.collision_map = [[False] * size[1] for _ in range(size[0])]
        
        # 内部建筑配置
        self.building_configs = {
            'tavern': {
                'name': '酒馆',
                'services': ['招募佣兵', '收集情报'],
                'sprite_config': {
                    'spritesheet': 'assets/spritesheets/buildings/tavern.svg',
                    'frame_size': (64, 64)
                }
            },
            'barracks': {
                'name': '兵营',
                'services': ['训练军队', '升级装备'],
                'sprite_config': {
                    'spritesheet': 'assets/spritesheets/buildings/barracks.svg',
                    'frame_size': (64, 64)
                }
            },
            'market': {
                'name': '市场',
                'services': ['交易物资', '雇佣商队'],
                'sprite_config': {
                    'spritesheet': 'assets/spritesheets/buildings/market.svg',
                    'frame_size': (64, 64)
                }
            }
        }
    
    def add_building(self, building_type: str, position: Tuple[int, int]) -> InteriorBuilding:
        """添加内部建筑"""
        if building_type in self.building_configs:
            config = self.building_configs[building_type]
            building = InteriorBuilding(
                config['name'],
                building_type,
                position,
                config['sprite_config']
            )
            self.buildings.append(building)
            self._update_collision_map(position, True)
            return building
        return None
    
    def add_npc(self, name: str, npc_type: str, position: Tuple[int, int], sprite_config: Dict) -> NPC:
        """添加NPC"""
        npc = NPC(name, npc_type, position, sprite_config)
        self.npcs.append(npc)
        return npc
    
    def get_available_interactions(self, player_pos: Tuple[int, int]) -> List[Dict]:
        """获取玩家当前位置可用的交互选项"""
        available = []
        
        # 检查建筑交互
        for building in self.buildings:
            dx = player_pos[0] - building.position[0]
            dy = player_pos[1] - building.position[1]
            if (dx*dx + dy*dy) <= building.interaction_radius*building.interaction_radius:
                available.append({
                    'type': 'building',
                    'target': building,
                    'actions': self.building_configs[building.type]['services']
                })
        
        # 检查NPC交互
        for npc in self.npcs:
            dx = player_pos[0] - npc.position[0]
            dy = player_pos[1] - npc.position[1]
            if (dx*dx + dy*dy) <= 25:  # 5x5的交互范围
                available.append({
                    'type': 'npc',
                    'target': npc,
                    'actions': ['对话', '交易'] if npc.shop_inventory else ['对话']
                })
        
        return available
    
    def _update_collision_map(self, position: Tuple[int, int], is_blocked: bool):
        """更新碰撞地图"""
        x, y = position
        if 0 <= x < self.size[0] and 0 <= y < self.size[1]:
            self.collision_map[x][y] = is_blocked
    
    def can_move_to(self, position: Tuple[int, int]) -> bool:
        """检查位置是否可以移动"""
        x, y = position
        if 0 <= x < self.size[0] and 0 <= y < self.size[1]:
            return not self.collision_map[x][y]
        return False