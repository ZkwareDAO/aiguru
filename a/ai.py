# ai.py
import random
from base import Player

class AIPlayer(Player):
    def __init__(self, name):
        super().__init__(name, is_ai=True)

    def take_turn(self, game):
        # 简单的 AI 行为
        action = random.choice(["build", "recruit", "pass"]) #增加更多行为逻辑
        if action == "build":
            city = random.choice(self.cities)
            building_type = random.choice(["Barracks", "Farm"])
            city.build(building_type)
        elif action == "recruit":
            pass #招募逻辑
        print(f"{self.name} 选择了 {action}")
