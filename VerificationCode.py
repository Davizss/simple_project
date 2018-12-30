#!/usr/bin/env python
# -*- coding:utf-8 -*-
# 本文件的作用：验证码识别类
#  ccn验证码识别：https://github.com/ypwhs/captcha_break/blob/master/cnn.ipynb
import sys
import os
import time
import random
import string
import numpy as np
from datetime import datetime
# import matplotlib.pyplot as plt
# import matplotlib.image as mpimg
from captcha.image import ImageCaptcha
import keras
from keras.utils.np_utils import to_categorical
from keras.models import Model, Input
from keras.layers import Convolution2D, MaxPool2D, Flatten, Dropout, Dense, BatchNormalization
from keras.utils.vis_utils import plot_model
from tqdm import tqdm
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# 生成验证码的字符集
CHARACTERS = string.digits + string.ascii_uppercase
# 验证码图片的宽，高，字符数量(分类长度)，字符集长度(分类数量)
WIDTH = 170
HEIGHT = 80
CHAR_LEN = 4
CHAR_CLASS = 36
LOSS = []


def gen(batch_size=32):
    """
    数据生成器，因为while True，会一直给出训练集(batch_size个)和答案集(barch_size个)
    :param batch_size:
    :return:
    """
    # 创建一个4维的零数组X  第一维是训练图片的数量，剩余的三维分别包含了图片在三个维度上的信息
    X = np.zeros((batch_size, HEIGHT, WIDTH, 3), dtype=np.uint8)
    # y是一个数组，长度为分类的长度，每一个表示一个验证码图片在分类长度(第一到第四)上的落点(如果是0，落在第1个上，是z则落在最后1个上面)
    y = [np.zeros((batch_size, CHAR_CLASS), dtype=np.uint8) for _ in range(CHAR_LEN)]
    # 实例化captcha提供的生成验证码的类，每调用一次generate_image就给出一个验证码
    generator = ImageCaptcha(width=WIDTH, height=HEIGHT)
    while True:
        for i in range(batch_size):
            # 随机生成的验证码字符串
            random_str = ''.join([random.choice(CHARACTERS) for _ in range(4)])
            # 生成验证码对象
            X[i] = generator.generate_image(random_str)
            # 遍历验证码字符串
            for j, ch in enumerate(random_str):
                # 将数据归0
                y[j][i:, ] = 0
                # 存储拥有的字符的落点
                y[j][i, CHARACTERS.find(ch)] = 1
        yield X, y


def data_gen_test():
    """
    测试生成器
    :return:
    """
    X, y = next(gen(1))
    # plt.imshow(X[0])
    # plt.title(decode(y))
    # plt.show()


def view_model(model):
    """
    将模型可视化
    :param model: keras模型
    :return: None
    """
    # plot_model(model, to_file='model.png')
    # # model_img = mpimg.imread('model.png')
    # plt.imshow(model_img)
    # plt.title('模型')
    # # 展示模型
    # plt.show()


def decode(y):
    """
    解析数组为对应的验证码字符串
    对于概率数组 会找出最大概率吃的一组数据作为预测的验证码字符串
    :param y: 数组
    :return: None
    """
    # 返回横轴上的最大值,因为有概率的问题，所以找出概率最大的作为预测的字符
    y = np.argmax(np.array(y), axis=2)[:, 0]
    # 解析出最终的字符串
    return ''.join([CHARACTERS[x] for x in y])


def create_model():
    """
    创建模型
    :return:None
    """
    # 输入层
    input_tensor = Input((HEIGHT, WIDTH, 3))
    # x是输入的数据
    x = input_tensor
    # 循环四次，每一次添加两个二维的卷积层(过滤器为3*3的大小，激活函数是ReLU)和一个最大池形式的池化层
    for i in range(4):
        x = Convolution2D(32 * 2 ** i, 3, 3, activation='relu')(x)
        x = Convolution2D(32 * 2 ** i, 3, 3, activation='relu')(x)
        x = BatchNormalization()(x)
        x = MaxPool2D((2, 2))(x)
    # 扁平化层
    x = Flatten()(x)
    # Dropout层 避免过拟合问题
    x = Dropout(0.25)(x)
    # 全连接层
    x = [Dense(CHAR_CLASS, activation='softmax', name='c%d' % (i + 1))(x) for i in range(4)]
    # 创建模型
    model = Model(input=input_tensor, output=x)
    model.compile(loss='categorical_crossentropy',
                  optimizer='adadelta',
                  metrics=['accuracy'])
    return model


def evaluate(model, batch_num=20):
    """
    计算模型整体准确率
    :param model: 用来测试的模型
    :param batch_num:
    :return: 模型整体准确率
    """
    batch_acc = 0
    generator = gen()
    for i in tqdm(range(batch_num)):
        X, y = next(generator)
        y_pred = model.predict(X)
        batch_acc += np.mean(np.argmax(y, axis=2).T == np.argmax(y_pred, axis=2).T)
    return batch_acc / batch_num


def main():
    # model = create_model()
    model = keras.models.load_model('cnn_captcha_recognize.h5')
    # 训练模型
    hist = model.fit_generator(
        gen(),
        # 每一代训练的branch数量
        samples_per_epoch=25,
        # 循环的次数(5代)
        nb_epoch=60,
        validation_data=gen(),
        nb_val_samples=100
    )
    d = hist.history
    with open('hist.json', 'w') as f:
        json.dump(d, f)
    # 测试模型
    X, y = next(gen(1))
    y_pred = model.predict(X)
    # plt.title('real:{} \n pred:{}'.format(decode(y), decode(y_pred)))
    # plt.imshow(X[0], cmap='gray')
    # plt.axis('off')
    # plt.show()

    # 计算模型整体准确率
    evaluate(model)
    # 保存模型
    model.save('cnn_captcha_recognize.h5')


if __name__ == '__main__':
    main()
