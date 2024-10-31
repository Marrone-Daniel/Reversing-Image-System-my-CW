import cv2
import numpy as np
print(cv2.getBuildInformation())

# 创建一个空白图像
image = np.zeros((400, 400, 3), dtype=np.uint8)

# 创建窗口
cv2.namedWindow('Depth Image', cv2.WINDOW_NORMAL)

# 显示图像
cv2.imshow('Depth Image', image)

# 等待按键
cv2.waitKey(0)

# 销毁所有窗口
cv2.destroyAllWindows()
