import sys
sys.path.append("/home/cqzhao/projects/matrix/")
sys.path.append("../../")


import os


import matplotlib.pyplot as plt


import time


import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

import matplotlib.pyplot as plt


import numpy as np

from common_py.dataIO import loadImgs_pytorch
from common_py.evaluationBS import evaluation_numpy
from common_py.evaluationBS import evaluation_numpy_entry
from common_py.dataIO import saveImg
from common_py.dataIO import saveMod

from common_py.dataIO import readImg_byFilesIdx
from common_py.dataIO import readImg_byFilesIdx_pytorch

from common_py.dataIO import loadFiles_plus

from function.prodis import getEmptyCF
from function.prodis import getHist_plus
from function.prodis import getEmptyCF_plus
from function.prodis import ProductDis_plus
from function.prodis import ProductDis_multi
from function.prodis import ProductDis_multiW
from function.prodis import ProductDis_fast
from function.prodis import getRandCF
from function.prodis import getRandCF_plus
from function.prodis import getRandCF_multi
from function.prodis import ProductDis_test
from function.prodis import corDisVal

from bayesian.bayesian import bayesRefine_iterative_gpu

from binarymask.binarymask import getTrainBinMask


from function.prodis import DifferentiateDis_multi


from params_input.params_input import QParams



import imageio


from torch.autograd import Variable

np.set_printoptions(threshold=np.inf)



# print("Hello World")
#
#
# showHello()
#


# def video2tpixels(imgs, curidx):
#
#     return None




class GaussianBlurConv(nn.Module):
    def __init__(self, channels=3):
        super(GaussianBlurConv, self).__init__()
        self.channels = channels
        # print("channels: ", channels.shape)
        kernel = [[0.00078633, 0.00655965, 0.01330373, 0.00655965, 0.00078633],
                  [0.00655965, 0.05472157, 0.11098164, 0.05472157, 0.00655965],
                  [0.01330373, 0.11098164, 0.22508352, 0.11098164, 0.01330373],
                  [0.00655965, 0.05472157, 0.11098164, 0.05472157, 0.00655965],
                  [0.00078633, 0.00655965, 0.01330373, 0.00655965, 0.00078633]]

        kernel = torch.FloatTensor(kernel).unsqueeze(0).unsqueeze(0)    # (H, W) -> (1, 1, H, W)
        kernel = kernel.expand((int(channels), 1, 5, 5))
        self.weight = nn.Parameter(data=kernel, requires_grad=False)

    def __call__(self, x):
        x = F.conv2d(x, self.weight, padding=2, groups=self.channels)
        return x



def getConvImgs(imgs):

    frames_im, row_im, column_im, byte_im = imgs.shape

    gaussian = GaussianBlurConv()

    re_imgs = torch.abs(imgs - imgs)
    for i in range(frames_im):
        re_imgs[i] = gaussian(imgs[i, :, :, :].unsqueeze(dim = 0).permute(0, 3, 1, 2)).squeeze().permute(1, 2, 0)

        print("total num:", frames_im, " i = ", i)


    return re_imgs



def getConvImgs_test(imgs):

    frames_im, row_im, column_im, byte_im = imgs.shape

    gaussian = GaussianBlurConv()

#    re_imgs = torch.abs(imgs - imgs)
    for i in range(frames_im):
        imgs[i] = gaussian(imgs[i, :, :, :].unsqueeze(dim = 0).permute(0, 3, 1, 2)).squeeze().permute(1, 2, 0)

        print("total num:", frames_im, " i = ", i)


    return imgs



#    im = imgs[100, :, :, :]
#    convim = convimgs[100, :, :, :]


#
#     im = imgs[100, :, :, :]
#     inputim = im.unsqueeze(dim = 0).permute(0, 3, 1, 2)
#
#
# #    convim = gaussian(im.unsqueeze(dim = 0).permute(0, 3, 1, 2))
#
#     print(im.shape)
#     convim = gaussian(inputim)
#
#     convim = convim.squeeze().permute(1, 2, 0)
#
#     print(convim.shape)




def getDisData():
    pa_im = '/home/cqzhao/dataset/dataset2014/dataset/dynamicBackground/fountain01/input'
#    pa_im = 'D:/dataset/dataset2014/dataset/dynamicBackground/fountain01/input'
    ft_im = 'jpg'

    pa_gt = '/home/cqzhao/dataset/dataset2014/dataset/dynamicBackground/fountain01/groundtruth'
#    pa_gt = 'D:/dataset/dataset2014/dataset/dynamicBackground/fountain01/groundtruth'
    ft_gt = 'png'


    imgs = loadImgs_pytorch(pa_im, ft_im)
    labs = loadImgs_pytorch(pa_gt, ft_gt)


    frame, row, column, byte = imgs.shape

    curidx = 1140

    im = imgs[curidx]
    lb = labs[curidx]


    c_L, f_L = getEmptyCF(-255, 255, 1)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    labs_data = torch.empty(row*column)

    cnt = 0



    for r in range(row):
        for c in range(column):
            vec = imgs[:, r, c, :].squeeze()
            val = im[r, c, :]

            sub = vec - val

            for b in range(byte):
#                c_I, f_I = getHist_plus(sub[:, b], 1, -255, 255)
                hist_data[cnt, :, b] = torch.histc(sub[:, b], 511, -255, 255)

            labs_data[cnt] = lb[r, c]


            cnt = cnt + 1


        print("r = ", r, " ", row)



    # randomly permutate the input

    idx = torch.randperm(row*column)

    hist_data = hist_data[idx]
    labs_data = labs_data[idx]




    idx_fg = labs_data == 255
    idx_bk = labs_data == 0


    hist_fg = hist_data[idx_fg]
    hist_bk = hist_data[idx_bk]

    labs_fg = labs_data[idx_fg]
    labs_bk = labs_data[idx_bk]





    data_fg = hist_fg[0:100, :, 0].squeeze()
    data_bk = hist_bk[0:100, :, 0].squeeze()



    data = torch.cat((data_fg, data_bk), dim = 0)
    labs = torch.zeros(200)
    labs[0:100] = labs[0:100] + 1


    num_labs = torch.numel(labs)

    idx = torch.randperm(torch.numel(labs))

    labs = labs[idx]
    data = data[idx]



    return data, labs



def getSpatioVidHist_plus(imgs, left = -1, right = 1, border = 0.01):

    frame, row, column, byte = imgs.shape

    imgs_pad = F.pad(imgs.permute(0, 3, 1, 2), (1, 1, 1, 1), mode='replicate')
    imgs_pad = imgs_pad.permute(0, 2, 3, 1)
    imgs_pad = (imgs_pad/255.0)*right


    imgs = (imgs/255.0)*right
    imgs = imgs.reshape(frame, row*column, byte)
    imgs = imgs.permute(1, 0, 2)


    c_L, f_L = getEmptyCF(left, right, border)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    num_hist = round((right - left)/border) + 1


    cnt = 0
    for r in range(1, row + 1):
        for c in range(1, column + 1):
            for b in range(byte):
                data = imgs_pad[:, r-1:r+2, c-1:c+2, b].reshape(frame*3*3)
                num_data = torch.numel(data)

                hist_data[cnt, :, b] = torch.histc(data, num_hist, left, right)/(num_data*1.0)

            cnt = cnt + 1

    return hist_data





def getVidHist_plus(imgs, left = -1, right = 1, border = 0.01):

    frame, row, column, byte = imgs.shape

#    print("before test")
#    imgs = (imgs/255.0)*right

#    print("after test")
    imgs = imgs.reshape(frame, row*column, byte)
    imgs = imgs.permute(1, 0, 2)


    c_L, f_L = getEmptyCF(left, right, border)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    num_hist = round((right - left)/border) + 1


    for i in range(row*column):
        for b in range(byte):
            hist_data[i, :, b] = torch.histc( (imgs[i, :, b]/255.0)*right, num_hist, left, right)/(frame*1.0)

    return hist_data



def getNormalData_plus(imgs, labs, curidx, left = -1, right = 1, border = 0.01):

	frame, row, column, byte = imgs.shape

	im = imgs[curidx]
	lb = labs[curidx]
	imgs_vec = imgs - im

	imgs_vec = (imgs_vec/255.0)*right
    #- (im/255.0)*right
#    imgs_vec = imgs_vec - (im/255.0)


	imgs_vec = imgs_vec.reshape(frame, row*column, byte)
	imgs_vec = imgs_vec.permute(1, 0, 2)


	c_L, f_L = getEmptyCF(left, right, border)
	len_hist = torch.numel(f_L)

	hist_data = torch.empty([row*column, len_hist , byte])
	labs_data = lb.reshape(row*column)
	num_hist = round((right - left)/border) + 1


	for i in range(row*column):
		for b in range(byte):
			hist_data[i, :, b] = torch.histc(imgs_vec[i, :, b], num_hist, left, right)/(frame*1.0)


	return hist_data, labs_data



def getSpatialData_byHistVid(vid_hist, imgs, labs, curidx, left = -1, right = 1, delta = 0.01):


    data_vid, labs_vid = getNormalData_byHistVid(vid_hist, imgs, labs, curidx, left, right, delta)


    frames, row_im, column_im, byte_im = imgs.shape

    num_hist, len_hist, byte_hist = vid_hist.shape


    mat_hist = data_vid.reshape(row_im, column_im, len_hist, byte_hist)

    pad_hist = mat_hist.permute(2, 3, 0, 1)
    pad_hist = F.pad(pad_hist, (1, 1, 1, 1), mode='replicate')
    pad_hist = pad_hist.permute(2, 3, 0, 1)


    spatial_hist = torch.cat((mat_hist, mat_hist, mat_hist, mat_hist, mat_hist), dim=3)

    print(mat_hist.shape)

    print(spatial_hist.shape)

    for r in range(1,row_im + 1):
        for c in range(1,column_im + 1):

            spatial_hist[r - 1, c - 1, :, 0:3]   = pad_hist[r - 1, c, :, :]
            spatial_hist[r - 1, c - 1, :, 3:6]   = pad_hist[r, c - 1, :, :]
            spatial_hist[r - 1, c - 1, :, 6:9]   = pad_hist[r, c, :, :]
            spatial_hist[r - 1, c - 1, :, 9:12]  = pad_hist[r + 1, c, :, :]
            spatial_hist[r - 1, c - 1, :, 12:15] = pad_hist[r, c + 1, :, :]



    return spatial_hist, labs_vid









def getNormalData_byHistVid(vid_hist, imgs, pa_gt, ft_gt, curidx, left = -1, right = 1, delta = 0.01):


    frames, row_im, column_im, byte_im = imgs.shape

    im = imgs[curidx].reshape(row_im*column_im, byte_im)
    lb = readImg_byFilesIdx_pytorch(curidx, pa_gt, ft_gt)
#    lb = labs[curidx]

    im = (im/255.0)*right
    im = torch.round(im/delta)


    num_hist = round((right - left)/delta) + 1
    num_right = round(right/delta) + 1

    offset_right = round(right/delta)

    hist_data = torch.abs(vid_hist - vid_hist)
    labs_data = lb.reshape(row_im*column_im)

    for i in range(num_right):
        for b in range(byte_im):
            idx_r = im[:, b] == i

            hist_data[idx_r, (num_hist - offset_right - i ):(num_hist - i) , b] = vid_hist[idx_r, (num_hist - offset_right):num_hist, b]

    return hist_data, labs_data





def getNormalData_byHistVid_andImgs(vid_hist, im, pa_gt, ft_gt, curidx, left = -1, right = 1, delta = 0.01):


#    frames, row_im, column_im, byte_im = imgs.shape
    row_im, column_im, byte_im = im.shape

#    im = imgs[curidx].reshape(row_im*column_im, byte_im)
    im = im.reshape(row_im*column_im, byte_im)
    lb = readImg_byFilesIdx_pytorch(curidx, pa_gt, ft_gt)
    print("load groundtruth imgs:", pa_gt, " idx:", curidx)
#    lb = labs[curidx]

    im = (im/255.0)*right
    im = torch.round(im/delta)


    num_hist = round((right - left)/delta) + 1
    num_right = round(right/delta) + 1



    offset_right = round(right/delta)


    if len(lb.shape) > 2:
        lb = lb[:, :, 0]

    hist_data = torch.abs(vid_hist - vid_hist)
    labs_data = lb.reshape(row_im*column_im)

    for i in range(num_right):
        for b in range(byte_im):
            idx_r = im[:, b] == i

            hist_data[idx_r, (num_hist - offset_right - i - 1):(num_hist - i) , b] = vid_hist[idx_r, (num_hist - offset_right - 1):num_hist, b]

    return hist_data, labs_data


# data_vid,    labs_vid    =



# def getListNormalData_byHistVid_andImgs(vid_hist, imgs,      pa_gt, ft_gt, curidx_list, mode, left = -1, right = 1, border = 0.01):



#     getListNormalData_byHistVid_andImgs(vid_hist, trainimgs, pa_gt, ft_gt,  curidx,    "train", left_data, right_data, delta)




def getListNormalData_byHistVid_andImgs_old(vid_hist, imgs, pa_gt, ft_gt, curidx_list, mode, left = -1, right = 1, border = 0.01):


    curidx = curidx_list[0]

    hist_data, hist_labs = getNormalData_byHistVid_andImgs(vid_hist, imgs[0], pa_gt, ft_gt, curidx, left, right, border)


    NUM = len(curidx_list)



    frames, length, byte = hist_data.shape

    re_data = torch.empty(frames*NUM, length, byte)
    re_labs = torch.empty(frames*NUM)


    i = 1

    re_data[(i - 1)*frames:i*frames, :, :] = hist_data
    re_labs[(i - 1)*frames:i*frames] = hist_labs




    for curidx in curidx_list[1:NUM]:
#    for i in range(1, NUM):

        print("curidx = ", curidx)
        temp_data, temp_labs = getNormalData_byHistVid_andImgs(vid_hist, imgs[i], pa_gt, ft_gt, curidx, left, right, border)




#        hist_data = torch.cat((hist_data.clone(), temp_data.clone()), dim = 0)

#        hist_labs = torch.cat((hist_labs.clone(), temp_labs.clone()), dim = 0)

        i = i + 1


        re_data[(i - 1)*frames:i*frames, :, :] = temp_data
        re_labs[(i - 1)*frames:i*frames] = temp_labs



#    hist_data = re_data
#    hist_labs = re_labs

    if mode == "train":
        idx = (re_labs == 255) | (re_labs == 0)


        print("in training mode")


        re_data = re_data[idx]
        re_labs = re_labs[idx]

        print("extract training data completed")

        LEN_NUM = torch.numel(re_labs)
        idx = torch.randperm(LEN_NUM)

        print("idx starts")
#|         re_data = re_data[idx]
#|         re_labs = re_labs[idx]

        print("idx completed")


    return re_data, re_labs









def getListNormalData_byHistVid_andImgs(  vid_hist, trainimgs, pa_gt, ft_gt,  curidx,       mode, left_data = -1, right_data = 1, delta = 0.01):




    idxval = curidx[0]

    hist_data, hist_labs = getNormalData_byHistVid_andImgs(vid_hist, trainimgs[0], pa_gt, ft_gt, idxval, left_data, right_data, delta)


    NUM = len(curidx)



    frames, length, byte = hist_data.shape

    re_data = torch.empty(frames*NUM, length, byte)
    re_labs = torch.empty(frames*NUM)


    i = 1

    re_data[(i - 1)*frames:i*frames, :, :] = hist_data
    re_labs[(i - 1)*frames:i*frames] = hist_labs




    for idxval in curidx[1:NUM]:
#    for i in range(1, NUM):

        print("idxval = ", idxval)
        temp_data, temp_labs = getNormalData_byHistVid_andImgs(vid_hist, trainimgs[i], pa_gt, ft_gt, idxval, left_data, right_data, delta )




#        hist_data = torch.cat((hist_data.clone(), temp_data.clone()), dim = 0)

#        hist_labs = torch.cat((hist_labs.clone(), temp_labs.clone()), dim = 0)

        i = i + 1


        re_data[(i - 1)*frames:i*frames, :, :] = temp_data
        re_labs[(i - 1)*frames:i*frames] = temp_labs

        print("in the for ========================================")


#    hist_data = re_data
#    hist_labs = re_labs

    if mode == "train":
        idx = (re_labs == 255) | (re_labs == 0)


        print("in training mode")


        re_data = re_data[idx]
        re_labs = re_labs[idx]

        print("extract training data completed")

        LEN_NUM = torch.numel(re_labs)
        idx = torch.randperm(LEN_NUM)

        print("idx starts")
#|         re_data = re_data[idx]
#|         re_labs = re_labs[idx]

        print("idx completed")


    return re_data, re_labs











def getListNormalData_byHistVid(vid_hist, imgs, pa_gt, ft_gt, curidx_list, mode, left = -1, right = 1, border = 0.01):


    curidx = curidx_list[0]

    hist_data, hist_labs = getNormalData_byHistVid(vid_hist, imgs, pa_gt, ft_gt, curidx, left, right, border)



    NUM = len(curidx_list)

    for curidx in curidx_list[1:NUM]:

        temp_data, temp_labs = getNormalData_byHistVid(vid_hist, imgs, pa_gt, ft_gt, curidx, left, right, border)

        hist_data = torch.cat((hist_data, temp_data), dim = 0)
        hist_labs = torch.cat((hist_labs, temp_labs), dim = 0)



    if mode == "train":
        idx = (hist_labs == 255) | (hist_labs == 0)

        hist_data = hist_data[idx]
        hist_labs = hist_labs[idx]


        LEN_NUM = torch.numel(hist_labs)
        idx = torch.randperm(LEN_NUM)

        hist_data = hist_data[idx]
        hist_labs = hist_labs[idx]


    return hist_data, hist_labs


# def getNormalData
def getNormalData(imgs, labs, curidx):


    frame, row, column, byte = imgs.shape


    im = imgs[curidx]
    lb = labs[curidx]


    # 使用这种方式可以保证和getNormalData_old 完全一样
#     im = im/255.0
#     imgs = imgs/255.0


    imgs_vec = imgs - im

    imgs_vec = imgs_vec/255.0
    imgs_vec = imgs_vec.reshape(frame, row*column, byte)
    imgs_vec = imgs_vec.permute(1, 0, 2)


    c_L, f_L = getEmptyCF(-1, 1, 0.01)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    labs_data = lb.reshape(row*column)


    for i in range(row*column):
        for b in range(byte):
            hist_data[i, :, b] = torch.histc(imgs_vec[i, :, b], 201, -1, 1)/(frame*1.0)
    return hist_data, labs_data





# def getNormalData
def getNormalData_old(imgs, labs, curidx):

#    imgs = loadImgs_pytorch(pa_im, ft_im)
#    labs = loadImgs_pytorch(pa_gt, ft_gt)


    frame, row, column, byte = imgs.shape

#    curidx = 1140

    im = imgs[curidx]
    lb = labs[curidx]


    c_L, f_L = getEmptyCF(-1, 1, 0.01)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    labs_data = torch.empty(row*column)

    cnt = 0





    for r in range(row):
        for c in range(column):
            vec = imgs[:, r, c, :].squeeze()/255.0
            val = im[r, c, :]/255.0


            sub = vec - val

            for b in range(byte):
#                c_I, f_I = getHist_plus(sub[:, b], 1, -255, 255)
                hist_data[cnt, :, b] = torch.histc(sub[:, b], 201, -1, 1)/(frame * 1.0)

            labs_data[cnt] = lb[r, c]

            cnt = cnt + 1



        print("r = ", r, " ", row)


    return hist_data, labs_data



# def getTempData(pa_im, ft_im, pa_gt, ft_gt):
#     imgs = loadImgs_pytorch(pa_im, ft_im)
#     labs = loadImgs_pytorch(pa_gt, ft_gt)
#
#
#     frame, row, column, byte = imgs.shape
#
# #    curidx = 1140
#
#
#     c_L, f_L = getEmptyCF(-1, 1, 0.01)
#     len_hist = torch.numel(f_L)
#
#     hist_data = torch.empty([row*column, len_hist , byte])
#     labs_data = torch.empty(row*column)
#
#     cnt = 0
#
#
#
#     for r in range(row):
#         for c in range(column):
#             vec = imgs[:, r, c, :].squeeze()/255.0
#
#
#
#             for b in range(byte):
# #                c_I, f_I = getHist_plus(sub[:, b], 1, -255, 255)
#                 hist_data[cnt, :, b] = torch.histc(vec[:, b], 201, -1, 1)/(frame * 1.0)
#
#             cnt = cnt + 1
#
#
#         print("r = ", r, " ", row)
#
#
#     return hist_data, imgs, labs





def getHistData(pa_im, ft_im, pa_gt, ft_gt, curidx):

    imgs = loadImgs_pytorch(pa_im, ft_im)
    labs = loadImgs_pytorch(pa_gt, ft_gt)


    frame, row, column, byte = imgs.shape

#    curidx = 1140

    im = imgs[curidx]
    lb = labs[curidx]


    c_L, f_L = getEmptyCF(-255, 255, 1)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    labs_data = torch.empty(row*column)

    cnt = 0



    for r in range(row):
        for c in range(column):
            vec = imgs[:, r, c, :].squeeze()
            val = im[r, c, :]

            sub = vec - val

            for b in range(byte):
#                c_I, f_I = getHist_plus(sub[:, b], 1, -255, 255)
                hist_data[cnt, :, b] = torch.histc(sub[:, b], 511, -255, 255)

            labs_data[cnt] = lb[r, c]

            cnt = cnt + 1


        print("r = ", r, " ", row)


    return hist_data, labs_data





def getVideoData():
    pa_im = '/home/cqzhao/dataset/dataset2014/dataset/dynamicBackground/fountain01/input'
    pa_im = 'D:/dataset/dataset2014/dataset/dynamicBackground/fountain01/input'
    ft_im = 'jpg'

    pa_gt = '/home/cqzhao/dataset/dataset2014/dataset/dynamicBackground/fountain01/groundtruth'
    pa_gt = 'D:/dataset/dataset2014/dataset/dynamicBackground/fountain01/groundtruth'
    ft_gt = 'png'


    imgs = loadImgs_pytorch(pa_im, ft_im)
    labs = loadImgs_pytorch(pa_gt, ft_gt)


    frame, row, column, byte = imgs.shape

    curidx = 1140

    im = imgs[curidx]
    lb = labs[curidx]


    c_L, f_L = getEmptyCF(-255, 255, 1)
    len_hist = torch.numel(f_L)

    hist_data = torch.empty([row*column, len_hist , byte])
    labs_data = torch.empty(row*column)

    cnt = 0



    for r in range(row):
        for c in range(column):
            vec = imgs[:, r, c, :].squeeze()
            val = im[r, c, :]

            sub = vec - val

            for b in range(byte):
#                c_I, f_I = getHist_plus(sub[:, b], 1, -255, 255)
                hist_data[cnt, :, b] = torch.histc(sub[:, b], 511, -255, 255)

            labs_data[cnt] = lb[r, c]

            cnt = cnt + 1


        print("r = ", r, " ", row)


    return hist_data, labs_data




def balanceData_plus(data, labs):

    idx_fg = labs == 255
    idx_bk = labs == 0


    data_fg = data[idx_fg]
    data_bk = data[idx_bk]

    labs_fg = labs[idx_fg]
    labs_bk = labs[idx_bk]


    num_fg = torch.numel(labs_fg)
    num_bk = torch.numel(labs_bk)

    value = round(num_bk/num_fg)


#    print(data_fg.shape)
    data_fg = data_fg.repeat(value, 1, 1)
    labs_fg = labs_fg.repeat(value)


    re_data = torch.cat( (data_fg, data_bk), dim = 0)
    re_labs = torch.cat( (labs_fg, labs_bk), dim = 0)

    return re_data, re_labs






def balanceData(data, labs):

    idx_fg = labs == 255
    idx_bk = labs == 0


    data_fg = data[idx_fg]
    data_bk = data[idx_bk]

    labs_fg = labs[idx_fg]
    labs_bk = labs[idx_bk]


    num_fg, len_fg = data_fg.shape
    num_bk, len_bk = data_bk.shape



#     print("borderline ----------------")
#     print(data_fg.shape)
#     print(data_bk.shape)
#     print("borderline ----------------")


    # 一切求快，之后再改
    value = round(num_bk/num_fg)

    data_fg = data_fg.repeat(value, 1)
    labs_fg = labs_fg.repeat(value)


#     print("data_fg.shape:", data_fg.shape)
#     print("data_bk.shape:", data_bk.shape)
#
#     print("labs_fg.shape:", labs_fg.shape)
#     print("labs_bk.shape:", labs_bk.shape)


    re_data = torch.cat( (data_fg, data_bk), dim = 0)
    re_labs = torch.cat( (labs_fg, labs_bk), dim = 0)





    return re_data, re_labs



def getTensorOptim(var, learning_rate):

    var = Variable(var, requires_grad = True)

    return optim.Adam([var], lr = learning_rate, amsgrad = True)



class ClassNet(nn.Module):

    def __init__(self, input_size=1000, hidden_size=2000):
        super().__init__()

        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 2)


        self.hidden_size = hidden_size


    def forward(self, input):
        x = F.relu(self.fc1(input))

        x = x.view(-1, self.hidden_size)

        x = self.fc2(x)

        return F.log_softmax(x, dim=1)







def train(data_vid, labs_vid, batchsize, device, network, loss_func, prodis_mul, difdis_mul,
          c_data, c_W, f_W, c_B, f_B, c_Z, delta, params,
          optim_W, optim_B,
          optim_net, net_pa, num_epoch):

    LEN_DATA = torch.numel(labs_vid)

    value = round(LEN_DATA/batchsize)


    # 断点重新训练
    cnt = 0
    judge = 0
    while judge == 0:
        check_name_net = net_pa + "network_dis_" + str(cnt).zfill(4) + ".pt"

        if not os.path.exists(check_name_net):
            judge = 1
        else:
            print("epoch ", cnt, " was completed")
            cnt += 1



#     print("cnt = ", cnt)
#
#     print("borderline ------------------------------")


    cnt = cnt - 1

    if cnt > -1:

        name_net = net_pa + "network_dis_" + str(cnt).zfill(4) + ".pt"
        name_f_W = net_pa + "f_W_" + str(cnt).zfill(4) + ".pt"

        name_f_B = net_pa + "f_B_" + str(cnt).zfill(4) + ".pt"


        f_W = torch.load(name_f_W)
        f_B = torch.load(name_f_B)

        network.load_state_dict(torch.load(name_net))

        print("network loaded")


#    data_vid_src = data_vid
#    labs_vid_src = labs_vid

#     print("save training data")
#     saveMod("../data/data_vid_src.pt", data_vid_src)
#     saveMod("../data/labs_vid_src.pt", labs_vid_src)
#     print("completed")
#
#     print("clean temp training data")
#     del data_vid
#     del labs_vid
#     del data_vid_src
#     del labs_vid_src
#     print("completed")


    for epoch in range(cnt + 1, num_epoch):

        total_loss = 0

        torch.manual_seed(epoch)

        idx = torch.randperm(LEN_DATA)

#         print("load training data")
#         data_vid_src = torch.load("../data/data_vid_src.pt")
#         labs_vid_src = torch.load("../data/labs_vid_src.pt")
#         print("completed")

        print("idx training data")
        data_vid = data_vid[idx]
        labs_vid = labs_vid[idx]
        print("completed")

#         print("clean loaded data")
#         del data_vid_src
#         del labs_vid_src
#         print("completed")


        for i in range(value):
            left = i*batchsize
            right = (i + 1)*batchsize


            data = data_vid[left:right]
            labs = labs_vid[left:right]

            data = data.to(device)
            labs = labs.to(device, dtype = torch.int64)


            f_Z_W = torch.cat( [prodis_mul(c_data, data[:, :, b], c_W, f_W[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_W.shape[-1])], dim = 3 )
            f_Z_B = torch.cat( [difdis_mul(c_data, data[:, :, b], c_B, f_B[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_B.shape[-1])], dim = 3 )


            f_F = f_Z_W + f_Z_B
            f_F = f_F.permute(0, 3, 1, 2)

            output = network(f_F)


            loss = loss_func(output, labs)

            print("epoch = ", epoch,  "  ", i, "\\" , value,   " loss = ", loss.item())
            total_loss = total_loss + loss.item()


            optim_W.zero_grad()
            optim_B.zero_grad()

            optim_net.zero_grad()

            loss.backward(retain_graph = True)

            optim_W.step()
            optim_B.step()

            optim_net.step()


        left = i*batchsize
        right = LEN_DATA



        data = data_vid[left:right]
        labs = labs_vid[left:right]

        data = data.to(device)
        labs = labs.to(device, dtype = torch.int64)


        f_Z_W = torch.cat( [prodis_mul(c_data, data[:, :, b], c_W, f_W[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_W.shape[-1])], dim = 3 )
        f_Z_B = torch.cat( [difdis_mul(c_data, data[:, :, b], c_B, f_B[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_B.shape[-1])], dim = 3 )


        f_F = f_Z_W + f_Z_B
        f_F = f_F.permute(0, 3, 1, 2)


        output = network(f_F)


        loss = loss_func(output, labs)

        print("epoch = ", epoch,  "  ", i, "\\" , value,   " loss = ", loss.item())
        total_loss = total_loss + loss.item()


        optim_W.zero_grad()
        optim_B.zero_grad()

        optim_net.zero_grad()

        loss.backward(retain_graph = True)

        optim_W.step()
        optim_B.step()

        optim_net.step()



        if epoch % 1 == 0:
            name_net = net_pa + "network_dis_" + str(epoch).zfill(4) + ".pt"

            name_f_W = net_pa + "f_W_" + str(epoch).zfill(4) + ".pt"
            name_f_B = net_pa + "f_B_" + str(epoch).zfill(4) + ".pt"


            saveMod(name_f_W, f_W)
            saveMod(name_f_B, f_B)

            torch.save(network.state_dict(), name_net)

            print("\n\n save model completed")

        print("")
        print("")
        print("borderline ----------------------------------------------")
        print("total_loss:", total_loss)
        print("borderline ----------------------------------------------")
        print("")
        print("")


    return network, f_W, f_B



def test(data_vid, batchsize, device, prodis_mul, difdis_mul, c_data, network,
            c_W, f_W,
         c_B, f_B, c_Z, delta, params):

    with torch.no_grad():

        LEN_DATA, dis_num, byte = data_vid.shape

        re_labs = np.zeros(LEN_DATA)

        value = round(LEN_DATA/batchsize)


        sum_prodis_time = 0
        sum_difdis_time = 0
        sum_relabs_time = 0


        for i in range(value):
            left = i*batchsize
            right = (i + 1)*batchsize


            data = data_vid[left:right]
    #        labs = labs_vid[left:right]

            data = data.to(device)
    #        labs = labs.to(device, dtype = torch.int64)



            f_Z_W = torch.cat( [prodis_mul(c_data, data[:, :, b], c_W, f_W[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_W.shape[-1])], dim = 3 )
            f_Z_B = torch.cat( [difdis_mul(c_data, data[:, :, b], c_B, f_B[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_B.shape[-1])], dim = 3 )


            f_F = f_Z_W + f_Z_B
            f_F = f_F.permute(0, 3, 1, 2)


            output = network(f_F)

            re_labs[left:right] = output.argmax(dim = 1, keepdim = True).cpu().detach().squeeze()

    #        print( i, ":", value )



        left = i*batchsize
        right = LEN_DATA



        data = data_vid[left:right]
    #    labs = labs_vid[left:right]

        data = data.to(device)
    #    labs = labs.to(device, dtype = torch.int64)




        f_Z_W = torch.cat( [prodis_mul(c_data, data[:, :, b], c_W, f_W[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_W.shape[-1])], dim = 3 )
        f_Z_B = torch.cat( [difdis_mul(c_data, data[:, :, b], c_B, f_B[:, :, b], c_Z, delta, params)[1].unsqueeze(-1) for b in range(f_B.shape[-1])], dim = 3 )


        f_F = f_Z_W + f_Z_B
        f_F = f_F.permute(0, 3, 1, 2)





    #    print("f_F.shape:", f_F.shape)
        output = network(f_F)

        re_labs[left:right] = output.argmax(dim = 1, keepdim = True).cpu().detach().squeeze()



    return re_labs



def getListNormalData_plus(imgs, labs, curidx_list, mode, left = -1, right = 1, border = 0.01):


    curidx = curidx_list[0]

    hist_data, hist_labs = getNormalData_plus(imgs, labs, curidx, left, right, border)



    NUM = len(curidx_list)

    for curidx in curidx_list[1:NUM]:

        temp_data, temp_labs = getNormalData_plus(imgs, labs, curidx, left, right, border)

        hist_data = torch.cat((hist_data, temp_data), dim = 0)
        hist_labs = torch.cat((hist_labs, temp_labs), dim = 0)



    if mode == "train":
        idx = (hist_labs == 255) | (hist_labs == 0)

        hist_data = hist_data[idx]
        hist_labs = hist_labs[idx]


        LEN_NUM = torch.numel(hist_labs)
        idx = torch.randperm(LEN_NUM)

        hist_data = hist_data[idx]
        hist_labs = hist_labs[idx]


    return hist_data, hist_labs




def getListNormalData(imgs, labs, curidx_list, mode):


    curidx = curidx_list[0]

    hist_data, hist_labs = getNormalData(imgs, labs, curidx)



    NUM = len(curidx_list)

    for curidx in curidx_list[1:NUM]:

        temp_data, temp_labs = getNormalData(imgs, labs, curidx)

        hist_data = torch.cat((hist_data, temp_data), dim = 0)
        hist_labs = torch.cat((hist_labs, temp_labs), dim = 0)



    if mode == "train":
        idx = (hist_labs == 255) | (hist_labs == 0)

        hist_data = hist_data[idx]
        hist_labs = hist_labs[idx]


        LEN_NUM = torch.numel(hist_labs)
        idx = torch.randperm(LEN_NUM)

        hist_data = hist_data[idx]
        hist_labs = hist_labs[idx]


    return hist_data, hist_labs






class ClassifyNetwork(nn.Module):
    def __init__(self, dis_num):
        super().__init__()

        self.conv1 = nn.Conv2d(3, 1, (dis_num, 1) )
#        self.conv2 = nn.Conv2d(10, 500, (1, 201))

        self.fc1 = nn.Linear(201, 512)
        self.fc2 = nn.Linear(512, 2)

    def forward(self, input):

#        print("input.shape:", input.shape)
        x = self.conv1(input)


#        print("x.shape:", x.shape)
        x = x.view(-1, 201)

#        x = self.conv2(x)
        x = self.fc1(x)
        x = F.relu(x)
#        x = F.relu( self.conv2(self.conv1(input)) )
        x = x.view(-1, 512)
        x = self.fc2(x)


        return F.log_softmax(x, dim = 1)


def generateTempBinaryMask(pa_gt, ft_gt, root_dir, name_categroy, name_video):

    fs, fullfs = loadFiles_plus(pa_gt, ft_gt)

    frames = len(fullfs)

    re_pa = root_dir + '/' + name_categroy + '/' + name_video + '/'

    for i in range(frames):

        gtim = torch.tensor(imageio.imread(fullfs[i]), dtype = torch.float)

        igtim = getTrainBinMask(gtim)

        filename = re_pa + fs[i]

        print('save files:', filename)
        saveImg(filename, igtim.numpy().astype(np.uint8))


    return re_pa


def byteCheck(imgs):

    if len(imgs.squeeze().shape) == 3:

        frames_im, row_im, column_im = imgs.shape

        imgs = imgs.expand(3, frames_im, row_im, column_im).permute(1, 2, 3, 0).clone()

        print(imgs.shape)

    return imgs


def main(argc, argv):

    params = QParams()
    params.setParams(argc, argv)


    ft_im = 'jpg'
    ft_gt = 'png'


    pa_im = params['pa_im']
    pa_gt = params['pa_gt']
    pa_out = params['pa_out']


    ft_im = params['ft_im']
    ft_gt = params['ft_gt']



    curidx = params['imgs_idx']
    curidx[:] = [i - 1 for i in curidx]


    torch.manual_seed(0)


    imgs = loadImgs_pytorch(pa_im, ft_im)
#    imgs = byteCheck(imgs)

    imgs = getConvImgs_test(imgs)



    print("labs ============================")



    left_data = -1
    right_data = 1

    left = -1
    right = 1
    delta = 0.01
    num_dis = 2



    frames, row_im, column_im, byte_im = imgs.shape
    frames_im, row_im, column_im, byte_im = imgs.shape



    print("generating video histograms")

    starttime = time.time()
    vid_hist = getVidHist_plus(imgs, left_data, right_data, delta)
    endtime = time.time()

    print("completed, total time:", endtime - starttime)

    print(vid_hist.shape)






#     print("generating spatial histograms")
#
#     starttime = time.time()
#     vid_hist = getSpatioVidHist_plus(imgs, left_data, right_data, delta)
#     endtime = time.time()
#
#     print("completed, total time:", endtime - starttime)


#    print(torch.sum(torch.abs(vid_hist - vid_hist_pad)))



    trainimgs = imgs[curidx]

    print("clean temp imgs data")
    del imgs
    print("completed")



    print("trainimgs.shape:", trainimgs.shape)



#    data_vid,    labs_vid    = getListNormalData_byHistVid_andImgs_old(vid_hist, trainimgs, pa_gt, ft_gt,  curidx,    "train", left_data, right_data, delta)







#
#
#
#     idxval = curidx[0]
#
#     hist_data, hist_labs = getNormalData_byHistVid_andImgs(vid_hist, trainimgs[0], pa_gt, ft_gt, idxval, left_data, right_data, delta)
#
#
#     NUM = len(curidx)
#
#
#
#     frames, length, byte = hist_data.shape
#
#     re_data = torch.empty(frames*NUM, length, byte)
#     re_labs = torch.empty(frames*NUM)
#
#
#     i = 1
#
#     re_data[(i - 1)*frames:i*frames, :, :] = hist_data
#     re_labs[(i - 1)*frames:i*frames] = hist_labs
#

    print("generating trainning data")
    i = 0

    for idxval in curidx:
#    for i in range(1, NUM):

        print("idxval = ", idxval)

        data_vid, labs_vid = getNormalData_byHistVid_andImgs(vid_hist, trainimgs[i], pa_gt, ft_gt, idxval, left_data, right_data, delta )




        idx = (labs_vid == 255) | (labs_vid == 0)

        print("idx:", torch.sum(idx))


        data_vid[~idx] = 0


#         strcmd = input('stop in main')
#
#         data_vid = data_vid[idx]
#         labs_vid = labs_vid[idx]

        labs_vid = torch.round(labs_vid/255)


        i = i + 1

        filename_data_vid = pa_out + 'data_' + str(i).zfill(4) + '.hist'
        filename_labs_vid = pa_out + 'data_' + str(i).zfill(4) + '.labs'
        filename_vid_hist = pa_out + 'vid_hist.pt'
#
#     saveMod(filename_data_vid, data_vid)
#     saveMod(filename_labs_vid, labs_vid)


        saveMod(filename_data_vid, data_vid)
        saveMod(filename_labs_vid, labs_vid)
        saveMod(filename_vid_hist, vid_hist)



        print("checking training data")
        data_vid_check = torch.load(filename_data_vid)
        labs_vid_check = torch.load(filename_labs_vid)
        vid_hist_check = torch.load(filename_vid_hist)

        print(data_vid.shape)
        print(labs_vid.shape)
        print(vid_hist.shape)


        print(torch.sum( data_vid_check - data_vid  ))
        print(torch.sum( labs_vid_check - labs_vid ))
        print(torch.sum( vid_hist_check - vid_hist ))

        print("checking completed")

#     labs_vid    = torch.round(labs_vid/255)



    print("completed")
#    hist_data = re_data
#    hist_labs = re_labs
#
#     idx = (re_labs == 255) | (re_labs == 0)
#
#
#     print("in training mode")
#
#
#     re_data = re_data[idx]
#     re_labs = re_labs[idx]
#
#     print("extract training data completed")
#
#     LEN_NUM = torch.numel(re_labs)
#     idx = torch.randperm(LEN_NUM)
#
#     print("idx starts")
# #|     re_data = re_data[idx]
# #|     re_labs = re_labs[idx]
#
#     print("idx completed")
#


#     filename_data_vid = pa_out + 'data_vid.hist'
#     filename_labs_vid = pa_out + 'labs_vid.labs'
#     filename_vid_hist = pa_out + 'vid_hist.pt'
#
#     saveMod(filename_data_vid, data_vid)
#     saveMod(filename_labs_vid, labs_vid)
#     saveMod(filename_vid_hist, vid_hist)



#        hist_data = torch.cat((hist_data.clone(), temp_data.clone()), dim = 0)

#        hist_labs = torch.cat((hist_labs.clone(), temp_labs.clone()), dim = 0)


#
#         re_data[(i - 1)*frames:i*frames, :, :] = temp_data
#         re_labs[(i - 1)*frames:i*frames] = temp_labs
#
#         print("in the for ========================================")


#    hist_data = re_data
#    hist_labs = re_labs
#
#     idx = (re_labs == 255) | (re_labs == 0)
#
#
#     print("in training mode")
#
#
#     re_data = re_data[idx]
#     re_labs = re_labs[idx]
#
#     print("extract training data completed")
#
#     LEN_NUM = torch.numel(re_labs)
#     idx = torch.randperm(LEN_NUM)
#
#     print("idx starts")
# #|     re_data = re_data[idx]
# #|     re_labs = re_labs[idx]
#
#     print("idx completed")
#
#
#
#     print(torch.sum( torch.abs( re_data - data_vid)))
#
#
#
#
#
#     strsdfsdf = input('stop sdfsdf')
#
#
#
#
#
#
#
#
#
#
#
#     print("clean trainimgs data")
#     del trainimgs
#     print("completed")
#
#
# #    print("labs_vid:", labs_vid.shape)
# #    strcom = input('stop here')
#
# #     idx = labs_vid != 85
# #
# #     labs_vid = labs_vid[idx]
# #
# #
# #
# #     strtempstop = input('stop herer')
#
#     print("labs_vid:", labs_vid.shape)
#
#
#     idx_fg = labs_vid == 255
#     idx_bk = labs_vid == 0
#
#     idx = torch.logical_or(idx_fg, idx_bk)
#
#
#     print(labs_vid[~idx])
#
#     strcmd = input('stop here')
#
#     labs_vid    = torch.round(labs_vid/255)
#
#     print("the size of training data")
#     print("data_vid:", data_vid.shape)
#     print("labs_vid:", labs_vid.shape)
#
#     print("saving training data ...")
#
#     filename_data_vid = pa_out + 'data_vid.hist'
#     filename_labs_vid = pa_out + 'labs_vid.labs'
#     filename_vid_hist = pa_out + 'vid_hist.pt'
#
#     saveMod(filename_data_vid, data_vid)
#     saveMod(filename_labs_vid, labs_vid)
#     saveMod(filename_vid_hist, vid_hist)
# #     saveMod("../data/data_vid_src.pt", data_vid_src)
# #     saveMod("../data/labs_vid_src.pt", labs_vid_src)
#
#     print("completed")
#
#
#     print("checking saveimg data")
#
#     data_vid_check = torch.load(filename_data_vid)
#     labs_vid_check = torch.load(filename_labs_vid)
#     vid_hist_check = torch.load(filename_vid_hist)
#
#
#     print(torch.sum( data_vid_check - data_vid  ))
#     print(torch.sum( labs_vid_check - labs_vid ))
#     print(torch.sum( vid_hist_check - vid_hist ))
#
#     print("completed")
#
#


if __name__ == '__main__':

    argc = len(sys.argv)
    argv = sys.argv

    main(argc, argv)
