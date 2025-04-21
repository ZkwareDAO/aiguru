# building.py
# 建筑模型定义

class Building:
    """建筑基类，代表游戏中的一个建筑"""
    
    def __init__(self, name, building_type, owner=None):
        self.name = name
        self.type = building_type
        self.owner = owner  # 所属势力或玩家
        self.level = 1
        self.health = 100
        self.max_health = 100
        self.construction_progress = 0  # 建造进度 (0-100)
        self.is_completed = False
        self.maintenance_cost = {"gold": 5}  # 维护成本
        
        # 建筑特性，由子类覆盖
        self.resource_bonus = {}  # 资源产出加成
        self.happiness_bonus = 0  # 幸福度加成
        self.defense_bonus = 0  # 防御加成
        
    def update(self):
        """更新建筑状态（每回合调用）"""
        if not self.is_completed:
            self.construction_progress += 10
            if self.construction_progress >= 100:
                self.is_completed = True
                self.construction_progress = 100
                self.apply_effect()
    
    def apply_effect(self, city=None):
        """应用建筑效果到城市"""
        pass  # 由子类实现
    
    def remove_effect(self, city=None):
        """移除建筑效果"""
        pass  # 由子类实现
    
    def upgrade(self):
        """升级建筑"""
        self.level += 1
        self.max_health += 50
        self.health = self.max_health
        # 子类可以覆盖此方法以提供额外的升级效果
        
    def repair(self, amount):
        """修复建筑"""
        self.health = min(self.max_health, self.health + amount)
        
    def take_damage(self, amount):
        """建筑受到伤害"""
        self.health -= amount
        return self.health <= 0  # 返回是否被摧毁


class Farm(Building):
    """农场，提高食物产量"""
    
    def __init__(self, name, owner=None):
        super().__init__(name, "farm", owner)
        self.resource_bonus = {"food": 1.2}  # 增加20%食物产量
        self.happiness_bonus = 2  # 小幅提高幸福度
        
    def upgrade(self):
        super().upgrade()
        # 升级效果：进一步提高食物产量
        self.resource_bonus["food"] += 0.1  # 每级增加10%
        

class Mine(Building):
    """矿场，提高金矿和石头产量"""
    
    def __init__(self, name, owner=None):
        super().__init__(name, "mine", owner)
        self.resource_bonus = {"gold": 1.3, "stone": 1.5}  # 增加金矿和石头产量
        
    def upgrade(self):
        super().upgrade()
        # 升级效果：进一步提高产量
        self.resource_bonus["gold"] += 0.1
        self.resource_bonus["stone"] += 0.1
        

class LumberMill(Building):
    """伐木场，提高木材产量"""
    
    def __init__(self, name, owner=None):
        super().__init__(name, "lumber_mill", owner)
        self.resource_bonus = {"wood": 1.5}  # 增加50%木材产量
        
    def upgrade(self):
        super().upgrade()
        # 升级效果：进一步提高木材产量
        self.resource_bonus["wood"] += 0.1  # 每级增加10%
        

class Barracks(Building):
    """兵营，允许训练军队"""
    
    def __init__(self, name, owner=None):
        super().__init__(name, "barracks", owner)
        self.defense_bonus = 10  # 提供防御加成
        self.trainable_units = ["soldier", "archer"]  # 可训练的单位类型
        
    def upgrade(self):
        super().upgrade()
        # 升级效果：提高防御加成，解锁新单位
        self.defense_bonus += 5
        if self.level == 2:
            self.trainable_units.append("knight")
        elif self.level == 3:
            self.trainable_units.append("catapult")
        elif self.level == 4:
            self.trainable_units.append("mage")
        elif self.level == 5:
            self.trainable_units.append("siege_engine")
            

class Castle(Building):
    """城堡，提供强大的防御和代币收入"""
    
    def __init__(self, name, owner=None):
        super().__init__(name, "castle", owner)
        self.defense_bonus = 30  # 提供强大的防御加成
        self.resource_bonus = {"gold": 1.5}  # 增加50%金币收入
        self.happiness_bonus = 10  # 显著提高幸福度
        self.garrison_capacity = 5  # 驻军容量
        self.garrison_units = []  # 当前驻军
        self.special_abilities = ["inspire"]  # 特殊能力
        
    def upgrade(self):
        super().upgrade()
        # 升级效果：全面提升城堡性能
        self.defense_bonus += 10
        self.resource_bonus["gold"] += 0.2
        self.happiness_bonus += 2
        self.garrison_capacity += 2
        
        # 解锁新的特殊能力
        if self.level == 2:
            self.special_abilities.append("rally")  # 集结军队
        elif self.level == 3:
            self.special_abilities.append("fortify")  # 强化防御
        elif self.level == 4:
            self.special_abilities.append("conscription")  # 征兵
        elif self.level == 5:
            self.special_abilities.append("royal_decree")  # 皇家敕令
            
    def garrison_unit(self, unit):
        """添加驻军单位"""
        if len(self.garrison_units) < self.garrison_capacity:
            self.garrison_units.append(unit)
            self.defense_bonus += unit.combat_power
            return True
        return False
        
    def remove_garrison(self, unit):
        """移除驻军单位"""
        if unit in self.garrison_units:
            self.garrison_units.remove(unit)
            self.defense_bonus -= unit.combat_power
            return True
        return False
        
    def apply_effect(self, city=None):
        """应用城堡效果到城市"""
        if city:
            city.defense += self.defense_bonus
            city.happiness += self.happiness_bonus
            for resource, bonus in self.resource_bonus.items():
                city.resource_multipliers[resource] *= bonus