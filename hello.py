import json
import time
from datetime import datetime
from pynput import mouse, keyboard
from pynput.mouse import Button


class GameTracker:
    def __init__(self, output_file="game_tracking.json", game_title="Unnamed Game"):
        self.output_file = output_file
        self.game_title = game_title
        self.mouse_listener = None
        self.keyboard_listener = None
        self.is_recording = False
        self.movement_events = []
        self.current_direction = None
        self.current_start_time = 0
        self.start_time = 0
        self.last_position = (0, 0)
        self.key_states = {}
        self.direction_mapping = {
            'w': 'W',  # 上
            's': 'S',  # 下
            'a': 'A',  # 左
            'd': 'D',  # 右
            ' ': 'B',  # 射击/炸弹
            'l': 'L',  # 激光
        }

    def on_move(self, x, y):
        """处理鼠标移动事件"""
        if not self.is_recording:
            return

    def on_click(self, x, y, button, pressed):
        """处理鼠标点击事件"""
        if not self.is_recording:
            return

    def on_scroll(self, x, y, dx, dy):
        """处理鼠标滚轮事件"""
        if not self.is_recording:
            return

    def on_press(self, key):
        """处理键盘按下事件"""
        if not self.is_recording:
            return

        try:
            key_char = key.char.lower()
        except AttributeError:
            key_char = str(key)

        current_time = time.time() - self.start_time

        # 处理方向键按下
        if key_char in self.direction_mapping:
            self.key_states[key_char] = True
            self.update_direction(current_time)

        # 按ESC键停止记录
        if key == keyboard.Key.esc:
            self.stop_recording()
            return False

    def on_release(self, key):
        """处理键盘释放事件"""
        if not self.is_recording:
            return

        try:
            key_char = key.char.lower()
        except AttributeError:
            key_char = str(key)

        current_time = time.time() - self.start_time

        # 处理方向键释放
        if key_char in self.direction_mapping:
            if key_char in self.key_states:
                del self.key_states[key_char]
            self.update_direction(current_time)

    def update_direction(self, current_time):
        """更新当前方向并处理方向变更"""
        # 根据当前按下的键确定方向
        direction_chars = sorted([k for k in self.key_states if k in self.direction_mapping])
        new_direction = ''.join([self.direction_mapping[k] for k in direction_chars])

        # 如果方向发生变化，记录上一个方向的结束时间
        if new_direction != self.current_direction:
            if self.current_direction is not None:
                # 结束上一个方向的事件
                self.movement_events.append({
                    "direction": self.current_direction,
                    "start_time": self.current_start_time,
                    "end_time": current_time
                })

            # 开始新方向的事件
            self.current_direction = new_direction
            self.current_start_time = current_time

    def start_recording(self, duration=None):
        """开始记录游戏操作轨迹"""
        self.movement_events = []
        self.current_direction = None
        self.current_start_time = 0
        self.key_states = {}
        self.is_recording = True
        self.start_time = time.time()

        # 启动鼠标和键盘监听器
        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

        print(f"开始记录游戏操作轨迹... 按ESC键停止记录")

        # 如果设置了记录时长，则自动停止
        if duration:
            time.sleep(duration)
            self.stop_recording()

    def stop_recording(self):
        """停止记录游戏操作轨迹"""
        if not self.is_recording:
            return

        self.is_recording = False

        # 停止监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

        # 添加最后一个未完成的方向事件
        current_time = time.time() - self.start_time
        if self.current_direction is not None:
            self.movement_events.append({
                "direction": self.current_direction,
                "start_time": self.current_start_time,
                "end_time": current_time
            })

        print(f"已停止记录，共记录 {len(self.movement_events)} 个移动事件")
        self.save_trajectory()

    def save_trajectory(self):
        """保存轨迹数据到JSON文件"""
        try:
            data = {
                "game_metadata": {
                    "game_title": self.game_title,
                    "session_id": f"SA-{datetime.now().strftime('%Y-%m-%d')}-{int(time.time() % 10000):04d}",
                    "video_name": "",
                    "start_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "duration_seconds": time.time() - self.start_time
                },
                "movement_events": self.movement_events
            }

            with open(self.output_file, "w") as f:
                json.dump(data, f, indent=2)

            print(f"轨迹数据已保存到 {self.output_file}")
        except Exception as e:
            print(f"保存轨迹数据时出错: {e}")


if __name__ == "__main__":
    # 创建游戏轨迹采集器实例
    tracker = GameTracker(output_file="game_trajectory.json", game_title="Space Adventure v1.0")

    # 开始记录，默认持续60秒，可按ESC提前结束
    tracker.start_recording(duration=60)