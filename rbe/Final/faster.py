import pyrealsense2 as rs
import numpy as np
import cv2
import csv
import time
import winsound  # 用于播放声音报警（仅 Windows）

# 常量定义
DISTANCE_THRESHOLDS = [0.3, 0.5, 1.0, 2.0]  #（米）
ALERT_FREQUENCIES = [100, 1500, 2500, 5000]  # 频率（毫秒）
csv_file = "distance_data.csv"  # CSV 文件名
click_data = []  # 存储点击点的数据

# 初始化相机管道
def initialize_camera():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)  # 深度
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)  # RGB
    pipeline.start(config)
    return pipeline, rs.align(rs.stream.color)

# 获取深度和RGB帧
def get_frames(pipeline, align):
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    return aligned_frames.get_depth_frame(), aligned_frames.get_color_frame()

# 检查最近距离并触发报警
def check_alerts(closest_distance, last_alert_time):
    for i, threshold in enumerate(DISTANCE_THRESHOLDS):
        if closest_distance < threshold:
            current_time = time.time() * 1000  # 当前时间（毫秒）
            if current_time - last_alert_time > ALERT_FREQUENCIES[i]:
                print(f"警报：目标物体太近！最近距离为：{round(closest_distance, 2)} 米")
                winsound.Beep(3000, 200)  # 播放报警声音
                return current_time  # 更新最后报警时间
    return last_alert_time

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        param.append((x, y, time.time()))  # 记录点击时间

def main():
    pipeline, align = initialize_camera()
    last_alert_time = 0

    cv2.namedWindow('Camera')  # 创建窗口

    # 打开 CSV 文件用于写入
    with open(csv_file, mode="w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["X", "Y", "Distance (m)"])  # 写入表头

        try:
            while True:
                depth_frame, color_frame = get_frames(pipeline, align)
                if not depth_frame or not color_frame:
                    continue

                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

                combined_image = cv2.addWeighted(color_image, 0.5, depth_colormap, 0.5, 0)

                # 获取深度值并计算最近距离
                distances = np.array([depth_frame.get_distance(x, y) for y in range(depth_frame.get_height()) for x in range(depth_frame.get_width())]).reshape((480, 640))
                closest_distance = np.min(distances[distances > 0]) if np.any(distances > 0) else float('inf')

                # 检查报警
                last_alert_time = check_alerts(closest_distance, last_alert_time)

                # 显示合成图像
                if click_data:
                    current_time = time.time()
                    for (x, y, click_time) in click_data:
                        # 检查点击是否在3秒内
                        if current_time - click_time <= 3:
                            distance = depth_frame.get_distance(x, y)
                            cv2.putText(combined_image, f"Distance: {distance:.2f} m", (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                cv2.imshow('Camera', combined_image)

                # 设置鼠标回调
                cv2.setMouseCallback('Camera', mouse_callback, click_data)

                # 写入数据到 CSV 文件
                if click_data:
                    for x, y, _ in click_data:
                        distance = depth_frame.get_distance(x, y)
                        print(f"({x}, {y}) 处的距离: {distance:.2f} 米")
                        writer.writerow([x, y, distance])
                    click_data.clear()  # 清空已处理的数据

                # 按 'q' 键退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            pipeline.stop()
            cv2.destroyAllWindows()
            print(f"程序结束，距离数据已保存到 {csv_file} 文件中。")

if __name__ == "__main__":
    main()
