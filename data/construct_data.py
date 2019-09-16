import numpy as np
import os
from datetime import datetime
import random
import cv2
from functools import cmp_to_key
from PIL import Image
from tqdm import tqdm
from data.utils import *
from utils import *
import math
from config import *

## FOR SMALL DATASET
# MVS_URL = r'/home/sjhu/datasets/small_dataset/samples_mvs'
# KEYFRAMES_URL = r'/home/sjhu/datasets/small_dataset/samples_keyframes'
# FEATURES_URL = r'/home/sjhu/datasets/small_dataset/samples_features'
# ROOT_URL = r'/home/sjhu/datasets'
# VIDEOS_URL = r'/home/sjhu/datasets/all_dataset'
# TXT_ROOT_URL = r'/home/sjhu/datasets/small_dataset/'

## FOR MEDIUM
FEATURES_URL = r'/data/sjhu/features_1'
ROOT_URL = r'/home/sjhu/datasets'
VIDEOS_URL = r'/home/sjhu/datasets/all_dataset'  #
TXT_ROOT_URL = r'/data/sjhu/'

## For Dataset
WIDTH = 256
HEIGHT = 340


class VideoExtracter:
    def __init__(self, video_name):
        # ex: filename = 916710595466737253411014029368.mp4
        self.video_name = video_name
        self.video_features_folder = os.path.join(FEATURES_URL, video_name.split('.')[0])
        self.y_files = []
        self.u_files = []
        self.v_files = []
        self.depth_files = []
        self.qp_files = []
        self.mv_x_files = []
        self.mv_y_files = []
        self.pic_names = []
        if not os.path.exists(self.video_features_folder): os.makedirs(self.video_features_folder)
        os.chdir(self.video_features_folder)
        self.mvs_folder = os.path.join(self.video_features_folder, 'mvs')
        self.keyframes_folder = os.path.join(self.video_features_folder, 'keyframes')
        self.residuals_folder = os.path.join(self.video_features_folder, 'residuals')
        # os.mkdir(self.mvs_folder)
        # os.mkdir(self.keyframes_folder)
        # os.mkdir(self.residuals_folder)

    def save_video_level_features(self):
        # for mvs and residuals
        os.chdir(VIDEOS_URL)
        os.system('~/env/extract_mvs %s' % self.video_name)
        temp_folder = os.path.join(VIDEOS_URL, self.video_name.split('.')[0])
        # #
        filenames = []
        for file in os.listdir(os.path.join(temp_folder)):
            filename = os.path.join(temp_folder, file)
            filenames.append(filename)
        filenames.sort(key=self.sort_by_frame_order)
        self.extract_files_by_type(filenames)
        self.deal_residual_matrixs(self.residuals_folder)
        self.deal_mv_matrix(self.mvs_folder)
        free_folder_space(temp_folder)

        # for keyframes
        os.system(
            "/home/sjhu/env/ffmpeg-4.2-amd64-static/ffmpeg -i %s -vf select='eq(pict_type\,I)' -vsync 2 -s 340x256 -f image2 %s/%%d.jpeg " % (
                os.path.join(VIDEOS_URL, self.video_name), self.keyframes_folder))

    def load_video_level_features(self, num_segments):
        residuals = self.load_residuals(num_segments)
        mvs = self.load_mvs(num_segments)
        keyframes = self.load_keyframes()
        return residuals, mvs, keyframes

    def load_keyframes(self,is_train):
        num_max = 20
        os.chdir(self.keyframes_folder)
        mat = []
        files = os.listdir(self.keyframes_folder)
        length = len(files)

        if length == 0:
            mat = np.random.randint(255, size=(5, WIDTH, HEIGHT, 3))

        idx = list(range(length))
        if length > num_max:
            # print(self.video_name)
            if is_train:
                idx = random_sample(idx,num_max)
            else:
                idx = fix_sample(idx,num_max)

        for i in idx:
            img = files[i]
            temp = np.asarray(Image.open(img))
            mat.append(temp)

        return np.array(mat, dtype=np.float32)

    def load_mvs(self, num_segments, is_train):
        """
        :param num_segments:
        :param is_train:
        :return: (counts, width, height, channels)
        """
        os.chdir(self.mvs_folder)
        mat = []
        files = os.listdir(self.mvs_folder)
        length = len(files)
        interval = math.ceil(length / num_segments)

        ## for some except
        if interval == 0:
            mat = np.random.randint(1, size=(num_segments, WIDTH, HEIGHT, 2))
            return np.array(mat, dtype=np.float32)

        if length < num_segments:
            idx = list(range(length))
        else:
            idx = list(range(length))
            if is_train:
                idx = random_sample(idx,num_segments)
                idx.sort()
            else:
                idx = fix_sample(idx,num_segments)
        for i in idx:
            img = files[i]
            temp = np.asarray(Image.open(img))
            mat.append(temp)
        mat = np.array(mat, dtype=np.int16)
        mat = mat - 128
        if mat.shape[0] < num_segments:
            # use zero to pad
            pad = np.zeros((num_segments - mat.shape[0], WIDTH, HEIGHT, 3))
            mat = np.concatenate((mat, pad), axis=0)
        return np.array(mat[..., :2], dtype=np.float32)

    def load_residuals(self, num_segments, is_train):
        """
        :param num_segments:
        :param is_train:
        :return: (counts, width, height, channels)
        """
        os.chdir(self.mvs_folder)
        mat = []
        files = os.listdir(self.mvs_folder)
        length = len(files)
        interval = math.ceil(length / num_segments)

        ## for some except
        if interval == 0:
            mat = np.random.randint(1, size=(num_segments, WIDTH, HEIGHT, 3))
            return np.array(mat, dtype=np.float32)

        if length < num_segments:
            idx = list(range(length))
        else:
            idx = list(range(length))
            if is_train:
                idx = random_sample(idx, num_segments)
                idx.sort()
            else:
                idx = fix_sample(idx, num_segments)
        for i in idx:
            img = files[i]
            temp = np.asarray(Image.open(img))
            mat.append(temp)
        mat = np.array(mat, dtype=np.int16)
        mat = mat - 128
        if mat.shape[0] < num_segments:
            # use zero to pad
            e = mat[-1, ...]
            e = e[np.newaxis, ...]
            pad = np.repeat(e, num_segments - mat.shape[0], axis=0)
            mat = np.concatenate((mat, pad), axis=0)
        return np.array(mat, dtype=np.float32)

    def extract_files_by_type(self, filenames):
        self.u_files = [file for file in filenames if 'D_U' in file]
        self.y_files = [file for file in filenames if 'D_Y' in file]
        self.v_files = [file for file in filenames if 'D_V' in file]
        self.depth_files = [file for file in filenames if 'depth' in file]
        self.qp_files = [file for file in filenames if 'QP' in file]
        # for B-frame , here just abondon the back refernce frame
        self.mv_x_files = [file for file in filenames if '_mv_0_x' in file]
        self.mv_y_files = [file for file in filenames if 'mv_0_y' in file]

    def sort_by_frame_order(self, elem):
        return int(elem.split('/')[-1].split('_')[0])

    def sort_by_image_order(self, elem):
        return int(elem.split('/')[-1].split('.')[0])

    def deal_residual_matrixs(self, folder):
        os.chdir(folder)
        for i in range(len(self.u_files)):
            U = np.loadtxt(self.u_files[i])
            V = np.loadtxt(self.v_files[i])
            Y = np.loadtxt(self.y_files[i])
            row, col = Y.shape
            ######  key code ######
            extend_u = cv2.resize(U, dsize=(col, row), interpolation=cv2.INTER_CUBIC)
            extend_v = cv2.resize(V, dsize=(col, row), interpolation=cv2.INTER_CUBIC)
            dst = cv2.merge((Y, extend_v, extend_u))
            rgb = cv2.cvtColor(dst.astype(np.float32), cv2.COLOR_YUV2RGB)
            rgb = rgb.astype(np.int8)
            rgb = np.array(rgb + 128, np.uint8)
            im = Image.fromarray(rgb)
            im.save("%d.jpeg" % i)

    def deal_mv_matrix(self, folder):
        os.chdir(folder)
        for i in range(len(self.mv_x_files)):
            mv_x = np.loadtxt(self.mv_x_files[i])
            mv_y = np.loadtxt(self.mv_y_files[i])
            row, col = mv_x.shape
            ######  key code ######
            extend_mv_x = cv2.resize(mv_x, dsize=(col * 4, row * 4), interpolation=cv2.INTER_CUBIC)
            extend_mv_y = cv2.resize(mv_y, dsize=(col * 4, row * 4), interpolation=cv2.INTER_CUBIC)
            blank = np.zeros((row * 4, col * 4), dtype=np.float64)
            mv = cv2.merge((extend_mv_x, extend_mv_y, blank))
            mv = mv.astype(np.int8)
            mv = np.array(mv + 128, np.uint8)
            im = Image.fromarray(mv)
            im.save("%d.jpeg" % i)



def single_proecess(array):
    for video in array:
        e = VideoExtracter(video)
        e.save_video_level_features()


def debug():
    e = VideoExtracter('652779091773751607628017706010.mp4')
    # e.save_video_level_features()
    e.load_video_level_features(5)


def run():
    from multiprocessing import Process, cpu_count, Pool
    print(cpu_count())
    videos = []
    with open(os.path.join(TXT_ROOT_URL, 'dataset_sample.txt'), 'r') as f1:
        for line in f1:
            video = line.strip()
            video = os.path.basename(video)
            videos.append(video)
    f1.close()
    groups = partition(videos[2000:], cpu_count() // 4)
    p = Pool(cpu_count() // 4)
    for i in range(cpu_count() // 4):
        p.apply_async(single_proecess, (groups[i],))
    p.close()
    p.join()
    print("finished\n")


if __name__ == '__main__':
    debug()
    # run()
