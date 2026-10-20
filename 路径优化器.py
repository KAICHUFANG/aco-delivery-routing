import numpy as np
import matplotlib.pyplot as plt
import pickle
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
import heapq
import random
import matplotlib
from matplotlib import font_manager
import os

# 设置中文字体支持
def setup_chinese_font():
    """设置中文字体支持"""
    try:
        # 方法1: 直接设置系统字体路径
        if os.name == 'nt':  # Windows系统
            font_paths = [
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
                'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
                'C:/Windows/Fonts/simkai.ttf',  # 楷体
                'C:/Windows/Fonts/simsun.ttc',  # 宋体
            ]
        else:  # Linux/Mac系统
            font_paths = [
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                '/System/Library/Fonts/PingFang.ttc',
            ]
        
        # 尝试添加字体文件
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_prop = font_manager.FontProperties(fname=font_path)
                font_manager.fontManager.addfont(font_path)
                print(f"成功添加字体: {font_path}")
        
        # 设置字体族
        plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 测试字体
        test_fonts = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        available_fonts = [f.name for f in font_manager.fontManager.ttflist]
        
        for font in test_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = [font]
                print(f"使用字体: {font}")
                return True
        
        print("警告: 使用默认字体，中文可能无法正常显示")
        return False
        
    except Exception as e:
        print(f"字体设置失败: {e}")
        return False

# 在程序开始时调用字体设置
setup_chinese_font()

class TrafficLightSimulator:
    """红绿灯模拟器 - 支持时间模拟"""
    def __init__(self, traffic_lights_config: Dict):
        self.traffic_lights = traffic_lights_config
        self.current_time = 0
        
    def update(self, delta_time: float):
        """更新红绿灯状态"""
        self.current_time += delta_time
        
    def get_light_state(self, position: Tuple[int, int]) -> str:
        """获取指定位置红绿灯的当前状态"""
        if position not in self.traffic_lights:
            return 'none'
            
        config = self.traffic_lights[position]
        cycle_time = config['cycle_time']
        cycle_position = self.current_time % cycle_time
        
        if config['initial_green']:
            return 'green' if cycle_position < config['green_duration'] else 'red'
        else:
            return 'red' if cycle_position < config['red_duration'] else 'green'
    
    def get_time_to_next_change(self, position: Tuple[int, int]) -> float:
        """获取距离下一次状态变化的时间"""
        if position not in self.traffic_lights:
            return 0
            
        config = self.traffic_lights[position]
        cycle_time = config['cycle_time']
        cycle_position = self.current_time % cycle_time
        
        if config['initial_green']:
            if cycle_position < config['green_duration']:
                return config['green_duration'] - cycle_position
            else:
                return cycle_time - cycle_position
        else:
            if cycle_position < config['red_duration']:
                return config['red_duration'] - cycle_position
            else:
                return cycle_time - cycle_position
    
    def reset(self):
        """重置模拟器时间"""
        self.current_time = 0

class MultiPathFinder:
    """多路径查找器 - 提供多条可选路径"""
    
    def __init__(self, roads: Set[Tuple[int, int]], k_paths: int = 3):
        self.roads = roads
        self.k_paths = k_paths
        
    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """曼哈顿距离启发函数"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """获取相邻位置"""
        row, col = pos
        neighbors = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            new_pos = (row + dr, col + dc)
            if new_pos in self.roads:
                neighbors.append(new_pos)
                
        return neighbors
    
    def yen_k_shortest_paths(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[List[Tuple[int, int]]]:
        """Yen's K最短路径算法"""
        # 首先找到最短路径
        shortest_path = self.a_star_search(start, goal)
        if not shortest_path:
            return []
            
        # 存储所有找到的路径
        k_paths = [shortest_path]
        potential_paths = []
        
        for k in range(1, self.k_paths):
            for i in range(len(k_paths[k-1]) - 1):
                # spur node: 当前路径的第i个节点
                spur_node = k_paths[k-1][i]
                # root path: 从起点到spur_node的路径
                root_path = k_paths[k-1][:i+1]
                
                # 临时移除边
                removed_edges = []
                for path in k_paths:
                    if len(path) > i and root_path == path[:i+1]:
                        next_node = path[i+1] if i+1 < len(path) else None
                        if next_node:
                            # 临时移除这条边
                            removed_edges.append((spur_node, next_node))
                
                # 寻找spur_node到终点的最短路径
                spur_path = self.a_star_search_with_removed_edges(spur_node, goal, removed_edges)
                
                if spur_path:
                    # 合并路径
                    total_path = root_path[:-1] + spur_path
                    if total_path not in potential_paths and total_path not in k_paths:
                        potential_paths.append(total_path)
                
                # 恢复移除的边 (在我们的实现中，由于是临时计算，不需要实际恢复)
            
            if not potential_paths:
                break
                
            # 选择最短的潜在路径
            potential_paths.sort(key=len)
            k_paths.append(potential_paths.pop(0))
        
        return k_paths
    
    def a_star_search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """标准的A*算法"""
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        while frontier:
            current_cost, current = heapq.heappop(frontier)
            
            if current == goal:
                break
                
            for next_pos in self.get_neighbors(current):
                new_cost = cost_so_far[current] + 1
                
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + self.heuristic(goal, next_pos)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
        
        if goal not in came_from:
            return []
            
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        
        return path
    
    def a_star_search_with_removed_edges(self, start, goal, removed_edges):
        """带有边移除的A*搜索"""
        removed_edges_set = set(removed_edges)
        
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        while frontier:
            current_cost, current = heapq.heappop(frontier)
            
            if current == goal:
                break
                
            for next_pos in self.get_neighbors(current):
                # 检查边是否被移除
                if (current, next_pos) in removed_edges_set:
                    continue
                    
                new_cost = cost_so_far[current] + 1
                
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + self.heuristic(goal, next_pos)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
        
        if goal not in came_from:
            return []
            
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        
        return path

class TimeOptimizedACO:
    """优化最小配送时间的ACO算法 - 支持多路径选择"""
    
    def __init__(self, map_data: Dict, 
                 ant_count: int = 10,
                 iterations: int = 50,
                 alpha: float = 1.0,
                 beta: float = 5.0,
                 evaporation_rate: float = 0.3,
                 q0: float = 0.7,
                 move_speed: float = 1.0,
                 k_paths: int = 3):  # 每对点之间的路径选项数
        
        self.map_data = map_data
        self.roads = set(map_data['roads'])
        self.start = map_data['start']
        self.delivery_points = map_data['delivery_points']
        self.traffic_lights_config = map_data.get('traffic_lights', {})
        self.move_speed = move_speed
        self.k_paths = k_paths
        
        # 算法参数
        self.ant_count = ant_count
        self.iterations = iterations
        self.alpha = alpha
        self.beta = beta
        self.evaporation_rate = evaporation_rate
        self.q0 = q0
        
        # 初始化组件
        self.multi_path_finder = MultiPathFinder(self.roads, k_paths)
        self.traffic_simulator = TrafficLightSimulator(self.traffic_lights_config)
        
        # 预计算所有点之间的多条路径
        self.all_points = [self.start] + self.delivery_points
        self.multi_path_matrix = self.compute_multi_path_matrix()
        
        # 初始化信息素（基于时间而不是距离）
        n = len(self.all_points)
        self.pheromone = np.ones((n, n))
        np.fill_diagonal(self.pheromone, 0)
        
        # 记录最佳结果
        self.best_path_indices = []
        self.best_delivery_time = float('inf')
        self.best_full_path = []
        self.best_waiting_time = 0
        self.convergence_history = []
        
        # 记录详细时间信息
        self.time_breakdown = {
            'total_time': 0,
            'moving_time': 0,
            'waiting_time': 0,
            'delivery_count': 0
        }
        
        # 记录每个段选择的路径
        self.best_segment_paths = []
        
    def compute_multi_path_matrix(self):
        """存储所有点之间的多条路径"""
        n = len(self.all_points)
        multi_path_matrix = [[[] for _ in range(n)] for _ in range(n)]
        
        print("预计算多路径矩阵...")
        for i in range(n):
            for j in range(n):
                if i != j:
                    paths = self.multi_path_finder.yen_k_shortest_paths(
                        self.all_points[i], self.all_points[j]
                    )
                    multi_path_matrix[i][j] = paths
                    if paths:
                        print(f"点 {i} -> 点 {j}: 找到 {len(paths)} 条路径")
                    else:
                        print(f"警告: 点 {i} -> 点 {j}: 未找到路径")
        
        return multi_path_matrix
    
    def calculate_path_delivery_time(self, path_indices: List[int]) -> Dict:
        """计算完整路径的配送时间，选择最优的子路径组合"""
        total_time = 0.0
        moving_time = 0.0
        waiting_time = 0.0
        full_path = []
        segment_paths = []
        
        # 重置交通模拟器
        self.traffic_simulator.reset()
        current_time = 0.0
        
        # 为每个路径段选择最优的子路径
        for i in range(len(path_indices) - 1):
            start_idx = path_indices[i]
            end_idx = path_indices[i + 1]
            
            # 获取这个段的所有可选路径
            available_paths = self.multi_path_matrix[start_idx][end_idx]
            if not available_paths:
                return {
                    'total_time': float('inf'), 
                    'moving_time': 0, 
                    'waiting_time': 0,
                    'full_path': [],
                    'segment_paths': []
                }
            
            # 评估每条路径的时间成本
            best_path = None
            best_time = float('inf')
            best_path_waiting = 0
            
            for path in available_paths:
                path_time, path_waiting = self.evaluate_path_time(path, current_time)
                if path_time < best_time:
                    best_time = path_time
                    best_path = path
                    best_path_waiting = path_waiting
            
            # 更新时间和路径
            total_time += best_time
            waiting_time += best_path_waiting
            current_time += best_time
            
            if full_path:
                full_path.extend(best_path[1:])
            else:
                full_path.extend(best_path)
            
            segment_paths.append(best_path)
            
            # 更新移动时间
            moving_time += (len(best_path) - 1) / self.move_speed
        
        return {
            'total_time': total_time,
            'moving_time': moving_time,
            'waiting_time': waiting_time,
            'full_path': full_path,
            'segment_paths': segment_paths
        }
    
    def evaluate_path_time(self, path: List[Tuple[int, int]], start_time: float) -> Tuple[float, float]:
        """评估单条路径的时间成本和等待时间"""
        current_time = start_time
        total_time = 0.0
        waiting_time = 0.0
        
        # 创建临时交通模拟器用于评估
        temp_traffic_sim = TrafficLightSimulator(self.traffic_lights_config)
        temp_traffic_sim.current_time = start_time
        
        for j in range(len(path) - 1):
            current_pos = path[j]
            next_pos = path[j + 1]
            
            # 移动时间
            move_time = 1.0 / self.move_speed
            total_time += move_time
            current_time += move_time
            
            # 更新红绿灯状态
            temp_traffic_sim.update(move_time)
            
            # 检查红绿灯
            light_state = temp_traffic_sim.get_light_state(next_pos)
            if light_state == 'red':
                wait_time = temp_traffic_sim.get_time_to_next_change(next_pos)
                total_time += wait_time
                waiting_time += wait_time
                current_time += wait_time
                temp_traffic_sim.update(wait_time)
        
        return total_time, waiting_time
    
    def run_optimization(self):
        """运行时间优化算法"""
        print("开始时间优化的ACO算法...")
        print(f"优化目标: 最小配送时间")
        print(f"需要访问的点: 起点 + {len(self.delivery_points)}个外卖点")
        print(f"红绿灯数量: {len(self.traffic_lights_config)}")
        print(f"每对点之间的路径选项: {self.k_paths}")
        print(f"迭代次数: {self.iterations}")
        
        n = len(self.all_points)
        
        # 在开始优化前初始化收敛历史
        self.convergence_history = []
        
        for iteration in range(self.iterations):
            ant_times = []
            ant_paths = []
            
            for ant_idx in range(self.ant_count):
                # 每只蚂蚁构建一个访问顺序
                visited = [0]  # 从起点开始
                unvisited = list(range(1, n))
                current_path = [0]
                
                while unvisited:
                    current_node = current_path[-1]
                    
                    # 选择下一个节点
                    next_node = self.select_next_node(current_node, unvisited)
                    if next_node is None:
                        break
                    
                    current_path.append(next_node)
                    unvisited.remove(next_node)
                
                if len(current_path) == n:  # 成功访问所有点
                    # 计算这个路径的配送时间
                    time_info = self.calculate_path_delivery_time(current_path)
                    total_time = time_info['total_time']
                    
                    if total_time < float('inf'):
                        ant_times.append(total_time)
                        ant_paths.append(current_path)
                        
                        # 更新最佳路径
                        if total_time < self.best_delivery_time:
                            self.best_delivery_time = total_time
                            self.best_path_indices = current_path.copy()
                            self.best_full_path = time_info['full_path']
                            self.best_waiting_time = time_info['waiting_time']
                            self.best_segment_paths = time_info['segment_paths']
                            
                            print(f"迭代 {iteration}: 发现更优解: 配送时间 = {total_time:.2f}秒, 等待时间 = {time_info['waiting_time']:.2f}秒")
            
            # 更新信息素（基于配送时间）
            self.update_pheromone(ant_paths, ant_times)
            
            # 每次迭代都记录当前最佳值
            self.convergence_history.append(self.best_delivery_time)
            
            # 每10次迭代输出一次进度信息
            if iteration % 10 == 0 or iteration == self.iterations - 1:
                successful_ants = len(ant_paths)
                avg_time = np.mean(ant_times) if ant_times else float('inf')
                print(f"迭代 {iteration}: 最佳时间 = {self.best_delivery_time:.2f}秒, 平均时间 = {avg_time:.2f}秒, 成功蚂蚁 = {successful_ants}/{self.ant_count}")
        
        # 最终时间分析
        if self.best_delivery_time < float('inf'):
            final_time_info = self.calculate_path_delivery_time(self.best_path_indices)
            self.time_breakdown = {
                'total_time': final_time_info['total_time'],
                'moving_time': final_time_info['moving_time'],
                'waiting_time': final_time_info['waiting_time'],
                'delivery_count': len(self.delivery_points)
            }
            
            print("\n" + "="*50)
            print("优化完成!")
            print("="*50)
            print(f"最小配送时间: {self.best_delivery_time:.2f} 秒")
            print(f"移动时间: {final_time_info['moving_time']:.2f} 秒")
            print(f"等待时间: {final_time_info['waiting_time']:.2f} 秒")
            print(f"访问顺序: {[self.all_points[i] for i in self.best_path_indices]}")
            print(f"路径节点数: {len(self.best_full_path)}")
            print(f"使用的路径段数: {len(self.best_segment_paths)}")
            print(f"收敛历史记录点数: {len(self.convergence_history)}")
        else:
            print("优化失败: 未找到有效路径")
    
    def select_next_node(self, current_node: int, unvisited: List[int]) -> Optional[int]:
        """选择下一个要访问的节点"""
        if not unvisited:
            return None
            
        # 预计算时间启发值
        time_heuristics = {}
        for next_node in unvisited:
            paths = self.multi_path_matrix[current_node][next_node]
            if paths:
                # 使用最短路径的长度作为启发值
                shortest_path = min(paths, key=len)
                time_heuristics[next_node] = 1.0 / len(shortest_path)
            else:
                time_heuristics[next_node] = 0
        
        probabilities = []
        total = 0.0
        
        for next_node in unvisited:
            if next_node in time_heuristics and time_heuristics[next_node] > 0:
                tau = self.pheromone[current_node][next_node] ** self.alpha
                eta = time_heuristics[next_node] ** self.beta
                prob = tau * eta
            else:
                prob = 0.0
            
            probabilities.append(prob)
            total += prob
        
        if total == 0:
            return random.choice(unvisited)
            
        probabilities = [p / total for p in probabilities]
        
        if random.random() < self.q0:
            return unvisited[np.argmax(probabilities)]
        else:
            r = random.random()
            cumulative = 0.0
            for i, prob in enumerate(probabilities):
                cumulative += prob
                if r <= cumulative:
                    return unvisited[i]
            return unvisited[-1]
    
    def update_pheromone(self, ant_paths: List[List[int]], ant_times: List[float]):
        """基于配送时间更新信息素"""
        # 信息素蒸发
        self.pheromone *= (1 - self.evaporation_rate)
        
        # 蚂蚁释放信息素（时间越短，信息素越多）
        for path, delivery_time in zip(ant_paths, ant_times):
            time_quality = 1.0 / delivery_time  # 配送时间越短，质量越高
            
            for i in range(len(path) - 1):
                node1, node2 = path[i], path[i+1]
                self.pheromone[node1][node2] += time_quality
                self.pheromone[node2][node1] += time_quality
    
    def visualize_optimization(self):
        """可视化优化结果"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 绘制地图和路径
        self.plot_map_with_path(ax1)
        
        # 绘制收敛曲线 - 确保显示每个迭代的数据
        if len(self.convergence_history) > 0:
            iterations = list(range(len(self.convergence_history)))
            ax2.plot(iterations, self.convergence_history, 'b-', linewidth=1.5, marker='', markersize=1)
            ax2.set_xlabel('迭代次数')
            ax2.set_ylabel('配送时间 (秒)')
            ax2.set_title(f'算法收敛曲线 (共{len(self.convergence_history)}次迭代)')
            ax2.grid(True, alpha=0.3)
            
            # 添加收敛说明
            if len(self.convergence_history) > 1:
                improvement = self.convergence_history[0] - self.convergence_history[-1]
                ax2.text(0.02, 0.98, f'总改进: {improvement:.2f}秒\n最终时间: {self.convergence_history[-1]:.2f}秒', 
                        transform=ax2.transAxes, fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        else:
            ax2.text(0.5, 0.5, '无收敛数据', transform=ax2.transAxes, 
                    ha='center', va='center', fontsize=12)
            ax2.set_title('算法收敛曲线')
        
        # 绘制时间分解饼图
        if self.best_delivery_time < float('inf'):
            times = [self.time_breakdown['moving_time'], self.time_breakdown['waiting_time']]
            labels = ['移动时间', '等待时间']
            colors = ['lightblue', 'lightcoral']
            ax3.pie(times, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax3.set_title('时间分解')
        else:
            ax3.text(0.5, 0.5, '无有效路径', transform=ax3.transAxes, 
                    ha='center', va='center', fontsize=12)
            ax3.set_title('时间分解')
        
        # 绘制路径统计
        ax4.axis('off')
        if self.best_delivery_time < float('inf'):
            stats_text = f"""
优化结果统计:
----------------
总配送时间: {self.time_breakdown['total_time']:.2f}秒
移动时间: {self.time_breakdown['moving_time']:.2f}秒
等待时间: {self.time_breakdown['waiting_time']:.2f}秒
外卖点数量: {self.time_breakdown['delivery_count']}
路径节点数: {len(self.best_full_path)}
路径段数: {len(self.best_segment_paths)}
路径选项数: {self.k_paths}
迭代次数: {len(self.convergence_history)}
            """
            ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, fontsize=12,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        else:
            ax4.text(0.1, 0.9, "优化失败: 未找到有效路径", transform=ax4.transAxes, fontsize=12,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
        
        plt.tight_layout()
        plt.show()
    
    def plot_map_with_path(self, ax):
        """在地图上绘制最佳路径"""
        rows, cols = self.map_data['grid_size']
        
        # 绘制网格
        for i in range(rows):
            for j in range(cols):
                pos = (i, j)
                if pos == self.start:
                    color = 'lime'
                elif pos in self.delivery_points:
                    color = 'orange'
                elif pos in self.roads:
                    color = 'silver'
                elif pos in self.traffic_lights_config:
                    # 根据当前红绿灯状态显示颜色
                    self.traffic_simulator.reset()
                    light_state = self.traffic_simulator.get_light_state(pos)
                    color = 'lightgreen' if light_state == 'green' else 'lightcoral'
                else:
                    color = 'white'
                
                rect = plt.Rectangle((j-0.5, i-0.5), 1, 1, 
                                   linewidth=1, edgecolor='gray',
                                   facecolor=color, alpha=0.8)
                ax.add_patch(rect)
                
                # 标记外卖点编号
                if pos in self.delivery_points:
                    delivery_list = sorted(list(self.delivery_points))
                    index = delivery_list.index(pos)
                    ax.text(j, i, f'{index+1}', 
                           ha='center', va='center', 
                           fontsize=8, fontweight='bold', color='darkred')
                
                # 标记红绿灯位置和状态
                if pos in self.traffic_lights_config:
                    self.traffic_simulator.reset()
                    light_state = self.traffic_simulator.get_light_state(pos)
                    state_char = 'G' if light_state == 'green' else 'R'
                    cycle_time = self.traffic_lights_config[pos]['cycle_time']
                    
                    ax.text(j, i+0.3, state_char, 
                           ha='center', va='center', 
                           fontsize=9, fontweight='bold',
                           color='darkgreen' if light_state == 'green' else 'darkred')
                    ax.text(j, i-0.3, f'{cycle_time}s', 
                           ha='center', va='center', 
                           fontsize=7, color='black')
        
        # 绘制完整路径
        if hasattr(self, 'best_full_path') and self.best_full_path:
            path_x = [pos[1] for pos in self.best_full_path]
            path_y = [pos[0] for pos in self.best_full_path]
            ax.plot(path_x, path_y, 'b-', linewidth=2, alpha=0.7, label='配送路径')
            ax.plot(path_x, path_y, 'bo', markersize=2, alpha=0.5)
        
        # 标记起点和外卖点
        ax.plot(self.start[1], self.start[0], 'gs', markersize=10, label='起点')
        for delivery in self.delivery_points:
            ax.plot(delivery[1], delivery[0], 'ro', markersize=8, label='外卖点')
    
        ax.set_xlim(-0.5, cols-0.5)
        ax.set_ylim(-0.5, rows-0.5)
        ax.set_aspect('equal')
        
        # 使用中文标题
        title = f"最佳配送路径 (总时间: {self.best_delivery_time:.2f}秒)"
        ax.set_title(title)
        ax.grid(True)
        
        # 显示图例（去重）
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right')
    
    def visualize_path_options(self, point_a: Tuple[int, int], point_b: Tuple[int, int]):
        """可视化两点之间的多条路径选项"""
        # 找到对应的索引
        if point_a in self.all_points and point_b in self.all_points:
            idx_a = self.all_points.index(point_a)
            idx_b = self.all_points.index(point_b)
            paths = self.multi_path_matrix[idx_a][idx_b]
            
            if not paths:
                print(f"未找到从 {point_a} 到 {point_b} 的路径")
                return
            
            # 创建子图
            fig, axes = plt.subplots(1, min(self.k_paths, len(paths)), figsize=(15, 5))
            if min(self.k_paths, len(paths)) == 1:
                axes = [axes]
            
            for i, (ax, path) in enumerate(zip(axes, paths)):
                self.plot_single_path_option(ax, path, point_a, point_b, f"路径选项 {i+1}")
            
            plt.tight_layout()
            plt.show()
        else:
            print("指定的点不在配送点列表中")
    
    def plot_single_path_option(self, ax, path, start, end, title):
        """绘制单条路径选项"""
        rows, cols = self.map_data['grid_size']
        
        # 绘制基础地图
        for i in range(rows):
            for j in range(cols):
                pos = (i, j)
                if pos == start:
                    color = 'lime'
                elif pos == end:
                    color = 'orange'
                elif pos in self.roads:
                    color = 'silver'
                elif pos in self.traffic_lights_config:
                    color = 'yellow'
                else:
                    color = 'white'
                
                rect = plt.Rectangle((j-0.5, i-0.5), 1, 1, 
                                   linewidth=1, edgecolor='gray',
                                   facecolor=color, alpha=0.8)
                ax.add_patch(rect)
        
        # 绘制路径
        if path:
            path_x = [pos[1] for pos in path]
            path_y = [pos[0] for pos in path]
            ax.plot(path_x, path_y, 'b-', linewidth=3, alpha=0.8, label='路径')
            ax.plot(path_x, path_y, 'bo', markersize=4, alpha=0.6)
            
            # 评估路径时间
            path_time, wait_time = self.evaluate_path_time(path, 0)
            ax.text(0.05, 0.95, f'时间: {path_time:.2f}秒\n等待: {wait_time:.2f}秒', 
                   transform=ax.transAxes, fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.set_xlim(-0.5, cols-0.5)
        ax.set_ylim(-0.5, rows-0.5)
        ax.set_aspect('equal')
        ax.set_title(title)
        ax.grid(True)

def create_test_map():
    """创建测试地图数据"""
    grid_size = (15, 15)
    roads = [(i, j) for i in range(15) for j in range(15)]
    
    map_data = {
        'grid_size': grid_size,
        'roads': roads,
        'start': (1, 1),
        'delivery_points': [
            (5, 5), (10, 10), (12, 3), (8, 8), (3, 12)
        ],
        'traffic_lights': {
            (5, 5): {'cycle_time': 20, 'initial_green': True, 'green_duration': 10, 'red_duration': 10},
            (10, 10): {'cycle_time': 30, 'initial_green': False, 'green_duration': 15, 'red_duration': 15},
            (7, 7): {'cycle_time': 25, 'initial_green': True, 'green_duration': 12, 'red_duration': 13},
            (3, 3): {'cycle_time': 18, 'initial_green': False, 'green_duration': 8, 'red_duration': 10}
        }
    }
    
    # 保存测试地图
    with open('delivery_map.pkl', 'wb') as f:
        pickle.dump(map_data, f)
    
    return map_data

def test_time_optimized_aco(iterations=100):
    """测试时间优化的ACO算法"""
    try:
        with open('delivery_map.pkl', 'rb') as f:
            map_data = pickle.load(f)
        print("成功加载地图数据")
    except FileNotFoundError:
        print("创建测试地图...")
        map_data = create_test_map()
    
    optimizer = TimeOptimizedACO(
        map_data=map_data,
        k_paths=3,
        ant_count=4,
        iterations=iterations,  # 使用参数设置迭代次数
        alpha=0.8,
        beta=2.0,
        evaporation_rate=0.5,
        q0=0.5,
        move_speed=1.0
    )
    
    optimizer.run_optimization()
    optimizer.visualize_optimization()
    
    return optimizer

if __name__ == "__main__":
    # 测试不同的迭代次数
    test_time_optimized_aco(iterations=50)   # 50次迭代
    # test_time_optimized_aco(iterations=100)  # 100次迭代  
    # test_time_optimized_aco(iterations=200)  # 200次迭代
