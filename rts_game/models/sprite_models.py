import pygame
from typing import Dict, Tuple, List
from enum import Enum

class AnimationState(Enum):
    """精灵动画状态枚举"""
    IDLE = 'idle'
    WALK = 'walk'
    RUN = 'run'
    ATTACK = 'attack'
    HURT = 'hurt'
    DEATH = 'death'
    WORK = 'work'
    SLEEP = 'sleep'

class Direction(Enum):
    """精灵朝向枚举"""
    DOWN = 0
    DOWN_RIGHT = 1
    RIGHT = 2
    UP_RIGHT = 3
    UP = 4
    UP_LEFT = 5
    LEFT = 6
    DOWN_LEFT = 7

class SpriteAnimation:
    """像素风格精灵动画系统"""
    def __init__(self, spritesheet_path: str, frame_size: Tuple[int, int], 
                 animation_config: Dict[str, Dict] = None, variants: int = 8):
        self.spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        self.frame_width, self.frame_height = frame_size
        self.frames: Dict[str, List[pygame.Surface]] = {}
        self.current_state = AnimationState.IDLE
        self.current_direction = Direction.DOWN
        self.current_frame_index = 0
        self.animation_timer = 0
        self.last_update = pygame.time.get_ticks()
        self.animation_config = animation_config or {
            AnimationState.IDLE.value: {
                'frames': [0, 1],
                'duration': 800,  # 每帧持续时间(ms)
                'loop': True
            }
        }
        self.animation_states = {
            'idle': slice(0, 1)
        }
        self.frames = {
            'idle': [self.spritesheet.subsurface((0, 0, self.frame_width, self.frame_height))]
        }
        
        self._initialize_frames()
    
    def _initialize_frames(self):
        """初始化动画帧"""
        sheet_rect = self.spritesheet.get_rect()
        
        for state in self.animation_config.keys():
            self.frames[state] = []
            frame_indices = self.animation_config[state]['frames']

            
            # 对于简单的精灵图，使用所有配置的帧
            for frame_index in frame_indices:
                frame = self.spritesheet.subsurface((0, 0, self.frame_width, self.frame_height))
                self.frames[state].append(frame)
            
            # 确保至少有一帧
            if not self.frames[state]:
                frame = self.spritesheet.subsurface((0, 0, self.frame_width, self.frame_height))
                self.frames[state].append(frame)
    
    def update(self, delta_time: float):
        """更新动画状态"""
        if not self.animation_config[self.current_state.value]['loop'] and \
           self.current_frame_index >= len(self.frames[self.current_state.value]) - 1:
            return
        
        self.animation_timer += delta_time
        frame_duration = self.animation_config[self.current_state.value]['duration'] / \
                        len(self.frames[self.current_state.value])
        
        if self.animation_timer >= frame_duration:
            self.animation_timer = 0
            self.current_frame_index = (self.current_frame_index + 1) % \
                                      len(self.frames[self.current_state.value])
    
    def set_state(self, state: AnimationState):
        """设置动画状态"""
        if state.value in self.animation_config and state != self.current_state:
            self.current_state = state
            self.current_frame_index = 0
            self.animation_timer = 0
    
    def set_direction(self, direction: Direction):
        """设置精灵朝向"""
        self.current_direction = direction
    
    def get_current_frame(self) -> pygame.Surface:
        """获取当前动画帧"""
        frame = self.frames[self.current_state.value][self.current_frame_index]
        return self._apply_direction(frame)
    
    def _apply_direction(self, frame: pygame.Surface) -> pygame.Surface:
        """根据朝向处理精灵图像"""
        if self.current_direction in [Direction.LEFT, Direction.UP_LEFT, Direction.DOWN_LEFT]:
            return pygame.transform.flip(frame, True, False)
        return frame

class IsometricProjection:
    """像素风格坐标投影"""
    TILE_WIDTH = 16  # 基础图块宽度
    TILE_HEIGHT = 16  # 基础图块高度
    
    @staticmethod
    def to_screen(tile_x: int, tile_y: int, tile_z: int = 0) -> Tuple[int, int]:
        """将游戏坐标转换为屏幕坐标"""
        screen_x = (tile_x - tile_y) * (IsometricProjection.TILE_WIDTH // 2)
        screen_y = (tile_x + tile_y) * (IsometricProjection.TILE_HEIGHT // 4) - tile_z * 8
        return (screen_x, screen_y)

# 地形精灵配置
TERRAIN_SPRITES = {
    'grass': {
        'spritesheet': 'assets/spritesheets/terrain/grass.png',
        'frame_size': (32, 32),
        'variants': 1,
        'animations': {
            'idle': {
                'frames': [0],
                'duration': 1000,
                'loop': False
            }
        }
    },
    'water': {
        'spritesheet': 'assets/spritesheets/terrain/water.png',
        'frame_size': (32, 32),
        'variants': 4,
        'animations': {
            'idle': {
                'frames': [0, 1, 2, 3],
                'duration': 2000,
                'loop': True
            }
        }
    },
    'mountain': {
        'spritesheet': 'assets/spritesheets/terrain/mountain.png',
        'frame_size': (32, 32),
        'variants': 1,
        'animations': {
            'idle': {
                'frames': [0],
                'duration': 1000,
                'loop': False
            }
        }
    }
}

# 单位精灵配置
UNIT_SPRITES = {
    'warrior': {
        'spritesheet': 'assets/spritesheets/units/warrior.png',
        'frame_size': (32, 32),
        'variants': 3,
        'animations': {
            'idle': {
                'frames': [0, 1],
                'duration': 1000,
                'loop': True
            },
            'walk': {
                'frames': [2, 3, 4, 5],
                'duration': 800,
                'loop': True
            },
            'attack': {
                'frames': [6, 7, 8, 9],
                'duration': 600,
                'loop': False
            }
        }
    }
}

# 建筑精灵配置
BUILDING_SPRITES = {
    'house': {
        'spritesheet': 'assets/spritesheets/buildings/house.png',
        'frame_size': (32, 32),
        'animations': {
            'idle': {
                'frames': [0, 1, 2, 3],
                'duration': 2000,
                'loop': True
            },
            'work': {
                'frames': [0],
                'duration': 1000,
                'loop': False
            }
        },
        'elevation': 0
    },
    'castle': {
        'spritesheet': 'assets/spritesheets/buildings/castle.png',
        'frame_size': (64, 64),
        'animations': {
            'idle': {
                'frames': [0],
                'duration': 1000,
                'loop': False
            }
        },
        'elevation': 2
    },
    'farm': {
        'spritesheet': 'assets/spritesheets/buildings/farm.png',
        'frame_size': (48, 48),
        'animations': {
            'idle': {
                'frames': [0, 1],
                'duration': 1000,
                'loop': True
            },
            'work': {
                'frames': [2, 3, 4, 5],
                'duration': 1200,
                'loop': True
            }
        }
    }
}

# 角色精灵配置
CHARACTER_SPRITES = {
    'farmer': {
        'spritesheet': 'assets/spritesheets/characters/farmer.png',
        'frame_size': (16, 32),
        'animations': {
            'idle': {
                'frames': [0, 1],
                'duration': 1000,
                'loop': True
            },
            'walk': {
                'frames': [4, 5, 6, 7],
                'duration': 800,
                'loop': True
            },
            'work': {
                'frames': [8, 9, 10, 11],
                'duration': 1000,
                'loop': True
            }
        }
    },
    'miner': {
        'spritesheet': 'assets/spritesheets/characters/miner.png',
        'frame_size': (16, 32),
        'animations': {
            'idle': {
                'frames': [0, 1],
                'duration': 1000,
                'loop': True
            },
            'work': {
                'frames': [4, 5, 6, 7],
                'duration': 800,
                'loop': True
            }
        }
    }
}

# 装饰物精灵配置
DECORATION_SPRITES = {
    'tree': {
        'spritesheet': 'assets/spritesheets/decorations/tree.png',
        'frame_size': (32, 48),
        'animations': {
            'idle': {
                'frames': [0, 1, 2],
                'duration': 2000,
                'loop': True
            }
        }
    },
    'flower': {
        'spritesheet': 'assets/spritesheets/decorations/flower.png',
        'frame_size': (16, 16),
        'animations': {
            'idle': {
                'frames': [0, 1],
                'duration': 1500,
                'loop': True
            }
        }
    }
}