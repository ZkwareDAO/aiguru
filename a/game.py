import random
from base import Player
from base import City
from base import AIPlayer
from base import Unit

class Game:
    def __init__(self, num_players=2, num_ai=2):
        # 修正字符串格式化，正确生成玩家和AI玩家
        self.players  = [Player(f"Player {i+1}") for i in range(num_players)]
        self.players  += [AIPlayer(f"AI {i+1}") for i in range(num_ai)]
        self.cities  = []
        self.turn  = 0
        self.game_over  = False

        # 初始城池 (简化)
        for player in self.players: 
            # 修正字符串格式化，正确生成城市名
            city = City(f"{player.name}'s  Capital", player)
            self.cities.append(city) 
            player.cities.append(city) 

    def start_game(self):
        print("游戏开始！")
        while not self.game_over: 
            self.turn  += 1
            # 修正字符串格式化，正确显示回合数
            print(f"\n--- 回合 {self.turn}  ---")
            self.take_turn() 

    def take_turn(self):
        for player in self.players: 
            # 修正字符串格式化，正确显示玩家名字
            print(f"\n{player.name}  的回合:")

            # 征税
            player.collect_taxes() 

            if player.is_ai: 
                player.take_turn(self)   # AI 行动
            else:
                # 玩家行动 (简化)
                while True:
                    action = input("你要做什么？ (build/recruit/pass/show): ")
                    if action == "build":
                        city_name = input("选择城市: ")
                        building_type = input("建造什么？ (Barracks/Farm/etc.): ")
                        city = self.find_city(city_name) 
                        if city and city.owner  == player:
                            city.build(building_type) 
                        else:
                            print("无效的城市或建筑")
                    elif action == "recruit":
                        unit_name = input("招募兵种: ")
                        city_name = input("选择城市: ")
                        city = self.find_city(city_name) 
                        # 查找兵种数据
                        # 检查资源
                        # 创建Unit对象,添加到player.units 
                    elif action == "show":
                        # 修正字符串格式化，正确显示玩家资源和城市信息
                        print(f"{player.name}  资源: {player.resources}") 
                        for city in player.cities: 
                            print(f"{city.name}:  人口 {city.population}") 
                    elif action == "pass":
                        break
                    else:
                        print("无效的行动")

            # 检查游戏结束条件 (简化)
            if len(self.cities)  == 1 and self.cities[0].owner  == player:
                # 修正字符串格式化，正确显示获胜玩家名字
                print(f"{player.name}  获胜！")
                self.game_over  = True
                break

            # 简化事件处理（如叛乱）
            for city in self.cities: 
                if city.loyalty  < 30:
                    if random.random()  < 0.2:  # 有一定概率叛乱
                        # 修正字符串格式化，正确显示叛乱城市名
                        print(f"{city.name}  发生了叛乱!")
                        new_owner = None  # 选择新的拥有者（可以是AI或叛军）
                        city.owner  = new_owner

    def find_city(self, city_name):
        for city in self.cities: 
            if city.name  == city_name:
                return city
        return None