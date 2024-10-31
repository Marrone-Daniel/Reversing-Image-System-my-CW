import pyrealsense2 as rs
import numpy as np
import cv2
import csv

# 初始化相机
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

# 启动相机
pipeline.start(config)

# 准备CSV文件
with open("distance_data.csv", mode="w", newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["X", "Y", "Distance (m)"]) 

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # 获取并显示距离
            distance = depth_frame.get_distance(x, y)
            print(f"({x}, {y}) 处的距离: {distance:.2f} 米")
            cv2.circle(depth_image, (x, y), 5, (0, 255, 0), -1)
            cv2.putText(depth_image, f"{distance:.2f}m", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            writer.writerow([x, y, distance])

    # 设置窗口和回调
    cv2.namedWindow('Depth Image')
    cv2.setMouseCallback('Depth Image', mouse_callback)

    try:
        while True:
            # 获取帧数据
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                continue

            # 转换深度数据并显示
            depth_image = np.asanyarray(depth_frame.get_data())
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            cv2.imshow('Depth Image', depth_colormap)
            if cv2.waitKey(1) == 27:  # ESC键退出
                break
    finally:
        # 停止相机
        pipeline.stop()
        print("程序结束，数据已保存到distance_data.csv文件中。")
