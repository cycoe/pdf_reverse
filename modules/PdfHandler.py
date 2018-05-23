# coding: utf-8

import os
import time
import numpy as np

from wand.image import Image as Image_pdf
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print('function <{}> run for {} seconds...'.format(func.__name__, str(end - start)))
        return result
    return wrapper



class PdfHandler(object):

    def __init__(self):
        pass

    def init_image_path(self):
        """
        在每次重新读取 pdf 文件时重置到处的图片列表
        :return: None
        """
        self.image_path = []

    def create_cache_dir(self):
        """
        创建用于存储 pdf 导出的图片的临时目录
        :param file_name: <str> 需要导出的 pdf 文件的绝对路径
        :return: None
        """
        self.new_file_path = '{}_new.pdf'.format(self.file_path[:-4])
        self.parent_path = os.sep.join(self.file_path.split(os.sep)[:-1])
        self.cache_path = os.sep.join([self.parent_path, 'cache'])
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)

    @timer
    def convert_to_img(self, suffix='jpg', resolution=100):
        image_pdf = Image_pdf(filename=self.file_path, resolution=resolution)
        image_pdf = image_pdf.convert(suffix)
        for index in range(len(image_pdf.sequence)):
            image_path = os.sep.join([self.cache_path, '{}.{}'.format(str(index), suffix)])
            self.image_path.append(image_path)
            img_page = Image_pdf(image=image_pdf.sequence[index]).make_blob(suffix)
            with open(image_path, 'wb') as fp:
                fp.write(img_page)
            del img_page
        del image_pdf

    @timer
    def remove_back(self, color_groups=10, sample=3, border_ratio=0.1, color_tolerant=100):

        color_sep = 256 // color_groups + 1

        for image_path in self.image_path:
            counter = np.zeros((color_groups, color_groups, color_groups))
            image = Image.open(image_path).convert('RGB')
            width = image.size[0]
            height = image.size[1]
            width_sep = width * border_ratio // sample
            height_sep = height * border_ratio // sample
            self.ratio = width / height

            # count the color of all pixel
            pixData = image.load()
            for x in range(sample):
                for y in range(height):
                    data = pixData[width_sep * x, y]
                    counter[data[0] // color_sep][data[1] // color_sep][data[2] // color_sep] += 1
                    data = pixData[width - width_sep * x - 1, y]
                    counter[data[0] // color_sep][data[1] // color_sep][data[2] // color_sep] += 1

            for x in range(width):
                for y in range(sample):
                    data = pixData[x, height_sep * y]
                    counter[data[0] // color_sep][data[1] // color_sep][data[2] // color_sep] += 1
                    data = pixData[x, height - height_sep * y - 1]
                    counter[data[0] // color_sep][data[1] // color_sep][data[2] // color_sep] += 1
            del pixData

            # get the main background color
            i, j, k = np.unravel_index(counter.argmax(), counter.shape)
            if counter[i][j][k] / np.sum(counter) >= 0.3:
                back_color = np.array([i ,j, k]) * color_sep
            elif 0.3 > counter[i][j][k] / np.sum(counter) >= 0.1:
                primary_color = np.array([i, j, k]) * color_sep
                counter[i][j][k] = 0
                i, j, k = np.unravel_index(counter.argmax(), counter.shape)
                if counter[i][j][k] / np.sum(counter) >= 0.3:
                    second_color = np.array([i, j, k]) * color_sep
                    back_color = (primary_color + second_color) // 2
                else:
                    back_color = primary_color
            else:
                del counter
                continue
            del counter

            if np.sum(back_color) <= 256 * 3 / 2:
                inverse = True
            else:
                inverse = False

            # 第二种方法
            # black_color = np.array([0, 0, 0])
            # white_color = np.array([256, 256, 256])

            img_array = np.asarray(image)
            del image

            back_color_array = np.array([[back_color for x in range(width)] for y in range(height)])
            black_color_array = np.array([[0 for x in range(width)] for y in range(height)])
            white_color_array = np.array([[256 for x in range(width)] for y in range(height)])

            new_img_array = np.where(
                np.sum(np.abs(img_array - back_color_array), axis=2) > color_tolerant,
                np.sum(img_array, axis=2) // 3,
                black_color_array if inverse else white_color_array
            )
            del img_array, back_color_array, black_color_array, white_color_array

            new_img = Image.fromarray(new_img_array.astype(np.uint8))
            del new_img_array

            if inverse:
                new_img = ImageOps.invert(new_img)
            new_img.save(image_path)
            del new_img

    @timer
    def convert_to_pdf(self):
        if self.ratio <= 1:
            (width, height) = A4
        else:
            (width, height) = landscape(A4)

        if self.ratio > width / height:
            new_width = width
            new_height = width / self.ratio
        else:
            new_width = height * self.ratio
            new_height = height

        pdf_canvas = canvas.Canvas(self.new_file_path, pagesize=(new_width, new_height))
        for image_path in self.image_path:
            pdf_canvas.drawImage(image_path, 0, 0, new_width, new_height)
            pdf_canvas.showPage()
        pdf_canvas.save()
        del pdf_canvas

    @timer
    def clean(self):
        for image_path in self.image_path:
            if os.path.exists(image_path):
                os.remove(image_path)
        if os.path.exists(self.cache_path):
            os.rmdir(self.cache_path)

    def run(self, file_path):
        self.file_path = file_path
        self.init_image_path()
        self.create_cache_dir()
        self.convert_to_img()
        self.remove_back()
        self.convert_to_pdf()
        self.clean()
