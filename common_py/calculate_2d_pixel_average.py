import numpy as np
import matplotlib.pyplot as plt
from skimage import io

def calculate_2d_pixel_nearest_neighbor(frames):
    """
    使用最近邻算法计算一系列帧的2D像素平均值。

    参数:
    frames (list of np.array): 代表图像帧的2D数组列表。

    返回:
    np.array: 代表平均像素值的2D数组。
    """
    if not frames:
        raise ValueError("The frame list is empty.")

    frame_shape = frames[0].shape
    if any(frame.shape != frame_shape for frame in frames):
        raise ValueError("All frames must have the same dimensions.")

    stacked_frames = np.stack(frames, axis=0)

    # 初始化一个数组来保存最近邻平均值
    #Initialize an array to hold the nearest neighbor average
    nearest_neighbor_average = np.zeros(frame_shape)

    # 遍历每个像素
    # Iterate over each pixel
    for i in range(frame_shape[0]):
        for j in range(frame_shape[1]):
            pixel_values = stacked_frames[:, i, j]
            average = np.mean(pixel_values)
            # 找到最接近平均值的像素值
            # Find the pixel value closest to the average
            nearest = min(pixel_values, key=lambda x: abs(x - average))
            nearest_neighbor_average[i, j] = nearest

    return nearest_neighbor_average

def create_histogram(image):
    """
    创建并显示2D图像中像素值的直方图。

    参数:
    image (np.array): 代表图像的2D数组。
    """
    plt.hist(image.ravel(), bins=256, range=[0,256])
    plt.title('Histogram of Nearest Neighbor Pixel Values')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.show()

def main():
    # 加载帧 - 根据实际情况修改文件名或路径
    frames = [io.imread(f'frame{i}.png') for i in range(1, 6)]
    #change name of the file to the name of the file you want to load

    nearest_neighbor_image = calculate_2d_pixel_nearest_neighbor(frames)

    create_histogram(nearest_neighbor_image)

if __name__ == "__main__":
    main()
