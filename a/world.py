import random
import time
# import socket  # 用于多人游戏，稍后添加

# --- 常量定义 ---
MAP_SIZE = 20
# 地形类型
TERRAIN_TYPES = ["grass", "forest", "mountain", "water"]
# 资源类型
RESOURCE_TYPES = ["gold", "wood", "food"]

# --- 类定义 ---

class Map:
    def __init__(self, size):
        self.size = size
        self.grid = [[self.generate_tile() for _ in range(size)] for _ in range(size)]
        self.fog_of_war = [[True for _ in range(size)] for _ in range(size)]  # 初始全部隐藏

    def generate_tile(self):
        terrain = random.choice(TERRAIN_TYPES)
        resource = None
        if terrain != "water" and random.random() < 0.2:  # 20% 几率生成资源
            resource = random.choice(RESOURCE_TYPES)
        return {"terrain": terrain, "resource": resource, "building": None, "unit": None}

    def reveal(self, x, y, radius):
        # 揭示战争迷雾
        for i in range(max(0, x - radius), min(self.size, x + radius + 1)):
            for j in range(max(0, y - radius), min(self.size, y + radius + 1)):
                self.fog_of_war[i][j] = False
    
    def is_visible(self, x, y):
        # 检查地块是否可见
        return not self.fog_of_war[x][y]

    def display(self, player):
        # 简易文本显示地图，可以根据需要扩展
        for y in range(self.size):
            for x in range(self.size):
                if not self.is_visible(x, y):
                    print("?", end=" ")  # 战争迷雾
                else:
                    tile = self.grid[x][y]
                    if tile["unit"]:
                        print(tile["unit"].icon, end=" ")
                    elif tile["building"]:
                        print(tile["building"].icon, end=" ")
                    elif tile["resource"]:
                        print(tile["resource"][0].upper(), end=" ")  # 资源首字母大写
                    else:
                        print(".", end=" ")  # 空地
            print()
class Faction:
    def __init__(self, name, is_player=False):
        self.name = name
        self.is_player = is_player
        self.resources = {"gold": 100, "wood": 50, "food": 50}
        self.units = []
        self.buildings = []
        self.technology = []
        self.diplomacy = {}  # {faction_name: relation}，关系可以是 "ally", "neutral", "enemy"
        self.loyalty = 100 #初始忠诚度
    
    def update_loyalty(self):
        #更新忠诚度
        #可以添加各种影响忠诚度的事件或条件
        pass
    
    def check_for_rebellion(self):
        #检查是否发生叛乱
        if self.loyalty < 30 and not self.is_player:
            return True
        return False
    
    #可以添加更多的函数,比如生产单位
    def collect_resources(self):
        #从建筑物/单位收集资源
        pass
    
    def can_afford(self, cost):
        #检查是否可以负担某样东西
        pass
    
    def pay(self,cost):
        #支付某种东西
        pass
    
class Unit:
    def __init__(self, x, y, faction, unit_type):
        self.x = x
        self.y = y
        self.faction = faction
        self.type = unit_type
        self.stats = UNIT_STATS[unit_type]  # 从全局字典获取属性
        self.health = self.stats["health"]
        self.icon = self.stats["icon"]
        self.level = 1
        self.experience = 0

    def move(self, dx, dy, game_map):
        new_x, new_y = self.x + dx, self.y + dy
        if 0 <= new_x < game_map.size and 0 <= new_y < game_map.size:
            if game_map.grid[new_x][new_y]["unit"] is None:  # 目标位置没有单位
                game_map.grid[self.x][self.y]["unit"] = None  # 清空旧位置
                self.x, self.y = new_x, new_y
                game_map.grid[self.x][self.y]["unit"] = self  # 放置到新位置
                return True
        return False
    
    def attack(self,target):
        #攻击逻辑
        if self.can_attack(target):
            damage = max(0, self.stats["attack"] - target.stats["defense"])
            target.health -= damage
            print(f"{self.faction.name} 的 {self.type} 攻击 {target.faction.name} 的 {target.type}，造成 {damage} 点伤害")
            if target.health <= 0:
                print(f"{target.faction.name} 的 {target.type} 被消灭！")
                target.faction.units.remove(target)  # 从势力中移除
                game_map.grid[target.x][target.y]["unit"] = None  # 从地图上移除
    
    def can_attack(self,target):
        #检查是否在攻击距离
        distance = abs(self.x-target.x) + abs(self.y - target.y)
        return distance <= self.stats["attack_range"]
            
    def gain_experience(self, amount):
        #获取经验值
        self.experience += amount
        while self.experience >= self.level * 10:  # 升级所需经验随等级增加
            self.level_up()

    def level_up(self):
        #单位升级
        self.level += 1
        self.experience -= (self.level - 1) * 10  # 扣除升级所需经验
        # 提升属性（示例）
        self.stats["health"] += 5
        self.stats["attack"] += 2
        self.health = self.stats["health"]  # 恢复满生命值
        print(f"{self.faction.name} 的 {self.type} 升级到 {self.level} 级！")

class Building:
    def __init__(self, x, y, faction, building_type):
        self.x = x
        self.y = y
        self.faction = faction
        self.type = building_type
        self.stats = BUILDING_STATS[building_type]
        self.health = self.stats["health"]
        self.icon = self.stats["icon"]
    
    def produce_unit(self,unit_type):
        #生产单位逻辑
        pass
    
    def upgarde(self):
        #升级建筑逻辑
        pass

class Technology:
    def __init__(self, name, cost, effects):
        self.name = name
        self.cost = cost
        self.effects = effects  # 效果可以是函数或属性修改

    def research(self, faction):
        #研究科技
        if faction.can_afford(self.cost):
            faction.pay(self.cost)
            faction.technology.append(self)
            # 应用科技效果
            self.apply_effects(faction)
            print(f"{faction.name} 完成了 {self.name} 的研究！")
        else:
            print(f"{faction.name} 无法负担 {self.name} 的研究。")

    def apply_effects(self, faction):
        #应用科技效果
        pass
    
# --- 全局变量/字典 ---
#单位属性
UNIT_STATS = {
    "peasant": {"health": 20, "attack": 5, "defense": 2, "speed": 1, "cost": {"food": 20}, "icon": "P","attack_range":1},
    "soldier": {"health": 40, "attack": 10, "defense": 5, "speed": 1, "cost": {"food": 30, "gold": 10}, "icon": "S","attack_range":1},
    "archer": {"health": 30, "attack": 8, "defense": 3, "speed": 1, "cost": {"food": 25, "wood": 15}, "icon": "A","attack_range":3},
}
#建筑属性
BUILDING_STATS = {
    "town_center": {"health": 100, "produces": ["peasant"], "cost": {"wood": 100}, "icon": "T"},
    "barracks": {"health": 60, "produces": ["soldier", "archer"], "cost": {"wood": 50, "gold": 20}, "icon": "B"},
    "farm": {"health": 40, "produces": [], "cost": {"wood": 30}, "icon": "F"},  # 农田不生产单位，提供食物
}
#科技树
TECHNOLOGIES = {
    "improved_farming": Technology("Improved Farming", {"food": 50, "wood": 50}, {}),
    "bronze_weapons": Technology("Bronze Weapons", {"gold": 75, "wood": 25}, {}),
}

# --- 事件系统 ---
class Event:
    def __init__(self, name, description, effect):
        self.name = name
        self.description = description
        self.effect = effect  # 效果可以是函数

    def trigger(self, game):
        #触发事件
        print(f"事件发生：{self.name} - {self.description}")
        self.effect(game)  # 执行事件效果

# 示例事件
def drought_effect(game):
    #干旱事件
    for faction in game.factions:
        faction.resources["food"] -= 20  # 食物减少

DROUGHT_EVENT = Event("Drought", "A severe drought hits the land!", drought_effect)

EVENTS = [DROUGHT_EVENT]

# --- 游戏类 ---

class Game:
    def __init__(self):
        self.map = Map(MAP_SIZE)
        self.factions = [
            Faction("Player", is_player=True),
            Faction("AI 1"),
            Faction("AI 2"),
        ]
        self.current_faction = self.factions[0]  # 当前行动的势力
        self.turn = 0
        self.game_time = 0 #游戏时长
        self.max_game_time = 100 #最大游戏时长
        self.game_over = False

    def run(self):
            while not self.game_over:
                self.turn += 1
                print(f"\n--- 回合 {self.turn} ---")
                self.game_time += 1

                for faction in self.factions:
                    self.current_faction = faction
                    print(f"\n>> {faction.name} 的回合")

                    faction.update_loyalty()
                    if faction.check_for_rebellion():
                        self.handle_rebellion(faction)
                    
                    faction.collect_resources()

                    if faction.is_player:
                        self.player_turn(faction)
                    else:
                        self.ai_turn(faction)

                    self.reveal_map(faction)  # 揭示当前势力的视野
                    self.map.display(faction)

                    if self.check_victory_conditions():
                        self.game_over = True
                        break
                if self.game_time >= self.max_game_time:
                    self.game_over = True
                    print("游戏时间到！")
                    self.display_final_scores()

    def player_turn(self, faction):
        #玩家回合
        while True:
            action = input("请输入指令 (move, build, recruit, tech, diplomacy, end): ")
            if action == "end":
                break
            elif action == "move":
                self.handle_move_command(faction)
            elif action == "build":
                self.handle_build_command(faction)
            elif action == "recruit":
                self.handle_recruit_command(faction)
            elif action == "tech":
                self.handle_tech_command(faction)
            elif action == "diplomacy":
                self.handle_diplomacy_command(faction)
            #还可以处理其他指令

    def handle_move_command(self, faction):
        #处理移动指令
        try:
            unit_x = int(input("请输入单位 x 坐标："))
            unit_y = int(input("请输入单位 y 坐标："))
            dx = int(input("请输入 x 方向移动量："))
            dy = int(input("请输入 y 方向移动量："))

            unit = self.map.grid[unit_x][unit_y]["unit"]
            if unit and unit.faction == faction:
                if unit.move(dx, dy, self.map):
                    print("单位移动成功。")
                else:
                    print("无法移动到目标位置。")
            else:
                print("所选位置没有您的单位。")
        except (ValueError, IndexError):
            print("无效的坐标输入。")

    def handle_build_command(self, faction):
        #处理建造命令
        try:
            x = int(input("请输入建造 x 坐标："))
            y = int(input("请输入建造 y 坐标："))
            building_type = input("请输入要建造的建筑类型：")

            if building_type in BUILDING_STATS:
                cost = BUILDING_STATS[building_type]["cost"]
                if faction.can_afford(cost):
                    if self.map.grid[x][y]["building"] is None:
                        faction.pay(cost)
                        building = Building(x, y, faction, building_type)
                        self.map.grid[x][y]["building"] = building
                        faction.buildings.append(building)
                        print(f"在 ({x}, {y}) 建造了 {building_type}。")
                    else:
                        print("该位置已有建筑。")
                else:
                    print("资源不足，无法建造。")
            else:
                print("无效的建筑类型。")
        except (ValueError, IndexError):
            print("无效的坐标输入。")

    def handle_recruit_command(self, faction):
        #处理招募命令
         try:
            x = int(input("请输入招募建筑的 x 坐标："))
            y = int(input("请输入招募建筑的 y 坐标："))
            unit_type = input("请输入要招募的单位类型：")

            building = self.map.grid[x][y]["building"]
            if building and building.faction == faction:
                if unit_type in building.stats.get("produces", []):
                    cost = UNIT_STATS[unit_type]["cost"]
                    if faction.can_afford(cost):
                        faction.pay(cost)
                        unit = Unit(x, y, faction, unit_type)
                        self.map.grid[x][y]["unit"] = unit  # 放置在建筑旁边
                        faction.units.append(unit)
                        print(f"在 ({x}, {y}) 招募了 {unit_type}。")
                    else:
                        print("资源不足，无法招募。")
                else:
                    print("该建筑无法生产此单位。")
            else:
                print("所选位置没有您的建筑或建筑类型不符。")
         except (ValueError, IndexError):
            print("无效的坐标输入。")

    def handle_tech_command(self, faction):
        #处理科技命令
        tech_name = input("请输入要研究的科技名称：")
        if tech_name in TECHNOLOGIES:
            TECHNOLOGIES[tech_name].research(faction)
        else:
            print("无效的科技名称。")

    def handle_diplomacy_command(self, faction):
        #处理外交命令
        target_faction_name = input("请输入目标势力名称：")
        if target_faction_name != faction.name:
            target_faction = self.find_faction(target_faction_name)
            if target_faction:
                action = input("请输入外交行动 (ally, declare_war, trade): ")
                if action == "ally":
                    self.propose_alliance(faction, target_faction)
                elif action == "declare_war":
                    self.declare_war(faction, target_faction)
                elif action == "trade":
                    self.initiate_trade(faction,target_faction)
            else:
                print("未找到该势力")
        else:
            print("您不能和自己进行外交")
    
    def find_faction(self, name):
        #根据名称查找阵营
        for faction in self.factions:
            if faction.name == name:
                return faction
        return None

    def propose_alliance(self, faction1, faction2):
        #提议结盟
        if faction2.is_player:
            #如果目标是玩家,询问玩家
            response = input(f"{faction1.name}提议与您结盟,是否同意(yes/no)?")
            if response.lower() == "yes":
                faction1.diplomacy[faction2.name] = "ally"
                faction2.diplomacy[faction1.name] = "ally"
                print(f"{faction1.name} 与 {faction2.name} 结盟了！")
            else:
                print(f"{faction2.name} 拒绝了 {faction1.name} 的结盟提议。")
        else:
            #如果是AI，根据AI逻辑决定
            if self.ai_accepts_alliance(faction1, faction2):
                faction1.diplomacy[faction2.name] = "ally"
                faction2.diplomacy[faction1.name] = "ally"
                print(f"{faction1.name} 与 {faction2.name} 结盟了！")
            else:
                print(f"{faction2.name} 拒绝了 {faction1.name} 的结盟提议。")
    
    def ai_accepts_alliance(self, faction1, faction2):
        #AI决定是否结盟
        #可以添加更复杂的逻辑
        return random.random() < 0.5 #50%概率同意

    def declare_war(self, faction1, faction2):
        #宣战
        faction1.diplomacy[faction2.name] = "enemy"
        faction2.diplomacy[faction1.name] = "enemy"
        print(f"{faction1.name} 向 {faction2.name} 宣战了！")

    def initiate_trade(self, faction1, faction2):
        #发起交易
        if faction2.is_player:
            #如果目标是玩家,询问玩家
            print(f"{faction1.name} 想和您交易。")
            offer = self.get_trade_offer(faction1)
            print(f"{faction1.name} 的提议：{offer}")
            response = input("您是否接受交易 (yes/no)? ")
            if response.lower() == "yes":
                if self.can_fulfill_trade(faction2, offer) and self.can_fulfill_trade(faction1, offer, reverse=True):
                    self.execute_trade(faction1, faction2, offer)
                    print("交易成功！")
                else:
                    print("交易失败，资源不足。")
            else:
                print("交易被拒绝。")
        else:
            # 如果是AI，根据AI逻辑决定
            offer = self.get_trade_offer(faction1)
            if self.ai_accepts_trade(faction2, offer):
                if self.can_fulfill_trade(faction2, offer) and self.can_fulfill_trade(faction1, offer, reverse=True):
                    self.execute_trade(faction1, faction2, offer)
                    print(f"{faction1.name} 与 {faction2.name} 完成了交易！")
                else:
                    print(f"{faction2.name} 无法完成与 {faction1.name} 的交易，资源不足。")
            else:
                print(f"{faction2.name} 拒绝了 {faction1.name} 的交易提议。")
    
    def get_trade_offer(self, faction):
        #获取交易提议
        #对于玩家，可以手动输入
        #对于AI，可以随机生成
        if faction.is_player:
            offer = {}
            print("请输入您的交易提议（格式：资源类型 数量, ...）：")
            offer_str = input()
            try:
                for item in offer_str.split(","):
                    resource, amount = item.strip().split()
                    offer[resource] = int(amount)
                return offer
            except:
                print("无效的交易提议格式。")
                return {}
        else:
            # AI 随机生成交易提议
            offer = {}
            for resource in RESOURCE_TYPES:
                if random.random() < 0.3:  # 30% 概率提供某种资源
                    amount = random.randint(10, 30)
                    offer[resource] = amount
            return offer
    
    def ai_accepts_trade(self, faction, offer):
        #AI判断是否接受交易
        #可以基于AI的需求和资源情况来判断
        return random.random() < 0.7 #70%接受

    def can_fulfill_trade(self, faction, offer, reverse=False):
        #检查是否有足够的资源完成交易
        for resource, amount in offer.items():
            if reverse:
                amount = -amount  # 反向交易，检查对方是否能提供
            if faction.resources.get(resource, 0) < amount:
                return False
        return True

    def execute_trade(self, faction1, faction2, offer):
        #执行交易
        for resource, amount in offer.items():
            faction1.resources[resource] -= amount
            faction2.resources[resource] += amount

    def handle_rebellion(self, faction):
        #处理叛乱
        print(f"{faction.name} 发生了叛乱！")
        #创建新的叛军势力
        rebel_faction = Faction(f"{faction.name} Rebels")
        self.factions.append(rebel_faction)
        #将一部分单位和建筑转移给叛军
        num_rebels = len(faction.units) // 3  # 假设1/3的单位叛变
        for _ in range(num_rebels):
            unit = faction.units.pop()
            unit.faction = rebel_faction
            rebel_faction.units.append(unit)
        
        # 叛军与原势力敌对
        faction.diplomacy[rebel_faction.name] = "enemy"
        rebel_faction.diplomacy[faction.name] = "enemy"

        # 也可以将一部分建筑转移给叛军（根据需要）

    def ai_turn(self, faction):
        #AI 回合的行动决策
        # 简单的 AI 示例：
        # 1. 尝试建造农田，如果食物不足
        if faction.resources["food"] < 50:
            self.ai_build(faction, "farm")
        # 2. 尝试建造兵营，如果金币和木材充足
        elif faction.resources["gold"] > 50 and faction.resources["wood"] > 50:
            self.ai_build(faction, "barracks")
        # 3. 尝试招募士兵，如果兵营存在
        for building in faction.buildings:
            if building.type == "barracks":
                self.ai_recruit(faction, building, "soldier")
        # 4. 随机移动单位
        for unit in faction.units:
            self.ai_move_unit(unit)
        # 5. 攻击敌方单位/建筑
        for unit in faction.units:
            self.ai_attack(unit)
    
    def ai_build(self, faction, building_type):
        #AI建造建筑
        for _ in range(10):  # 尝试 10 次随机位置
            x = random.randint(0, self.map.size - 1)
            y = random.randint(0, self.map.size - 1)
            if self.map.grid[x][y]["building"] is None and faction.can_afford(BUILDING_STATS[building_type]["cost"]):
                faction.pay(BUILDING_STATS[building_type]["cost"])
                building = Building(x, y, faction, building_type)
                self.map.grid[x][y]["building"] = building
                faction.buildings.append(building)
                print(f"AI {faction.name} 在 ({x}, {y}) 建造了 {building_type}。")
                return

    def ai_recruit(self, faction, building, unit_type):
        #AI招募单位
        if unit_type in building.stats.get("produces", []) and faction.can_afford(UNIT_STATS[unit_type]["cost"]):
            faction.pay(UNIT_STATS[unit_type]["cost"])
            unit = Unit(building.x, building.y, faction, unit_type)
            self.map.grid[building.x][building.y]["unit"] = unit  # 放置在建筑旁边
            faction.units.append(unit)
            print(f"AI {faction.name} 在 ({building.x}, {building.y}) 招募了 {unit_type}。")

    def ai_move_unit(self, unit):
        #AI 移动单位（随机移动）
        dx = random.randint(-1, 1)
        dy = random.randint(-1, 1)
        unit.move(dx, dy, self.map)
    
    def ai_attack(self, unit):
        #AI单位攻击
        #寻找视野范围内的敌方单位/建筑
        for target in self.find_targets_in_range(unit):
            if unit.can_attack(target):
                unit.attack(target)
                return #攻击后结束

    def find_targets_in_range(self,unit):
        #寻找攻击范围内的目标
        targets = []
        for x in range(self.map.size):
            for y in range(self.map.size):
                target_unit = self.map.grid[x][y]["unit"]
                target_building = self.map.grid[x][y]["building"]
                if target_unit and target_unit.faction != unit.faction:
                    targets.append(target_unit)
                if target_building and target_building.faction != unit.faction:
                    targets.append(target_building)
        return targets

    def reveal_map(self, faction):
        #揭示当前势力的视野
        for unit in faction.units:
            self.map.reveal(unit.x, unit.y, unit.stats["speed"] + 2)  # 视野基于移动速度
        for building in faction.buildings:
            self.map.reveal(building.x, building.y, 3)  # 建筑提供固定视野

    def check_victory_conditions(self):
        #检查胜利条件
        #示例：消灭所有敌对势力
        alive_factions = 0
        for faction in self.factions:
            if faction.units or faction.buildings:  # 如果还有单位或建筑，则势力存活
                alive_factions += 1
        if alive_factions == 1:  # 如果只剩一个势力，则游戏结束
            for faction in self.factions:
                if faction.units or faction.buildings:
                    print(f"{faction.name} 获胜！")
                    return True
        return False
    
    def display_final_scores(self):
        #显示最终得分
        #可以基于资源、单位、建筑、科技等计算
        print("游戏结束，最终得分：")
        for faction in self.factions:
            score = 0
            score += faction.resources["gold"] * 1
            score += faction.resources["wood"] * 0.5
            score += faction.resources["food"] * 0.5
            score += len(faction.units) * 10
            score += len(faction.buildings) * 20
            score += len(faction.technology) * 15
            print(f"{faction.name}: {score}")

# --- 游戏启动 ---

game = Game()
game.run()
