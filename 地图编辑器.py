import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, TextBox
import matplotlib.patches as patches
import pickle
import os
import matplotlib
from matplotlib import font_manager
import random

# 设置中文字体
def setup_chinese_font():
    """设置中文字体支持"""
    try:
        chinese_fonts = [
            'SimHei',           # 黑体
            'Microsoft YaHei',  # 微软雅黑  
            'KaiTi',            # 楷体
            'SimSun',           # 宋体
            'FangSong',         # 仿宋
            'Arial Unicode MS', # 跨平台字体
            'DejaVu Sans'       # 备用字体
        ]
        
        plt.rcParams['font.sans-serif'] = chinese_fonts
        plt.rcParams['axes.unicode_minus'] = False
        
        test_font = plt.rcParams['font.sans-serif'][0]
        print(f"已设置字体: {test_font}")
        return True
        
    except Exception as e:
        print(f"字体设置失败: {e}")
        return False

setup_chinese_font()

class TrafficLightConfig:
    """红绿灯配置类"""
    def __init__(self, position, cycle_time=None, initial_green=None):
        self.position = position  # (row, col)
        self.row, self.col = position
        
        # 随机生成红绿灯周期时间（30-120秒）
        if cycle_time is None:
            self.cycle_time = random.randint(30, 120)
        else:
            self.cycle_time = cycle_time
            
        # 随机初始状态（True为绿灯，False为红灯）
        if initial_green is None:
            self.initial_green = random.choice([True, False])
        else:
            self.initial_green = initial_green
            
        # 状态持续时间（周期的一半）
        self.green_duration = self.cycle_time / 2
        self.red_duration = self.cycle_time / 2
    
    def get_config_info(self):
        """获取配置信息"""
        state = "绿灯" if self.initial_green else "红灯"
        return f"位置{self.position}: 初始{state}, 周期{self.cycle_time}秒, 绿灯{self.green_duration}秒, 红灯{self.red_duration}秒"
    
    def to_dict(self):
        """转换为字典（用于保存）"""
        return {
            'position': self.position,
            'cycle_time': self.cycle_time,
            'initial_green': self.initial_green,
            'green_duration': self.green_duration,
            'red_duration': self.red_duration
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建红绿灯配置"""
        traffic_light = cls(data['position'], data['cycle_time'], data['initial_green'])
        return traffic_light

class MapEditor:
    def __init__(self, grid_size=(20, 20)):
        self.grid_size = grid_size
        self.rows, self.cols = grid_size
        self.roads = set()  # 道路集合
        self.start = None
        self.delivery_points = set()  # 外卖接收点集合
        self.traffic_lights = {}  # 位置 -> TrafficLightConfig对象
        self.current_mode = 'road'  # 'road', 'start', 'delivery', 'erase', 'traffic_light', 'rectangle_road', 'rectangle_erase'
        
        # 矩形绘制状态
        self.rectangle_start = None
        self.rectangle_end = None
        self.drawing_rectangle = False
        self.rectangle_preview = None
        
        # 性能优化：减少绘制调用
        self.last_update_time = 0
        self.update_delay = 0.1  # 秒
        
        # 创建图形界面 - 增加底部空间
        self.fig, self.ax = plt.subplots(figsize=(16, 12))
        plt.subplots_adjust(bottom=0.35)  # 增加底部空间以适应更多控件
        
        self.setup_ui()
        self.update_display()
        
    def setup_ui(self):
        """设置用户界面"""
        # 模式选择按钮 - 调整位置和大小以适应更大网格
        ax_mode = plt.axes([0.1, 0.15, 0.35, 0.15])
        self.mode_radio = RadioButtons(
            ax_mode, 
            ['道路', '起点', '外卖点', '擦除', '红绿灯', '矩形道路', '矩形擦除'],
            active=0
        )
        self.mode_radio.on_clicked(self.on_mode_change)
        
        # 第一行功能按钮
        ax_clear = plt.axes([0.5, 0.27, 0.08, 0.04])
        ax_save = plt.axes([0.6, 0.27, 0.08, 0.04])
        ax_load = plt.axes([0.7, 0.27, 0.08, 0.04])
        ax_reset = plt.axes([0.8, 0.27, 0.08, 0.04])
        
        self.btn_clear = Button(ax_clear, '清空道路')
        self.btn_save = Button(ax_save, '保存地图')
        self.btn_load = Button(ax_load, '加载地图')
        self.btn_reset = Button(ax_reset, '重置地图')
        
        # 第二行功能按钮
        ax_traffic_info = plt.axes([0.5, 0.21, 0.1, 0.04])
        ax_traffic_clear = plt.axes([0.62, 0.21, 0.12, 0.04])
        ax_delete_all_roads = plt.axes([0.75, 0.21, 0.12, 0.04])
        ax_clear_delivery = plt.axes([0.88, 0.21, 0.1, 0.04])
        
        self.btn_traffic_info = Button(ax_traffic_info, '红绿灯信息')
        self.btn_traffic_clear = Button(ax_traffic_clear, '清除所有红绿灯')
        self.btn_delete_all_roads = Button(ax_delete_all_roads, '删除所有道路')
        self.btn_clear_delivery = Button(ax_clear_delivery, '清除外卖点')
        
        # 第三行功能按钮 - 新增的大地图操作按钮
        ax_auto_roads = plt.axes([0.5, 0.15, 0.1, 0.04])
        ax_clear_center = plt.axes([0.62, 0.15, 0.12, 0.04])
        ax_create_city = plt.axes([0.75, 0.15, 0.12, 0.04])
        
        self.btn_auto_roads = Button(ax_auto_roads, '自动道路')
        self.btn_clear_center = Button(ax_clear_center, '清空中心区域')
        self.btn_create_city = Button(ax_create_city, '创建城市网格')
        
        # 网格大小控制
        ax_grid_text = plt.axes([0.5, 0.09, 0.06, 0.04])
        ax_grid_apply = plt.axes([0.57, 0.09, 0.06, 0.04])
        ax_grid_info = plt.axes([0.64, 0.09, 0.2, 0.04])
        
        self.grid_text = TextBox(ax_grid_text, '网格大小', initial=f'{self.rows}')
        self.grid_btn = Button(ax_grid_apply, '应用')
        self.grid_info_btn = Button(ax_grid_info, f'当前: {self.rows}x{self.cols} (最大100x100)')
        
        # 连接事件
        self.btn_clear.on_clicked(self.clear_roads)
        self.btn_save.on_clicked(self.save_map)
        self.btn_load.on_clicked(self.load_map)
        self.btn_reset.on_clicked(self.reset_map)
        self.btn_traffic_info.on_clicked(self.show_traffic_info)
        self.btn_traffic_clear.on_clicked(self.clear_traffic_lights)
        self.btn_delete_all_roads.on_clicked(self.delete_all_roads)
        self.btn_clear_delivery.on_clicked(self.clear_delivery_points)
        self.btn_auto_roads.on_clicked(self.create_auto_roads)
        self.btn_clear_center.on_clicked(self.clear_center_area)
        self.btn_create_city.on_clicked(self.create_city_grid)
        self.grid_btn.on_clicked(self.change_grid_size)
        
        # 连接鼠标事件
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_drag)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        
        print("外卖配送地图编辑器已启动！支持最大100x100网格")
        print("使用说明：")
        print("- 选择模式：道路/起点/外卖点/擦除/红绿灯/矩形道路/矩形擦除")
        print("- 点击单元格进行编辑")
        print("- 拖动鼠标可以连续编辑")
        print("- 矩形道路模式：点击拖动创建矩形区域道路")
        print("- 矩形擦除模式：点击拖动擦除矩形区域内所有元素")
        print("- 使用'自动道路'快速创建道路网络")
        print("- 使用'创建城市网格'生成城市风格道路")
        print("- 起点和外卖点必须在道路上设置")
        print("- 可以设置多个外卖接收点")
        print("- 红绿灯信息会保存在地图文件中")
        
    def on_mode_change(self, label):
        """模式改变回调"""
        mode_map = {
            '道路': 'road',
            '起点': 'start', 
            '外卖点': 'delivery',
            '擦除': 'erase',
            '红绿灯': 'traffic_light',
            '矩形道路': 'rectangle_road',
            '矩形擦除': 'rectangle_erase'
        }
        self.current_mode = mode_map[label]
        print(f"当前模式: {label}")
        
        # 退出矩形绘制模式
        if self.current_mode not in ['rectangle_road', 'rectangle_erase']:
            self.drawing_rectangle = False
            self.rectangle_start = None
            self.rectangle_end = None
            if self.rectangle_preview:
                self.rectangle_preview.remove()
                self.rectangle_preview = None
            self.update_display()
    
    def on_click(self, event):
        """鼠标点击事件"""
        if event.inaxes != self.ax:
            return
        
        col = int(event.xdata + 0.5)
        row = int(event.ydata + 0.5)
        
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if self.current_mode in ['rectangle_road', 'rectangle_erase']:
                # 开始矩形绘制
                self.rectangle_start = (row, col)
                self.drawing_rectangle = True
            else:
                self.modify_cell(row, col)
                self.throttled_update()
    
    def on_drag(self, event):
        """鼠标拖动事件"""
        if event.inaxes != self.ax or not event.button:
            return
        
        col = int(event.xdata + 0.5)
        row = int(event.ydata + 0.5)
        
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if self.current_mode in ['rectangle_road', 'rectangle_erase'] and self.drawing_rectangle:
                # 更新矩形预览
                self.rectangle_end = (row, col)
                self.update_rectangle_preview()
            elif self.current_mode not in ['rectangle_road', 'rectangle_erase']:
                self.modify_cell(row, col)
                self.throttled_update()
    
    def on_release(self, event):
        """鼠标释放事件"""
        if event.inaxes != self.ax:
            return
        
        if self.current_mode in ['rectangle_road', 'rectangle_erase'] and self.drawing_rectangle:
            col = int(event.xdata + 0.5)
            row = int(event.ydata + 0.5)
            
            if 0 <= row < self.rows and 0 <= col < self.cols:
                self.rectangle_end = (row, col)
                
                if self.current_mode == 'rectangle_road':
                    self.create_rectangle_roads()
                else:  # rectangle_erase
                    self.erase_rectangle_area()
                
            # 重置矩形绘制状态
            self.drawing_rectangle = False
            self.rectangle_start = None
            self.rectangle_end = None
            if self.rectangle_preview:
                self.rectangle_preview.remove()
                self.rectangle_preview = None
            self.update_display()
    
    def throttled_update(self):
        """节流更新，提高性能"""
        import time
        current_time = time.time()
        if current_time - self.last_update_time > self.update_delay:
            self.update_display()
            self.last_update_time = current_time
    
    def update_rectangle_preview(self):
        """更新矩形预览"""
        if not self.rectangle_start or not self.rectangle_end:
            return
            
        # 清除之前的预览
        if self.rectangle_preview:
            self.rectangle_preview.remove()
        
        # 计算矩形区域
        start_row, start_col = self.rectangle_start
        end_row, end_col = self.rectangle_end
        
        min_row = min(start_row, end_row)
        max_row = max(start_row, end_row)
        min_col = min(start_col, end_col)
        max_col = max(start_col, end_col)
        
        width = max_col - min_col + 1
        height = max_row - min_row + 1
        
        # 根据模式设置预览颜色
        if self.current_mode == 'rectangle_road':
            preview_color = 'lightblue'
            face_alpha = 0.4
        else:  # rectangle_erase
            preview_color = 'orange'
            face_alpha = 0.3
        
        # 创建预览矩形
        self.rectangle_preview = patches.Rectangle(
            (min_col - 0.5, min_row - 0.5), width, height,
            linewidth=2, edgecolor=preview_color, facecolor=preview_color, alpha=face_alpha
        )
        self.ax.add_patch(self.rectangle_preview)
        self.fig.canvas.draw()
    
    def create_rectangle_roads(self):
        """创建矩形区域道路"""
        if not self.rectangle_start or not self.rectangle_end:
            return
            
        start_row, start_col = self.rectangle_start
        end_row, end_col = self.rectangle_end
        
        min_row = min(start_row, end_row)
        max_row = max(start_row, end_row)
        min_col = min(start_col, end_col)
        max_col = max(start_col, end_col)
        
        # 统计添加的道路数量
        added_count = 0
        
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                pos = (row, col)
                # 检查位置是否有效且不是起点、外卖点或红绿灯
                if (0 <= row < self.rows and 0 <= col < self.cols and
                    pos != self.start and pos not in self.delivery_points and 
                    pos not in self.traffic_lights):
                    self.roads.add(pos)
                    added_count += 1
        
        print(f"添加了矩形道路区域: {min_row}x{min_col} 到 {max_row}x{max_col}, 共{added_count}个道路单元")
    
    def erase_rectangle_area(self):
        """擦除矩形区域内所有元素"""
        if not self.rectangle_start or not self.rectangle_end:
            return
            
        start_row, start_col = self.rectangle_start
        end_row, end_col = self.rectangle_end
        
        min_row = min(start_row, end_row)
        max_row = max(start_row, end_row)
        min_col = min(start_col, end_col)
        max_col = max(start_col, end_col)
        
        # 统计擦除的元素数量
        erased_roads = 0
        erased_traffic_lights = 0
        erased_start = False
        erased_delivery_points = 0
        
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                pos = (row, col)
                
                # 擦除道路
                if pos in self.roads:
                    self.roads.remove(pos)
                    erased_roads += 1
                
                # 擦除红绿灯
                if pos in self.traffic_lights:
                    del self.traffic_lights[pos]
                    erased_traffic_lights += 1
                
                # 擦除起点
                if pos == self.start:
                    self.start = None
                    erased_start = True
                
                # 擦除外卖点
                if pos in self.delivery_points:
                    self.delivery_points.remove(pos)
                    erased_delivery_points += 1
        
        # 输出擦除统计信息
        erase_info = []
        if erased_roads > 0:
            erase_info.append(f"{erased_roads}个道路")
        if erased_traffic_lights > 0:
            erase_info.append(f"{erased_traffic_lights}个红绿灯")
        if erased_start:
            erase_info.append("起点")
        if erased_delivery_points > 0:
            erase_info.append(f"{erased_delivery_points}个外卖点")
        
        if erase_info:
            print(f"矩形擦除区域 {min_row}x{min_col} 到 {max_row}x{max_col}: 清除了{', '.join(erase_info)}")
        else:
            print(f"矩形区域 {min_row}x{min_col} 到 {max_row}x{max_col} 内没有可擦除的元素")
    
    def modify_cell(self, row, col):
        """修改单元格状态"""
        pos = (row, col)
        
        if self.current_mode == 'road':
            # 在道路上添加时，如果该位置是外卖点或红绿灯，先移除它们
            if pos in self.delivery_points:
                self.delivery_points.remove(pos)
            if pos in self.traffic_lights:
                del self.traffic_lights[pos]
            if pos == self.start:
                self.start = None
            self.roads.add(pos)
        
        elif self.current_mode == 'start':
            # 设置起点（必须在道路上）
            if pos in self.roads and pos not in self.delivery_points and pos not in self.traffic_lights:
                self.start = pos
                print(f"设置起点: 位置{pos}")
            elif pos not in self.roads:
                print("错误：起点必须设置在道路上！")
            elif pos in self.delivery_points:
                print("错误：起点不能与外卖点重叠！")
            elif pos in self.traffic_lights:
                print("错误：起点不能与红绿灯重叠！")
        
        elif self.current_mode == 'delivery':
            # 添加或移除外卖点（必须在道路上）
            if pos in self.roads and pos != self.start and pos not in self.traffic_lights:
                if pos in self.delivery_points:
                    self.delivery_points.remove(pos)
                    print(f"移除外卖接收点: 位置{pos}，剩余{len(self.delivery_points)}个外卖点")
                else:
                    self.delivery_points.add(pos)
                    print(f"添加外卖接收点: 位置{pos}，当前共有{len(self.delivery_points)}个外卖点")
            elif pos not in self.roads:
                print("错误：外卖点必须设置在道路上！")
            elif pos == self.start:
                print("错误：外卖点不能与起点重叠！")
            elif pos in self.traffic_lights:
                print("错误：外卖点不能与红绿灯重叠！")
        
        elif self.current_mode == 'erase':
            # 擦除模式：移除任何类型的元素
            if pos in self.roads:
                self.roads.remove(pos)
            if pos in self.traffic_lights:
                del self.traffic_lights[pos]
                print(f"移除红绿灯: 位置{pos}")
            if pos == self.start:
                self.start = None
                print("移除起点")
            if pos in self.delivery_points:
                self.delivery_points.remove(pos)
                print(f"移除外卖接收点: 位置{pos}，剩余{len(self.delivery_points)}个外卖点")
        
        elif self.current_mode == 'traffic_light':
            # 添加或移除红绿灯（必须在道路上）
            if pos in self.roads and pos != self.start and pos not in self.delivery_points:
                if pos in self.traffic_lights:
                    del self.traffic_lights[pos]
                    print(f"移除红绿灯: 位置{pos}")
                else:
                    self.traffic_lights[pos] = TrafficLightConfig(pos)
                    tl = self.traffic_lights[pos]
                    print(f"添加红绿灯: {tl.get_config_info()}")
            elif pos not in self.roads:
                print("错误：红绿灯必须设置在道路上！")
            elif pos == self.start:
                print("错误：红绿灯不能与起点重叠！")
            elif pos in self.delivery_points:
                print("错误：红绿灯不能与外卖点重叠！")
    
    def update_display(self):
        """更新显示 - 优化大网格性能"""
        self.ax.clear()
        
        # 对于大网格，简化显示以提高性能
        if self.rows > 50 or self.cols > 50:
            self._update_display_large_grid()
        else:
            self._update_display_normal_grid()
        
        self.fig.canvas.draw()
    
    def _update_display_normal_grid(self):
        """正常网格显示（用于小到中等网格）"""
        # 设置颜色
        for i in range(self.rows):
            for j in range(self.cols):
                pos = (i, j)
                if pos == self.start:
                    color = 'lime'  # 亮绿色 - 起点
                elif pos in self.delivery_points:
                    color = 'orange'  # 橙色 - 外卖点
                elif pos in self.roads:
                    color = 'silver'  # 浅灰色 - 道路
                elif pos in self.traffic_lights:
                    # 红绿灯颜色：根据初始状态显示
                    traffic_light = self.traffic_lights[pos]
                    color = 'lightgreen' if traffic_light.initial_green else 'lightcoral'
                else:
                    color = 'white'  # 白色 - 非道路区域
                
                # 绘制矩形
                rect = patches.Rectangle(
                    (j-0.5, i-0.5), 1, 1, 
                    linewidth=1, 
                    edgecolor='gray',
                    facecolor=color,
                    alpha=0.8
                )
                self.ax.add_patch(rect)
                
                # 为外卖点添加编号
                if pos in self.delivery_points:
                    delivery_list = sorted(list(self.delivery_points))
                    index = delivery_list.index(pos)
                    self.ax.text(j, i, f'{index+1}', 
                                ha='center', va='center', 
                                fontsize=8, fontweight='bold',
                                color='darkred')
                
                # 为红绿灯添加文字标识
                if pos in self.traffic_lights:
                    traffic_light = self.traffic_lights[pos]
                    state_char = 'G' if traffic_light.initial_green else 'R'
                    cycle_char = str(traffic_light.cycle_time)
                    self.ax.text(j, i, f'{state_char}\n{cycle_char}', 
                                ha='center', va='center', 
                                fontsize=7, fontweight='bold',
                                color='darkgreen' if traffic_light.initial_green else 'darkred')
        
        self._setup_axes_and_labels()
    
    def _update_display_large_grid(self):
        """大网格显示优化（用于50x50以上网格）"""
        # 只绘制道路、起点、外卖点和红绿灯，跳过空白区域
        for i in range(self.rows):
            for j in range(self.cols):
                pos = (i, j)
                if pos in self.roads or pos == self.start or pos in self.delivery_points or pos in self.traffic_lights:
                    if pos == self.start:
                        color = 'lime'
                    elif pos in self.delivery_points:
                        color = 'orange'
                    elif pos in self.traffic_lights:
                        traffic_light = self.traffic_lights[pos]
                        color = 'lightgreen' if traffic_light.initial_green else 'lightcoral'
                    else:
                        color = 'silver'
                    
                    # 绘制矩形
                    rect = patches.Rectangle(
                        (j-0.5, i-0.5), 1, 1, 
                        linewidth=0.5,  # 更细的线条
                        edgecolor='gray',
                        facecolor=color,
                        alpha=0.8
                    )
                    self.ax.add_patch(rect)
                    
                    # 为大网格简化文字显示
                    if pos in self.delivery_points:
                        delivery_list = sorted(list(self.delivery_points))
                        index = delivery_list.index(pos)
                        fontsize = max(4, 100 // self.rows)  # 动态调整字体大小
                        self.ax.text(j, i, f'{index+1}', 
                                    ha='center', va='center', 
                                    fontsize=fontsize, fontweight='bold',
                                    color='darkred')
        
        self._setup_axes_and_labels()
        
        # 添加大网格提示
        self.ax.text(0.02, 0.98, f'大网格模式: {self.rows}x{self.cols}', 
                    transform=self.ax.transAxes, 
                    verticalalignment='top',
                    fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    def _setup_axes_and_labels(self):
        """设置坐标轴和标签"""
        # 设置坐标轴
        self.ax.set_xlim(-0.5, self.cols-0.5)
        self.ax.set_ylim(-0.5, self.rows-0.5)
        self.ax.set_aspect('equal')
        
        # 根据网格大小调整网格线显示
        if self.rows <= 50 and self.cols <= 50:
            self.ax.grid(True, color='gray', linestyle='-', linewidth=0.5)
            self.ax.set_xticks(range(self.cols))
            self.ax.set_yticks(range(self.rows))
        else:
            # 大网格显示较少的刻度
            x_ticks = range(0, self.cols, max(1, self.cols // 10))
            y_ticks = range(0, self.rows, max(1, self.rows // 10))
            self.ax.grid(True, color='gray', linestyle='-', linewidth=0.2)
            self.ax.set_xticks(x_ticks)
            self.ax.set_yticks(y_ticks)
        
        # 设置标题和标签
        self.ax.set_title(f'外卖配送地图编辑器 - {self.rows}x{self.cols}网格', fontsize=14, pad=20)
        
        # 显示状态信息
        start_text = f"起点: {self.start}" if self.start else "起点: 未设置"
        delivery_text = f"外卖点: {len(self.delivery_points)}个"
        status_text = f"道路: {len(self.roads)}个单元, 红绿灯: {len(self.traffic_lights)}个"
        
        self.ax.text(0.02, 0.02, status_text, 
                    transform=self.ax.transAxes, 
                    verticalalignment='bottom',
                    fontsize=11,
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        self.ax.text(0.02, 0.06, f"{start_text}, {delivery_text}", 
                    transform=self.ax.transAxes, 
                    verticalalignment='bottom',
                    fontsize=11,
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        # 添加图例说明
        legend_items = [
            "图例:",
            "绿色 = 起点", 
            "橙色 = 外卖接收点", 
            "浅灰 = 道路",
            "浅绿 = 初始绿灯", 
            "浅红 = 初始红灯"
        ]
        
        legend_text = "\n".join(legend_items)
        self.ax.text(0.7, 0.98, legend_text, 
                    transform=self.ax.transAxes, 
                    verticalalignment='top',
                    fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
        
        # 重要提示
        important_note = "重要：起点和外卖点必须在道路上！"
        self.ax.text(0.02, 0.95, important_note, 
                    transform=self.ax.transAxes, 
                    verticalalignment='top',
                    fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='red', alpha=0.3))
        
        # 矩形模式提示
        if self.current_mode == 'rectangle_road':
            rect_legend = "矩形道路模式: 点击并拖动创建矩形道路区域"
            self.ax.text(0.02, 0.90, rect_legend, 
                        transform=self.ax.transAxes, 
                        verticalalignment='top',
                        fontsize=9,
                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        elif self.current_mode == 'rectangle_erase':
            rect_legend = "矩形擦除模式: 点击并拖动擦除矩形区域内所有元素"
            self.ax.text(0.02, 0.90, rect_legend, 
                        transform=self.ax.transAxes, 
                        verticalalignment='top',
                        fontsize=9,
                        bbox=dict(boxstyle='round', facecolor='orange', alpha=0.7))
    
    def clear_roads(self, event=None):
        """清空所有道路（保留起点、外卖点和红绿灯）"""
        road_count = len(self.roads)
        self.roads.clear()
        # 如果起点不在道路上，清除起点
        if self.start and self.start not in self.roads:
            print(f"警告：起点{self.start}不在道路上，已自动清除")
            self.start = None
        self.update_display()
        print(f"已清空所有道路（{road_count}个道路单元），起点、外卖点和红绿灯保留")
    
    def delete_all_roads(self, event=None):
        """删除所有道路、起点、外卖点和红绿灯（完全清空地图）"""
        road_count = len(self.roads)
        traffic_count = len(self.traffic_lights)
        delivery_count = len(self.delivery_points)
        self.roads.clear()
        self.traffic_lights.clear()
        self.delivery_points.clear()
        self.start = None
        self.update_display()
        print(f"已删除所有元素：{road_count}个道路单元, {traffic_count}个红绿灯, {delivery_count}个外卖点，起点已清除")
    
    def clear_traffic_lights(self, event=None):
        """清除所有红绿灯"""
        traffic_count = len(self.traffic_lights)
        self.traffic_lights.clear()
        self.update_display()
        print(f"所有红绿灯已清除（{traffic_count}个）")
    
    def clear_delivery_points(self, event=None):
        """清除所有外卖点"""
        delivery_count = len(self.delivery_points)
        self.delivery_points.clear()
        self.update_display()
        print(f"所有外卖点已清除（{delivery_count}个）")
    
    def create_auto_roads(self, event=None):
        """自动创建道路网络"""
        self.delete_all_roads()
        
        # 创建主要道路
        for i in range(0, self.rows, max(2, self.rows // 10)):
            for j in range(self.cols):
                self.roads.add((i, j))
        
        for j in range(0, self.cols, max(2, self.cols // 10)):
            for i in range(self.rows):
                self.roads.add((i, j))
        
        # 设置起点
        if self.rows >= 2 and self.cols >= 2:
            self.start = (1, 1)
        
        # 添加一些外卖点
        delivery_candidates = []
        for i in range(1, self.rows-1):
            for j in range(1, self.cols-1):
                if (i, j) in self.roads and (i, j) != self.start:
                    delivery_candidates.append((i, j))
        
        # 随机选择外卖点，但不超过网格大小的1/20
        num_delivery = min(len(delivery_candidates), max(1, (self.rows * self.cols) // 200))
        if delivery_candidates:
            self.delivery_points = set(random.sample(delivery_candidates, num_delivery))
        
        self.update_display()
        print(f"已创建自动道路网络：{len(self.roads)}个道路单元，{len(self.delivery_points)}个外卖点")
    
    def clear_center_area(self, event=None):
        """清空中心区域，创建广场效果"""
        center_row = self.rows // 2
        center_col = self.cols // 2
        clear_radius = min(self.rows, self.cols) // 4
        
        cleared_count = 0
        for i in range(center_row - clear_radius, center_row + clear_radius + 1):
            for j in range(center_col - clear_radius, center_col + clear_radius + 1):
                if 0 <= i < self.rows and 0 <= j < self.cols:
                    pos = (i, j)
                    if pos in self.roads:
                        self.roads.remove(pos)
                        cleared_count += 1
                    if pos in self.traffic_lights:
                        del self.traffic_lights[pos]
                    if pos == self.start:
                        self.start = None
                    if pos in self.delivery_points:
                        self.delivery_points.remove(pos)
        
        self.update_display()
        print(f"已清空中心区域：半径{clear_radius}，清除了{cleared_count}个道路单元")
    
    def create_city_grid(self, event=None):
        """创建城市风格的道路网格"""
        self.delete_all_roads()
        
        # 创建主要干道
        for i in range(0, self.rows, max(3, self.rows // 15)):
            for j in range(self.cols):
                self.roads.add((i, j))
        
        for j in range(0, self.cols, max(3, self.cols // 15)):
            for i in range(self.rows):
                self.roads.add((i, j))
        
        # 创建次要道路
        for i in range(1, self.rows-1, max(2, self.rows // 30)):
            if i % (max(3, self.rows // 15)) != 0:  # 不在主干道上
                for j in range(1, self.cols-1):
                    self.roads.add((i, j))
        
        for j in range(1, self.cols-1, max(2, self.cols // 30)):
            if j % (max(3, self.cols // 15)) != 0:  # 不在主干道上
                for i in range(1, self.rows-1):
                    self.roads.add((i, j))
        
        # 设置起点在角落
        if self.rows >= 2 and self.cols >= 2:
            self.start = (1, 1)
        
        # 在外围添加外卖点
        delivery_locations = []
        margin = min(5, self.rows // 10, self.cols // 10)
        
        # 上边界
        for j in range(margin, self.cols - margin, max(2, self.cols // 20)):
            if (margin, j) in self.roads:
                delivery_locations.append((margin, j))
        
        # 下边界
        for j in range(margin, self.cols - margin, max(2, self.cols // 20)):
            if (self.rows - margin - 1, j) in self.roads:
                delivery_locations.append((self.rows - margin - 1, j))
        
        # 左边界
        for i in range(margin, self.rows - margin, max(2, self.rows // 20)):
            if (i, margin) in self.roads:
                delivery_locations.append((i, margin))
        
        # 右边界
        for i in range(margin, self.rows - margin, max(2, self.rows // 20)):
            if (i, self.cols - margin - 1) in self.roads:
                delivery_locations.append((i, self.cols - margin - 1))
        
        # 选择外卖点
        num_delivery = min(len(delivery_locations), max(5, (self.rows * self.cols) // 100))
        if delivery_locations:
            self.delivery_points = set(random.sample(delivery_locations, num_delivery))
        
        self.update_display()
        print(f"已创建城市风格道路网格：{len(self.roads)}个道路单元，{len(self.delivery_points)}个外卖点")
    
    def reset_map(self, event=None):
        """重置为默认外卖配送地图"""
        self.delete_all_roads()
        
        # 创建边界道路
        for i in range(self.rows):
            self.roads.add((i, 0))
            self.roads.add((i, self.cols-1))
        for j in range(self.cols):
            self.roads.add((0, j))
            self.roads.add((self.rows-1, j))
        
        # 设置起点（确保在道路上）
        self.start = (1, 1)
        
        # 创建一些内部道路
        for i in range(1, self.rows-1):
            self.roads.add((i, self.cols//2))
        for j in range(1, self.cols-1):
            self.roads.add((self.rows//2, j))
        
        # 添加几个默认的外卖点（确保在道路上）
        default_delivery_points = [
            (self.rows-2, self.cols-2),
            (1, self.cols-2),
            (self.rows-2, 1),
            (self.rows//2, self.cols//4),
            (self.rows//4, 3*self.cols//4)
        ]
        
        for point in default_delivery_points:
            if 0 <= point[0] < self.rows and 0 <= point[1] < self.cols and point in self.roads:
                self.delivery_points.add(point)
        
        self.update_display()
        print(f"已重置为默认外卖配送地图（带边界道路、十字路口和{len(self.delivery_points)}个外卖点）")
    
    def show_traffic_info(self, event=None):
        """显示红绿灯配置信息"""
        if not self.traffic_lights:
            print("当前没有红绿灯")
            return
            
        print("\n=== 红绿灯配置信息 ===")
        for pos, traffic_light in self.traffic_lights.items():
            print(f"  {traffic_light.get_config_info()}")
        print("====================\n")
    
    def save_map(self, event=None):
        """保存地图到文件"""
        if self.start is None:
            print("请先设置起点！")
            return
        
        # 检查起点是否在道路上
        if self.start not in self.roads:
            print("错误：起点必须设置在道路上！")
            return
            
        if len(self.delivery_points) == 0:
            print("请至少设置一个外卖接收点！")
            return
            
        # 检查所有外卖点是否在道路上
        invalid_delivery_points = [p for p in self.delivery_points if p not in self.roads]
        if invalid_delivery_points:
            print(f"错误：以下外卖点不在道路上: {invalid_delivery_points}")
            return
            
        map_data = {
            'grid_size': self.grid_size,
            'roads': list(self.roads),
            'start': self.start,
            'delivery_points': list(self.delivery_points),  # 保存外卖点列表
            'traffic_lights': {pos: tl.to_dict() for pos, tl in self.traffic_lights.items()}
        }
        
        filename = 'delivery_map.pkl'
        with open(filename, 'wb') as f:
            pickle.dump(map_data, f)
        
        print(f"外卖配送地图已保存到 {filename}")
        
        # 同时保存为文本文件便于查看
        with open('delivery_map.txt', 'w', encoding='utf-8') as f:
            f.write(f"网格大小: {self.grid_size}\n")
            f.write(f"起点: {self.start}\n")
            f.write(f"外卖点数量: {len(self.delivery_points)}\n")
            f.write(f"道路单元数量: {len(self.roads)}\n")
            f.write(f"红绿灯数量: {len(self.traffic_lights)}\n")
            f.write("外卖点位置:\n")
            for i, point in enumerate(sorted(self.delivery_points)):
                f.write(f"  外卖点{i+1}: {point}\n")
            f.write("道路位置:\n")
            for road in sorted(self.roads):
                f.write(f"  {road}\n")
            f.write("红绿灯配置:\n")
            for pos, tl in self.traffic_lights.items():
                state = "绿灯" if tl.initial_green else "红灯"
                f.write(f"  位置{pos}: 初始{state}, 周期{tl.cycle_time}秒, 绿灯时长{tl.green_duration}秒, 红灯时长{tl.red_duration}秒\n")
    
    def load_map(self, event=None):
        """从文件加载地图"""
        filename = 'delivery_map.pkl'
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                map_data = pickle.load(f)
            
            self.grid_size = map_data['grid_size']
            self.rows, self.cols = self.grid_size
            self.roads = set(map_data['roads'])
            self.start = map_data['start']
            self.delivery_points = set(map_data['delivery_points'])  # 加载外卖点
            
            # 加载红绿灯配置
            self.traffic_lights.clear()
            if 'traffic_lights' in map_data:
                for pos, tl_data in map_data['traffic_lights'].items():
                    self.traffic_lights[pos] = TrafficLightConfig.from_dict(tl_data)
            
            # 验证加载的数据
            if self.start not in self.roads:
                print(f"警告：加载的起点{self.start}不在道路上！")
            
            invalid_delivery_points = [p for p in self.delivery_points if p not in self.roads]
            if invalid_delivery_points:
                print(f"警告：以下外卖点不在道路上: {invalid_delivery_points}")
            
            self.update_display()
            print(f"外卖配送地图已从 {filename} 加载")
            print(f"包含 {len(self.roads)} 个道路单元, {len(self.delivery_points)} 个外卖点, {len(self.traffic_lights)} 个红绿灯")
        else:
            print("找不到地图文件，请先保存一个地图")
    
    def change_grid_size(self, event=None):
        """改变网格大小"""
        try:
            new_size = int(self.grid_text.text)
            if 5 <= new_size <= 100:
                self.grid_size = (new_size, new_size)
                self.rows, self.cols = self.grid_size
                self.delete_all_roads()
                print(f"网格大小已改为 {new_size}x{new_size}")
                self.update_display()
            else:
                print("网格大小必须在5-100之间")
        except ValueError:
            print("请输入有效的数字")
    
    def get_map_data(self):
        """获取地图数据"""
        return {
            'grid_size': self.grid_size,
            'roads': list(self.roads),
            'start': self.start,
            'delivery_points': list(self.delivery_points),
            'traffic_lights': self.traffic_lights
        }

def start_map_editor():
    """启动地图编辑器"""
    print("正在启动外卖配送地图编辑器...")
    print("功能：道路绘制、起点设置、多个外卖点配置、红绿灯配置、矩形道路创建、矩形擦除")
    print("使用说明：")
    print("- 支持最大100x100网格地图")
    print("- 选择模式：道路/起点/外卖点/擦除/红绿灯/矩形道路/矩形擦除")
    print("- 矩形道路模式：点击拖动创建矩形区域道路")
    print("- 矩形擦除模式：点击拖动擦除矩形区域内所有元素")
    print("- 使用'自动道路'快速创建道路网络")
    print("- 使用'创建城市网格'生成城市风格道路")
    print("- 起点和外卖点必须在道路上设置")
    print("- 可以设置多个外卖接收点，每个点都有编号")
    print("- 使用'清空道路'只清除道路，使用'删除所有道路'清除所有元素")
    
    editor = MapEditor(grid_size=(20, 20))
    plt.show()
    
    return editor.get_map_data()

# 如果直接运行这个文件，启动编辑器
if __name__ == "__main__":
    map_data = start_map_editor()
    print("\n最终地图数据:")
    print(f"网格大小: {map_data['grid_size']}")
    print(f"起点: {map_data['start']}")
    print(f"外卖点数量: {len(map_data['delivery_points'])}")
    print(f"道路单元数量: {len(map_data['roads'])}")
    print(f"红绿灯数量: {len(map_data['traffic_lights'])}")
    print("外卖点位置:")
    for i, point in enumerate(map_data['delivery_points']):
        print(f"  外卖点{i+1}: {point}")
