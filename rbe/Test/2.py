import pyrealsense2 as rs
import numpy as np
import cv2
import time
import winsound  # Windows 声音

# 设置警报距离和频率
ALERT_DISTANCE = 0.5
alert_frequency_ms = 1000
last_alert_time = 0

# 更新频率
def update_frequency(val):
    global alert_frequency_ms
    alert_frequency_ms = val

cv2.namedWindow('Aligned RGB + Depth')
cv2.createTrackbar('Alert Frequency (ms)', 'Aligned RGB + Depth', alert_frequency_ms, 5000, update_frequency)

# 初始化 RealSense
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
pipeline.start(config)

try:
    while True:
        # 获取帧数据
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        # 转换图像
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        depth_image_resized = cv2.resize(depth_image, (color_image.shape[1], color_image.shape[0]))

        # 获取中心点距离
        height, width = depth_image_resized.shape
        center_x, center_y = width // 2, height // 2
        center_distance = depth_frame.get_distance(center_x, center_y) if 0 <= center_x < depth_frame.get_width() and 0 <= center_y < depth_frame.get_height() else None

        # 转换为伪彩色图
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image_resized, alpha=0.03), cv2.COLORMAP_JET)

        # 标注近距离区域
        mask = (depth_image_resized / 1000 < ALERT_DISTANCE) & (depth_image_resized > 0)
        color_image[mask] = [0, 0, 255]  # 红色标注

        # 合成图像
        combined_image = cv2.addWeighted(color_image, 0.5, depth_colormap, 0.5, 0)

        # 显示图像
        cv2.imshow('Aligned RGB + Depth', combined_image)

        # 触发报警
        current_time = time.time() * 1000
        if center_distance is not None and center_distance < ALERT_DISTANCE and current_time - last_alert_time > alert_frequency_ms:
            print(f"警报：中心物体距离 {center_distance:.2f} 米")
            winsound.Beep(1000, 500)
            last_alert_time = current_time

        # 按 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # 关闭管道和窗口
    pipeline.stop()
    cv2.destroyAllWindows()

