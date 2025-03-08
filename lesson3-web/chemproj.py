import streamlit as st
import random

chemistry_question_bank = [
    ("Is water a compound?", True),
    ("Is oxygen gas (O₂) an element?", True),
    ("Is table salt (NaCl) a mixture?", False),
    ("Is air a compound?", False),
    ("Is carbon dioxide (CO₂) a pure substance?", True),
    ("Is bronze (Cu - Sn alloy) a compound?", False),
    ("Is hydrochloric acid (HCl) a mixture?", False),
    ("Is sugar water a compound?", False),
    ("Is methane (CH₄) an organic compound?", True),
    ("Is graphite a form of elemental carbon?", True),
    ("Is ozone (O₃) a compound?", False),
    ("Is ammonia (NH₃) a covalent compound?", True),
    ("Is seawater a homogeneous mixture?", True),
    ("Is hydrogen peroxide (H₂O₂) a compound?", True),
    ("Is dry ice (solid CO₂) a pure substance?", True),
    ("Is vinegar (acetic acid solution) a compound?", False),
    ("Is sodium hydroxide (NaOH) an ionic compound?", True),
    ("Is milk a homogeneous mixture?", False),
    ("Is sulfur (S₈) a molecular element?", True),
    ("Is diamond a form of carbon compound?", False),
    ("Is tap water a pure substance?", False),
    ("Is nitrogen gas (N₂) a diatomic element?", True),
    ("Is ethanol (C₂H₅OH) a hydrocarbon?", False),
    ("Is sulfuric acid (H₂SO₄) a ternary compound?", True),
    ("Is rust (Fe₂O₃·xH₂O) a mixture?", False),
    ("Is chlorophyll a complex compound?", True),
    ("Is silver nitrate (AgNO₃) a simple substance?", False),
    ("Is liquid nitrogen a compound?", False),
    ("Is potassium permanganate (KMnO₄) a salt?", True),
    ("Is cloud water vapor a mixture?", True),
    ("Is hydrogen chloride gas (HCl) a compound?", True),
    ("Is iodine tincture a colloid?", True),
    ("Is sodium silicate (Na₂SiO₃) a covalent compound?", False),
    ("Is dry air a homogeneous mixture?", True),
    ("Is calcium carbonate (CaCO₃) a carbonate?", True),
    ("Is 75% alcohol a solution?", True),
    ("Is argon gas (Ar) a monatomic element?", True),
    ("Is quartz (SiO₂) an oxide compound?", True),
    ("Is stainless steel a solid solution?", True),
    ("Is methane hydrate (CH₄·5.75H₂O) a clathrate compound?", True),
    ("Is liquid oxygen a pure substance?", True),
    ("Is carbon monoxide (CO) an acidic oxide?", False),
    ("Is phosphorus pentoxide (P₂O₅) a covalent oxide?", True),
    ("Is DDVP (C₄H₇Cl₂O₄P) an organic phosphorus compound?", True),
    ("Is mercury (Hg) a metallic element?", True),
    ("Is hydrogen sulfate (H₂SO₄) a binary acid?", False),
    ("Is sodium hypochlorite (NaClO) a chlorate?", False),
    ("Is ammonium chloride (NH₄Cl) an ionic compound?", True),
    ("Is cement a complex mixture?", True),
    ("Is graphene a carbon allotrope?", True) ,
    ("Is water a compound?", True),
    ("Does oxygen have 8 protons?", True),
    ("Is sodium chloride an element?", False),
    ("Do acids turn litmus paper blue?", False),
    ("Is carbon dioxide a greenhouse gas?", True),
    ("Is the chemical symbol for gold 'Ag'?", False),
    ("Do all metals conduct electricity?", True),
    ("Is helium a noble gas?", True),
    ("Does a base have a pH less than 7?", False),
    ("Is hydrogen the lightest element?", True),
    ("Is potassium a halogen?", False),
    ("Do non - metals generally have low melting points?", True),
    ("Is the formula for methane CH4?", True),
    ("Does iron rust in the presence of water and oxygen?", True),
    ("Is sulfur a metal?", False),
    ("Do all acids contain hydrogen?", True),
    ("Is neon more reactive than fluorine?", False),
    ("Is calcium a alkaline earth metal?", True),
    ("Does combustion always produce carbon dioxide?", False),
    ("Is the atomic number of lithium 3?", True),
    ("Is mercury a liquid at room temperature?", True),
    ("Do bases react with acids to form salts?", True),
    ("Is nitrogen the most abundant gas in the atmosphere?", True),
    ("Is chlorine a diatomic molecule?", True),
    ("Does copper sulfate solution turn blue when hydrated?", True),
    ("Is phosphorus a non - metal?", True),
    ("Do alkalis turn phenolphthalein pink?", True),
    ("Is ozone O3?", True),
    ("Is the melting point of ice 0 degrees Celsius?", True),
    ("Is nickel a transition metal?", True)
]


def generate_maze(size):
    # 增加围墙，实际迷宫大小为 size - 2
    maze = [[1] * size for _ in range(size)]
    stack = []
    start_x, start_y = size // 2, size // 2
    maze[start_x][start_y] = 0
    stack.append((start_x,  start_y))

    while stack:
        x, y = stack[-1]
        neighbors = []
        if x > 1 and maze[x - 2][y] == 1:
            neighbors.append((x  - 2, y))
        if y > 1 and maze[x][y - 2] == 1:
            neighbors.append((x,  y - 2))
        if x < size - 2 and maze[x + 2][y] == 1:
            neighbors.append((x  + 2, y))
        if y < size - 2 and maze[x][y + 2] == 1:
            neighbors.append((x,  y + 2))

        if neighbors:
            nx, ny = random.choice(neighbors) 
            maze[(x + nx) // 2][(y + ny) // 2] = 0
            maze[nx][ny] = 0
            stack.append((nx,  ny))
        else:
            stack.pop() 

    # 标记多个出口
    exits = []
    for i in range(1, size - 1):
        if maze[i][size - 2] == 0:
            exits.append((i,  size - 2))
        if maze[size - 2][i] == 0:
            exits.append((size  - 2, i))
    num_exits = random.randint(2,  min(5, len(exits)))
    selected_exits = random.sample(exits,  num_exits)
    for ex, ey in selected_exits:
        maze[ex][ey] = 3

    # 找出所有路口并标记问题点
    for i in range(1, size - 1):
        for j in range(1, size - 1):
            if maze[i][j] == 0:
                count = 0
                directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                for dx, dy in directions:
                    if maze[i + dx][j + dy] == 0:
                        count += 1
                if count > 2:
                    # 在分岔路口的各个路线往前处设置问题点
                    for dx, dy in directions:
                        if maze[i + dx][j + dy] == 0:
                            maze[i + 2 * dx][j + 2 * dy] = 2

    return maze


def reset_game():
    st.session_state.maze  = generate_maze(23)  # 实际迷宫大小 21，加上围墙为 23
    st.session_state.current  = (11, 11)
    st.session_state.path  = [(11, 11)]
    st.session_state.question_count  = 0
    st.session_state.answering  = False
    st.session_state.current_question  = None
    st.session_state.user_answer  = None


def is_path_blocked(maze, current, direction):
    nx, ny = current[0] + direction[0], current[1] + direction[1]
    # 检查是否封死到出口的路，简单判断是否还有其他路径可走
    # 这里只是一个简单示例，实际可能需要更复杂的路径搜索算法
    if maze[nx][ny] == 3:  # 如果下一个位置是出口，不封路
        return True
    return False


def play_maze():
    # 初始化session状态
    if "maze" not in st.session_state: 
        st.session_state.maze  = generate_maze(23)  # 实际迷宫大小 21，加上围墙为 23
        st.session_state.current  = (11, 11)
        st.session_state.path  = [(11, 11)]
        st.session_state.question_count  = 0
        st.session_state.answering  = False
        st.session_state.current_question  = None
        st.session_state.user_answer  = None

    maze_size = 23  # 加上围墙后的大小
    current = st.session_state.current 
    path = st.session_state.path 

    # 方向控制布局
    col1, col2, col3 = st.columns([1,  3, 1])
    disabled = st.session_state.answering 
    with col1:
        if st.button("←",  key="left", disabled=disabled):
            st.session_state.direction  = (0, -1)
    with col2:
        if st.button("↑",  key="up", disabled=disabled):
            st.session_state.direction  = (-1, 0)
        if st.button("↓",  key="down", disabled=disabled):
            st.session_state.direction  = (1, 0)
    with col3:
        if st.button("→",  key="right", disabled=disabled):
            st.session_state.direction  = (0, 1)

    # 移动处理逻辑
    if "direction" in st.session_state  and not st.session_state.answering: 
        dx, dy = st.session_state.direction 
        nx, ny = current[0] + dx, current[1] + dy

        if 0 <= nx < maze_size and 0 <= ny < maze_size:
            cell = st.session_state.maze[nx][ny] 

            if cell == 2:  # 路口问题处理
                st.session_state.answering  = True
                # 直接随机抽题，题库永不耗尽
                q, a = random.choice(chemistry_question_bank) 
                st.session_state.current_question  = (q, a)
                st.session_state.user_answer  = None

            elif cell == 0 or cell == 3:  # 正常路径或出口
                st.session_state.current  = (nx, ny)
                if (nx, ny) in path:
                    index = path.index((nx,  ny))
                    st.session_state.path  = path[:index + 1]
                else:
                    path.append((nx,  ny))

    # 答题逻辑
    if st.session_state.answering: 
        q, a = st.session_state.current_question 
        if st.session_state.user_answer  is None:
            st.session_state.user_answer  = st.radio(q,  ["True", "False"], index=None)
        if st.button("Submit  Answer"):
            user_ans = st.session_state.user_answer 
            if (user_ans == "True" and a) or (user_ans == "False" and not a):
                nx, ny = st.session_state.current[0]  + st.session_state.direction[0],  st.session_state.current[1]  + st.session_state.direction[1] 
                st.session_state.maze[nx][ny]  = 0  # 正确则变通路
                st.session_state.current  = (nx, ny)
                st.session_state.question_count  += 1
                if (nx, ny) in path:
                    index = path.index((nx,  ny))
                    st.session_state.path  = path[:index + 1]
                else:
                    path.append((nx,  ny))
                if not a:  # 如果答案是 false，检查是否封路
                    if not is_path_blocked(st.session_state.maze,  st.session_state.current,  st.session_state.direction): 
                        st.session_state.maze[st.session_state.current[0]][st.session_state.current[1]]  = 1
            else:
                st.error("Answer  is incorrect! The game will be reset!")
                reset_game()
            st.session_state.answering  = False
            st.session_state.current_question  = None
            st.session_state.user_answer  = None

    # 迷宫可视化（基于 HTML 表格）
    table_html = "<table style='border-collapse: collapse;'>"
    for i in range(maze_size):
        table_html += "<tr>"
        for j in range(maze_size):
            if (i, j) == st.session_state.current: 
                cell_content = "😀"
            elif (i, j) in st.session_state.path: 
                cell_content = "<div style='background-color: blue; width: 20px; height: 20px;'></div>"
            elif st.session_state.maze[i][j]  == 1:
                if i == 0 or i == maze_size - 1 or j == 0 or j == maze_size - 1:
                    cell_content = "⬛"
                else:
                    cell_content = "▓"
            elif st.session_state.maze[i][j]  == 2:
                cell_content = "❓"
            elif st.session_state.maze[i][j]  == 3:
                cell_content = "🚪"
            else:
                cell_content = " "
            table_html += f"<td style='border: 1px solid black; width: 20px; height: 20px; text-align: center;'>{cell_content}</td>"
        table_html += "</tr>"
    table_html += "</table>"
    st.markdown(table_html,  unsafe_allow_html=True)

    st.write(f"Number  of questions answered: {st.session_state.question_count}") 

    # 胜利条件判断
    if (st.session_state.current[0]  == maze_size - 2 or st.session_state.current[1]  == maze_size - 2) and st.session_state.maze[st.session_state.current[0]][st.session_state.current[1]]  == 3:
        st.balloons() 
        st.success("Successfully  escaped the maze!")
        if "maze" in st.session_state: 
            del st.session_state.maze 


if __name__ == "__main__":
    st.title("Chemistry  Maze Adventure")
    play_maze()