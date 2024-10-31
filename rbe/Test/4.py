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
        param.append((x, y))  

def main():
    pipeline, align = initialize_camera()
    last_alert_time = 0

    cv2.namedWindow('合成图像')  # 创建窗口

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

                # 创建透明覆盖层
                overlay = np.zeros_like(color_image)

                # 获取深度值并计算最近距离
                distances = np.array([depth_frame.get_distance(x, y) for y in range(depth_frame.get_height()) for x in range(depth_frame.get_width())]).reshape((480, 640))
                closest_distance = np.min(distances[distances > 0]) if np.any(distances > 0) else float('inf')

                # 检查报警
                last_alert_time = check_alerts(closest_distance, last_alert_time)

                # 标记不同深度区域
                for y in range(depth_frame.get_height()):
                    for x in range(depth_frame.get_width()):
                        distance = distances[y, x]
                        color = (0, 0, 0)  # 默认黑色
                        if 0 < distance < DISTANCE_THRESHOLDS[0]:
                            color = (0, 0, 255)  # 红色，最近
                        elif DISTANCE_THRESHOLDS[0] <= distance < DISTANCE_THRESHOLDS[1]:
                            color = (0, 165, 255)  # 橙色，近距离
                        elif DISTANCE_THRESHOLDS[1] <= distance < DISTANCE_THRESHOLDS[2]:
                            color = (0, 255, 255)  # 黄色，中等距离
                        elif DISTANCE_THRESHOLDS[2] <= distance < DISTANCE_THRESHOLDS[3]:
                            color = (0, 255, 0)  # 绿色，较远
                        
                        # 在覆盖层上绘制半透明圆点
                        cv2.circle(overlay, (x, y), 1, color, -1)

                # 合成覆盖层与原始图像
                combined_image = cv2.addWeighted(combined_image, 1.0, overlay, 0.3, 0)

                # 显示合成图像
                cv2.imshow('合成图像', combined_image)

                # 设置鼠标回调
                cv2.setMouseCallback('合成图像', mouse_callback, click_data)

                # 写入数据到 CSV 文件
                if click_data:
                    for x, y in click_data:
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
