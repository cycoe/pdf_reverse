# coding: utf-8

import os
import time
import numpy as np
import fitz

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileReader, PdfFileWriter, PdfFileMerger


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

    def init_image_path(self):
        """
        在每次重新读取 pdf 文件时重置到处的图片列表
        :return: None
        """
        try:
            del self.image_path
            del self.inverse
        except:
            pass
        self.image_path = []
        self.inverse = {}

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
    def convert_to_img(self, pdf_reader, pdf_path, image_path):
        pdf_writer = PdfFileWriter()
        pdf_writer.addPage(pdf_reader)
        pdf_writer.write(open(pdf_path, 'wb'))
        del pdf_writer

        try:
            pdf_page = fitz.open(pdf_path)
        except:
            return False
        trans = fitz.Matrix(1, 1)
        image_page = pdf_page[0].getPixmap(trans, alpha=False)
        image_page.writePNG(image_path)
        del pdf_page, image_page

        return True


    @timer
    def remove_back(self, image_path, color_groups=10, sample=3, border_ratio=0.1, color_tolerant=100):

        color_sep = 256 // color_groups + 1

        image = Image.open(image_path).convert('RGB')
        width = image.size[0]
        height = image.size[1]
        width_sep = width * border_ratio // sample
        height_sep = height * border_ratio // sample
        self.ratio = width / height

        # count the color of all pixel
        counter = np.zeros((color_groups, color_groups, color_groups))
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
            return False
        del counter

        # if np.sum(back_color) < 128 * 3:
        #     black = True
        # else:
        #     black = False

        # 第二种方法

        img_array = np.asarray(image)
        del image
        img_array_grey = np.sum(img_array, axis=2) // 3

        if np.sum(img_array_grey) < 128 * width * height:
            self.inverse[image_path] = True
        else:
            self.inverse[image_path] = False

        back_color_array = np.array([[back_color for x in range(width)] for y in range(height)])
        black_color_array = np.zeros((height, width))
        white_color_array = np.ones((height, width)) * 255

        new_img_array = np.where(
            np.sum(np.abs(img_array - back_color_array), axis=2) > color_tolerant,
            img_array_grey,
            black_color_array if self.inverse[image_path] else white_color_array
        )
        del img_array_grey, img_array, back_color_array, black_color_array, white_color_array

        new_img = Image.fromarray(new_img_array.astype(np.uint8))
        del new_img_array

        if self.inverse[image_path]:
            new_img = ImageOps.invert(new_img)
        new_img.save(image_path)
        del new_img

    @timer
    def convert_to_pdf(self, image_path, pdf_path):
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

        pdf_canvas = canvas.Canvas(pdf_path, pagesize=(new_width, new_height))
        pdf_canvas.drawImage(image_path, 0, 0, new_width, new_height)
        pdf_canvas.drawString(new_width // 20, new_height // 20, 'Powered By Cycoe')
        pdf_canvas.save()
        del pdf_canvas

    @timer
    def clean(self):
        for image_path in self.image_path:
            if os.path.exists(image_path):
                os.remove(image_path)
        if os.path.exists(self.cache_path):
            try:
                os.rmdir(self.cache_path)
            except:
                print('Not a empty directory')

    @timer
    def run(self, file_path, stop_method):
        self.file_path = file_path
        self.init_image_path()
        self.create_cache_dir()

        pdf_reader = PdfFileReader(open(self.file_path, 'rb'))
        pdf_merger = PdfFileMerger()
        self.page_num = pdf_reader.getNumPages()

        for index in range(self.page_num):

            if self.window.STOP:
                stop_method()
                break

            pdf_path = os.sep.join([self.cache_path, '{}.{}'.format(str(index), 'pdf')])
            image_path = os.sep.join([self.cache_path, '{}.{}'.format(str(index), 'png')])
            if self.convert_to_img(pdf_reader.getPage(index), pdf_path, image_path):
                self.remove_back(image_path)
                self.convert_to_pdf(image_path, pdf_path)

            pdf_merger.append(open(pdf_path, 'rb'))

            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

            self.window.progressBar.setValue((index + 1) * 100 // self.page_num)

        pdf_merger.write(open(self.new_file_path, 'wb'))
        pdf_merger.close()
        del pdf_merger, pdf_reader

        self.clean()