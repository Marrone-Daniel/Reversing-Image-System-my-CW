import pyrealsense2 as rs
import numpy as np
import cv2
import csv
import time
import pygame  # 导入pygame库

# 初始化pygame
pygame.mixer.init()

# 加载猫叫声的音频文件
meow_sound = pygame.mixer.Sound("meow.wav")

# 距离阈值定义（单位：米），从近到远分为四个区间
DISTANCE_THRESHOLDS = [0.3, 0.5, 1.0, 2.0]  # 0-0.3m, 0.3-0.5m, 0.5-1.0m, 1.0-2.0m

# 不同距离区域的报警频率（毫秒），距离越近报警频率越高
ALERT_FREQUENCIES = [100, 500, 1500, 5000]  # 每个区间对应的报警频率

# 初始化报警计时
last_alert_time = 0  # 上一次报警时间

# 创建CSV文件用于存储点击点的距离数据
csv_file = "distance_data.csv"
with open(csv_file, mode="w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["X", "Y", "Distance (m)"])  # 写入表头

    # 初始化相机管道和配置
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # 启动相机传输
    pipeline.start(config)

    # 创建对齐对象
    align = rs.align(rs.stream.color)

    # 创建一个窗口
    cv2.namedWindow('Combined Image')

    # 定义缩放因子
    depth_scale_factor = 1.0  
    color_scale_factor = 1.0  

    try:
        while True:
            # 获取深度和RGB帧并进行对齐
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            # 将深度数据和RGB数据转换为numpy数组
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # 将深度图缩放至0-255，方便可视化
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

            # 调整深度和RGB图像的大小
            depth_image_resized = cv2.resize(depth_colormap, (0, 0), fx=depth_scale_factor, fy=depth_scale_factor)
            color_image_resized = cv2.resize(color_image, (0, 0), fx=color_scale_factor, fy=color_scale_factor)

            # 获取调整后图像的尺寸
            depth_height, depth_width = depth_image_resized.shape[:2]
            color_height, color_width = color_image_resized.shape[:2]

            # 在RGB图像上标记出四个距离区间的像素区域
            for y in range(depth_height):
                for x in range(depth_width):
                    distance = depth_frame.get_distance(int(x / depth_scale_factor), int(y / depth_scale_factor))
                    if 0 < distance < DISTANCE_THRESHOLDS[0]:
                        cv2.circle(color_image_resized, (x, y), 1, (0, 0, 255), -1)  # 红色，表示最近
                    elif DISTANCE_THRESHOLDS[0] <= distance < DISTANCE_THRESHOLDS[1]:
                        cv2.circle(color_image_resized, (x, y), 1, (0, 128, 255), -1)  # 橙色，表示近距离
                    elif DISTANCE_THRESHOLDS[1] <= distance < DISTANCE_THRESHOLDS[2]:
                        cv2.circle(color_image_resized, (x, y), 1, (0, 255, 255), -1)  # 黄色，中等距离
                    elif DISTANCE_THRESHOLDS[2] <= distance < DISTANCE_THRESHOLDS[3]:
                        cv2.circle(color_image_resized, (x, y), 1, (0, 255, 0), -1)  # 绿色，较远

            # 合并调整后的RGB图像和深度图（半透明效果）
            combined_image = cv2.addWeighted(color_image_resized, 0.5, depth_image_resized, 0.5, 0)

            # 显示合并图像
            cv2.imshow('Combined Image', combined_image)

            # 检查整个画面的深度值，并根据距离区间触发不同频率的报警
            current_time = time.time() * 1000  # 当前时间，单位为毫秒
            closest_distance = float('inf')  # 初始化最近距离为无穷大
            closest_position = None  # 初始化最近距离的位置

            for y in range(depth_height):
                for x in range(depth_width):
                    distance = depth_frame.get_distance(int(x / depth_scale_factor), int(y / depth_scale_factor))
                    if distance > 0 and distance < closest_distance:  # 找到最小距离
                        closest_distance = distance
                        closest_position = (x, y)

            alarm_triggered = False  # 标记是否触发报警
            for i, threshold in enumerate(DISTANCE_THRESHOLDS):
                if closest_distance < threshold:
                    if current_time - last_alert_time > ALERT_FREQUENCIES[i]:
                        print(f"警报：目标物体太近！最近距离为：{round(closest_distance, 2)} 米 (位置: {closest_position})")
                        meow_sound.play()  # 播放猫叫声
                        last_alert_time = current_time  # 更新最后报警时间
                    alarm_triggered = True
                    break  # 一旦符合一个阈值区间，跳出循环避免重复检测

            # 鼠标点击以显示当前点的距离
            def mouse_callback(event, x, y, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN:
                    # 获取点击点的深度值并显示
                    distance = depth_frame.get_distance(int(x / depth_scale_factor), int(y / depth_scale_factor))
                    print(f"({x}, {y}) 处的距离: {distance:.2f} 米")

                    # 在合成图像上绘制当前点击点并显示距离信息
                    cv2.circle(combined_image, (x, y), 5, (0, 255, 0), -1)
                    cv2.putText(combined_image, f"{distance:.2f}m", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

                    # 将坐标和距离写入CSV文件
                    writer.writerow([x, y, distance])

            # 设置鼠标回调
            cv2.setMouseCallback('Combined Image', mouse_callback)

            # 按 'q' 键退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        # 停止相机并关闭窗口
        pipeline.stop()
        cv2.destroyAllWindows()
        print(f"程序结束，距离数据已保存到 {csv_file} 文件中。")

