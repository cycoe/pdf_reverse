# coding: utf-8

import os
import time

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

    def __init__(self, window):
        self.window = window
        pass

    def init_image_path(self):
        """
        在每次重新读取 pdf 文件时重置到处的图片列表
        :return: None
        """
        self.image_path = []

    def create_cache_dir(self, file_path):
        """
        创建用于存储 pdf 导出的图片的临时目录
        :param file_name: <str> 需要导出的 pdf 文件的绝对路径
        :return: None
        """
        self.file_path = file_path
        self.new_file_path = '{}_new.pdf'.format(file_path[:-4])
        self.parent_path = os.sep.join(self.file_path.split(os.sep)[:-1])
        self.cache_path = os.sep.join([self.parent_path, 'cache'])
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)

    @timer
    def convert_to_img(self, file_name, suffix='jpg', resolution=200):
        image_pdf = Image_pdf(filename=file_name, resolution=resolution)
        image_pdf = image_pdf.convert(suffix)
        for index in range(len(image_pdf.sequence)):
            image_path = os.sep.join([self.cache_path, '{}.{}'.format(str(index), suffix)])
            self.image_path.append(image_path)
            img_page = Image_pdf(image=image_pdf.sequence[index]).make_blob(suffix)
            with open(image_path, 'wb') as fp:
                fp.write(img_page)
        del image_pdf

    @timer
    def inverse(self):
        for image_path in self.image_path:
            image = Image.open(image_path).convert('RGB')
            self.ratio = image.size[0] / image.size[1]

            # pixdata = image.load()
            # light_count = 0
            # black_count = 0
            # for x in range(image.size[0]):
            #     for y in range(image.size[1]):
            #         if sum(pixdata[x, y]) >= 256 * 3 / 2:
            #             light_count += 1
            #         else:
            #             black_count += 1
            #
            # if black_count > light_count:
            #     image = ImageOps.invert(image)
            #     image.save(image_path)

            image = ImageOps.invert(image)
            image.save(image_path)
            del image

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
            os.remove(image_path)
        os.rmdir(self.cache_path)