import pyrealsense2 as rs
import numpy as np
import cv2
import time
import winsound  # 用于播放声音报警（仅 Windows）

# 设置警报距离阈值 (单位：米)
ALERT_DISTANCE = 0.5  # 设定物体小于 0.5 米时触发报警

# 初始化报警频率和计时
alert_frequency_ms = 1000  # 默认报警间隔时间为 1000 毫秒
last_alert_time = 0  # 上一次报警时间

# 创建一个窗口，并为报警频率创建一个滑块
def update_frequency(val):
    global alert_frequency_ms
    alert_frequency_ms = val

cv2.namedWindow('Combined Image')
cv2.createTrackbar('Alert Frequency (ms)', 'Combined Image', alert_frequency_ms, 5000, update_frequency)

# 初始化相机管道和配置
pipeline = rs.pipeline()
config = rs.config()

# 启用深度流和RGB流
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# 开始传输
pipeline.start(config)

try:
    while True:
        # 获取深度和RGB帧
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        
        if not depth_frame or not color_frame:
            continue

        # 将深度数据和RGB数据转换为 numpy 数组
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # 将深度图缩放至 0-255，方便可视化
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

        # 获取图像尺寸
        height, width = depth_image.shape

        # 在 RGB 图像上标记出小于 0.5 米的像素区域
        for y in range(height):
            for x in range(width):
                distance = depth_frame.get_distance(x, y)
                if distance < ALERT_DISTANCE and distance > 0:
                    # 在 RGB 图像上绘制红色小圆点标记
                    cv2.circle(color_image, (x, y), 1, (0, 0, 255), -1)

        # 获取中心点的深度值
        center_distance = depth_frame.get_distance(width // 2, height // 2)

        # 合并 RGB 图像和深度图（半透明效果）
        combined_image = cv2.addWeighted(color_image, 0.5, depth_colormap, 0.5, 0)

        # 显示合并图像
        cv2.imshow('Combined Image', combined_image)

        # 检查是否接近警报距离并触发报警
        current_time = time.time() * 1000  # 当前时间，单位为毫秒
        if center_distance < ALERT_DISTANCE and center_distance > 0:
            if current_time - last_alert_time > alert_frequency_ms:
                print("警报：目标物体太近！距离为：", round(center_distance, 2), "米")
                # 播放警报声音（频率 1000 Hz，持续 500 ms）
                winsound.Beep(1000, 500)
                last_alert_time = current_time  # 更新最后报警时间

        # 按 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # 停止相机并关闭窗口
    pipeline.stop()
    cv2.destroyAllWindows()
