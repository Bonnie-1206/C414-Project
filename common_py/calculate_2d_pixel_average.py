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

    # Check that all frames are the same size
    frame_shape = frames[0].shape
    if any(frame.shape != frame_shape for frame in frames):
        raise ValueError("All frames must have the same dimensions.")

    # Stack all frames into a 3D numpy array (assuming all frames are grayscale images)
    stacked_frames = np.stack(frames, axis=0)

    # Averages are calculated along the timeline (axis=0)
    averaged_frame = np.mean(stacked_frames, axis=0)

    return averaged_frame
    # Calculate the average along the first axis (the timeline) using numpy's mean function
    return np.mean(frames, axis=0)

def create_histogram(image):
    """
    Create and display a histogram of pixel values in a 2D image.

    Parameters:
    image (np.array): A 2D array representing an image.
    """
    
    plt.hist(image.ravel(), bins=256, range=[0,256])
    plt.title('Histogram of Averaged Pixel Values')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.show()

def main():
    # Load frames
   
    frames = [io.imread(f'frame{i}.png') for i in range(1, 6)]  # 根据实际情况修改

    # Calculate the average value of 2D pixels
    averaged_image = calculate_2d_pixel_average(frames)

    create_histogram(averaged_image)

if __name__ == "__main__":
    main()
