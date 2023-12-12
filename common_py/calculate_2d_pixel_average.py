import numpy as np
import matplotlib.pyplot as plt
from skimage import io

def calculate_2d_pixel_average(frames):
    """
    Calculate the average of pixel values across a sequence of 2D frames.

    Parameters:
    frames (list of np.array): List of 2D arrays representing image frames.

    Returns:
    np.array: A 2D array representing the average pixel values.
    """
    if not frames:
        raise ValueError("The frame list is empty.")

    # 检查所有帧的尺寸是否一致
    frame_shape = frames[0].shape
    if any(frame.shape != frame_shape for frame in frames):
        raise ValueError("All frames must have the same dimensions.")

    # 将所有帧堆叠到一个3D numpy数组中（假设所有帧都是灰度图像）
    stacked_frames = np.stack(frames, axis=0)

    # 沿着时间轴（axis=0）计算平均值
    averaged_frame = np.mean(stacked_frames, axis=0)

    return averaged_frame
    # 使用numpy的mean函数沿着第一个轴（时间轴）计算平均值
    return np.mean(frames, axis=0)

def create_histogram(image):
    """
    Create and display a histogram of pixel values in a 2D image.

    Parameters:
    image (np.array): A 2D array representing an image.
    """
    # 展平图像并创建直方图
    plt.hist(image.ravel(), bins=256, range=[0,256])
    plt.title('Histogram of Averaged Pixel Values')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.show()

def main():
    # 这里是加载帧的例子，您需要根据您的情况来加载帧
    # 假设有frame1.png, frame2.png等文件
    frames = [io.imread(f'frame{i}.png') for i in range(1, 6)]  # 根据实际情况修改

    # 计算2D像素的平均值
    averaged_image = calculate_2d_pixel_average(frames)

    # 创建并显示直方图
    create_histogram(averaged_image)

if __name__ == "__main__":
    main()
