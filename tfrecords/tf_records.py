# -*- coding: utf-8 -*- 
# author: liaoming
# python version: python2.7, python3.6 is ok, please note the print function.

from __future__ import print_function
import tensorflow as tf 
import numpy as np 
import cv2 as cv 
import os 
import random 
from tqdm import tqdm

def _int64_feature(value):
    """
    return int64 feature for int label
    """
    return tf.train.Feature(
        int64_list = tf.train.Int64List(value = [value]))

def _bytes_feature(value):
    """
    return bytes feature for image.
    """
    return tf.train.Feature(
        bytes_list = tf.train.BytesList(value = [value]))

def get_image_label_lst_classify(root_dir, cls_dict, out_path,
    eval_ratio = 0.0, shuffle = False, exts = ".png.jpg.jpeg.bmp", sep = " "):
    """
    params:\n
        root_dir: root folder of images. eg: root_dir = "/images/". 
        cls_dict: each class' folder and its specified label. 
            eg: cls_dict = {"bird": 0, "dog": 1}. 
        out_path: the output path of generated train.txt and eval.txt, 
            eg: "./17flowers", then generate "./17flowers_train.txt" and "./17flowers_eval.txt"
        eval_ratio: the percentage of evaluation part of whole datasets. Default = 0.
        shuffle: whether shuffle the train and eval list.
        exts: the acceptable extensions of image file.
        sep: the seprator of image label pair, default is ' '
    return: None, write image label pare to ${out_path}. 
    """
    assert os.path.exists(root_dir), "the specified directory:'{}' \
        is not exist, please check it again.".format(root_dir)
    assert eval_ratio >= 0.0 and eval_ratio <= 1.0, "the eval_ratio must \
        within [0.0, 1.0], but {} got.".format(eval_ratio)
    trains = []
    evals = []
    for sub_dir in cls_dict.keys():
        img_label_pairs = []
        path = os.path.join(root_dir, sub_dir)
        lst = os.listdir(path)
        for each in lst:
            if each.split(".")[-1] in exts:
                img_path = os.path.join(path, each)
                label = cls_dict[sub_dir]
                img_label_pairs.append("{}{}{}\n".format(img_path, sep, label))
        num = int(len(lst) * eval_ratio)
        random.shuffle(img_label_pairs)
        trains += img_label_pairs[num :]
        evals += img_label_pairs[0 : num]
    if shuffle:
        random.shuffle(trains)
        random.shuffle(evals)
    # write trains
    with open(out_path + "_train.txt", "w") as f:
        print("processing train dataset...")
        num = len(trains)
        for idx, each in enumerate(trains):
            f.write(each) 
            percent = idx * 100 / num 
            print("{:3d}%\r".format(percent)) 
    # write evals
    with open(out_path + "_eval.txt", "w") as f:
        print("processing eval dataset...")
        num = len(evals)
        for idx, each in enumerate(evals):
            f.write(each)
            percent = idx * 100 / num 
            print("{:3d}%\r".format(percent))

def get_image_label_lst_segmentation(root_dir, img_dir, label_dir, out_path, 
    sep = " ", img_exts = ".jpg.png.jpeg.bmp", label_exts = ".png"):
    """
    params:\n
        root_dir: the root directory of img_dir and label_dir.
        img_dir: the directory where stores the images.
        label_dir: the label directory where stores the labels correcpond to images.
    return: None, write the image label pare to ${out_path}.
    """
    img_path = os.path.join(root_dir, img_dir)
    label_path = os.path.join(root_dir, label_dir)
    assert os.path.exists(img_path), "could not find the image directory {}".format(img_path)
    assert os.path.exists(label_path), "could not find the label directory {}".format(label_path)
    # get image list
    img_lst = os.listdir(img_path)
    with open(out_path) as f:
        for name_ext in img_lst:
            name_exts = name_ext.split(".")
            if name_exts[1] in img_exts: # check is image
                label = os.path.join(label_path, name_exts[0] + label_exts)
                assert os.path.exists(label), "The label '{}' is not exist. Please check again."
                f.write(os.path.join(img_path, name_ext) + sep + label + "\n")
    

def create_tfrecords(tfr_path, img_label_lst, label_type = "classify", size = None, root_dir = "", sep = " ", angle = 0):
    assert os.path.exists(img_label_lst), "the specified image label list: {} is not exist, please check it again.".format(img_label_lst)
    assert label_type in ["classify", "segmentation"], "Now label_type only supports for classify and segmentation."
    writer = tf.python_io.TFRecordWriter(tfr_path)
    with open(img_label_lst, 'r') as fr:
        lines = fr.readlines()
        print("There {} examples to be written as TFRecords.".format(len(lines)))
        for line in tqdm(lines):
            line = line.split(sep) # ['image_path', 'label_path'] 
            assert 2 == len(line), "line content wrong, it should be [image_path, label_path]"
            # read image
            image = cv.imread(os.path.join(root_dir, line[0])) 
            if None != size:
                h, w = size # Please note the size definition between opencv and tensorflow.
                image = cv.resize(image, (w, h), interpolation = cv.INTER_LINEAR)
            # rotate
            if 0 == angle:
                pass
            elif 90 == angle:
                image = cv.rotate(image, cv.ROTATE_90_CLOCKWISE)
            elif 180 == angle:
                image = cv.rotate(image, cv.ROTATE_180)
            elif 270 == angle:
                image = cv.rotate(image, cv.ROTATE_90_COUNTERCLOCKWISE)
            else:
                print("not supported angle {} degree.".format(angle))
                break
                # cv.ROTATE_180, cv.ROTATE_90_CLOCKWISE, cv.ROTATE_90_COUNTERCLOCKWISE 
            image_raw = image.tobytes() 
            if "classify" == label_type: 
                label = int(line[1]) 
            elif("segmentation" == label_type): 
                label = cv.imread(line[1]) 
                if None != size:
                    cv.resize(label, size, interpolation = cv.INTER_NEAREST) 
                label_raw = label.tobytes()
            else:
                continue 
            if ("classify" == label_type):
                example = tf.train.Example(features = tf.train.Features(feature = {
                     "label": _int64_feature(label),
                     "image_raw": _bytes_feature(image_raw)
                }))
            elif "segmentation" == label_type:
                example = tf.train.Example(features = tf.train.Features(feature = {
                    "label_raw": _bytes_feature(label_raw),
                    "image_raw": _bytes_feature(image_raw)
                }))
            writer.write(example.SerializeToString())
            # line = f.readline()
    writer.close()

# read TFRecords by old methods. 
def read_tfrecords(tfr_path, size, channels, label_type = "classify"):
    reader = tf.TFRecordReader()
    queue = tf.train.string_input_producer([tfr_path])
    _, serialized_example = reader.read(queue)
    assert label_type in ["classify", "segmentation"]
    if "classify" == label_type:
        features = tf.parse_single_example(
            serialized_example,
            features = {
                "image_raw": tf.FixedLenFeature([], dtype = tf.string),
                "label": tf.FixedLenFeature([], tf.int64)
            }
        )
    elif "segmentation" == label_type:
        features = tf.parse_single_example(
            serialized_example,
            features = {
                "label_raw": tf.FixedLenFeature([], dtype = tf.string),
                "image_raw": tf.FixedLenFeature([], dtype = tf.int64)
            }
        )
    image = tf.decode_raw(features["image_raw"], out_type = tf.uint8)
    height, width = size 
    image = tf.reshape(image, shape = [height, width, channels])
    tf.cast(image, tf.float32)
    if "classify" == label_type:
        label = tf.cast(features["label"], dtype = tf.int32)
    elif "segmentation" == label_type:
        label = tf.decode_raw(features["label_raw"], out_type = tf.uint8)
        label = tf.reshape(label, shape = [height, width, 1])
    return image, label

def get_batch(image, label, batch_size, capacity, min_after_dequeue):
    """
    prams:\n
        images: tfrecord returned images.
        labels: tfrecord returned labels.
        batch_size: batch_size
        capacity: 
        min_after_dequeue:
    return: images_batch, labels_batch 
    """
    images, labels =  tf.train.shuffle_batch(
        [image, label],
        batch_size = batch_size,
        capacity = capacity,
        min_after_dequeue = min_after_dequeue)
    return images, tf.reshape(labels, [batch_size])

def transform_img(bgr):
    # you need to define your own transform function.
    pass 

# read TFRecords use new methds(tf.data module)
def read_tfrecords_by_data(tfr_path, size, channel, transform = None,
    label_type = "classify", batch_size = 1, drop_remainder = False,
    buffer_size = 1, seed = None, reshuffle_each_iter = True):
    """
    params:\n
        tfr_path: The TFRecords file path.
        size: resized image size.
        channel: how many channels of input image.
        transform: do some transform for input image.
        labey_type: the type of label. Now surpport for 'classify' and 'segmentation'.
        batch_size: how many image label pair in one batch. 
        drop_remainder: whether drop the remainder in the dataset.
        buffer_size: shuffle at how many image label pair once.
        seed: The random seed been used.
        reshuffle_each_iter: whether shuffle dataset at each iteration.
    return: image and label pair tensor. (You should use sess.run() to get value(np.ndarray).)
    """
    def map_func(tfr):
        if "classify" == label_type:
            features = tf.parse_single_example(tfr,
                features = {
                    "label": tf.FixedLenFeature([], tf.int64),
                    "image_raw": tf.FixedLenFeature([], tf.string)
                })
        elif "segmentation" == label_type:
            features = tf.parse_single_example(tfr,
                features = {
                    "label_raw": tf.FixedLenFeature([], tf.string),
                    "image_raw": tf.FixedLenFeature([], tf.string)
                })
        image = tf.decode_raw(features["image_raw"], tf.uint8)
        height, width = size
        image = tf.reshape(image, [height, width, channel])
        if None != transform:
            image = transform(image)                     # transform image, usually do some data augumentation.
        if "classify" == label_type:
            label = tf.cast(features["label"], tf.int64)
        elif "segmentation" == label_type:
            label = tf.decode_raw(features["label_raw"], tf.uint8)
            label = tf.reshape(label, [height, width, 1]) # 这里仅仅是进行了reshape, single channel
        return image, label 
    
    dataset = tf.data.TFRecordDataset(tfr_path)
    dataset = dataset.map(map_func)
    dataset = dataset.repeat() # dataset repeart times, if None of -1 then repeat inf times.
    dataset = dataset.batch(batch_size, drop_remainder)
    dataset = dataset.shuffle(buffer_size, seed, reshuffle_each_iter)
    iterator = dataset.make_one_shot_iterator()
    image_label_pairs = iterator.get_next() # get next batch
    return image_label_pairs # images, labels

def get_number_examples(tfr_path):
    if type(tfr_path) is str:
        return sum([1 for _ in tf.python_io.tf_record_iterator(tfr_path)])
    elif type(tfr_path) is list:
        num = 0
        for each_path in tfr_path:
            num += get_number_examples(each_path)
        return num
    else:
        print("unknow args.")

###############################################################################
###############################################################################
    
def main(): 
    # print("main function begin!")
    root_dir = "/home/lm/Resnet_classify/data/pc_orientation"
    tfr_path = "./tfrs/val_pc_128.tfr"
    if False:
        cls_dict = {}
        for i in range(17):
            cls_dict["{}".format(i)] = i 
        root_dir = "/media/lm/FILE/dataset/17flowers/"
        get_image_label_lst_classify(root_dir, cls_dict, "./17flowers.txt", shuffle = True)
    if True:
        print("creating tf_records...")
        create_tfrecords(tfr_path, root_dir + "/val.txt", size=(128, 128), root_dir = root_dir)
    if False:
        image, label = read_tfrecords_by_data(tfr_path, size = (224, 224), channel = 3)
        with tf.Session() as sess:
            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess = sess, coord = coord)
            for i in range(10):
                i, l = sess.run([image, label])
                print(type(i), type(l))
                print("image.shape: ", i.shape)
                cv.imshow("image", i[0])
                cv.waitKey() 
                print ("label: {}".format(l[0]))
            # close queue
            coord.request_stop()
            coord.join(threads=threads)
    if False:
        image, label = read_tfrecords(tfr_path, size = (224, 224), channels = 3)
        images, labels = get_batch(image, label, batch_size=2, capacity = 16, min_after_dequeue = 4)
        with tf.Session() as sess:
            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess = sess, coord = coord)
            # print images, labels 
            for i in range(10):
                image_batch, label_batch = sess.run([images, labels])
                # print "image_batch shape: {}, label_batch shape: {}".format(image_batch.shape, label_batch.shape)
                # # print image_batch,
                # print label_batch
                # print tf.reshape(label_batch, [2, 1])
                for idx, img in enumerate(image_batch):
                    # print "label: {}".format(label_batch[idx])
                    cv.imshow("image1", img)
                    cv.waitKey(0)
                    
            coord.request_stop()
            coord.join(threads = threads)
    if False:
        batch_size = 2
        image_label_pairs = read_tfrecords_by_data(tfr_path, (224, 224,), 3, batch_size = batch_size)
        with tf.Session() as sess:
            for i in range(10):
                images, labels = sess.run(image_label_pairs) # run 之后的格式 np.ndarray
                # print "images.type: ", type(images), "labels.type: ", type(labels)
                # print "image.shape:", images.shape, "labels: ", labels 
                for j in range(batch_size):
                    # print "label:", labels[j]
                    cv.imshow("image", images[j])                    
                    cv.waitKey(0) 
    if True:
       print("There are total {:d} examples in {}".format(get_number_examples(tfr_path), tfr_path))
    # print "done!"

if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-r', '--root_dir', type = str, default = "", 
        help = "The root directory of images in list.")
    argparser.add_argument('-t', '--tfr_path', type = str, default = "./data.tfr",
        help = "The file path of TFRecord which will be generated.")
    argparser.add_argument('-l', '--list', type = str, default = "./train.txt",
        help = "The image and label pairs list file.")
    argparser.add_argument('--height', type = int, default = 224,
        help = "The height of image be resize to.")
    argparser.add_argument('-w', '--width', type = int, default = 224,
        help = "The width of image be resized to.")
    argparser.add_argument('-a', '--angle', type = int, default = 0,
        help = "The angle to rotate the image. now support for 0, 90, 180, 270.")
    argparser.add_argument('-s', '--sep', type = str, default = " ",
        help = "The seprator of image label pair.")
    argparser.add_argument('-m', '--mode', type = str, default = "create",
        help = "The model of this file: 1. read -> read TFRecord file. 2. create -> create TFRecord file. 3. count -> count how many exmples in TFRecord file.")
    args = argparser.parse_args()
    
    if "create" == args.mode:
        if os.path.exists(args.tfr_path):
            print("The specified TFRecord file: {} already existed.".format(args.tfr_path))
            print("Program exit!")
        else:
            print("Creating TFRecord file: {}".format(args.tfr_path))
            print("Rotation angle: {} degree.".format(args.angle))
            create_tfrecords(args.tfr_path, 
                         args.list, 
                         size=(args.width, args.height), 
                         root_dir = args.root_dir,
                         angle = args.angle)
            print("TFRecord file generated.")
    elif "count" == args.mode:
        if os.path.exists(args.tfr_path):
            print("There are total {:d} examples in {}".format(get_number_examples(args.tfr_path), args.tfr_path))
        else:
            print("The specified TFRecord file: {} not exist, please check.".format(args.tfr_path))
    elif "read" == args.mode:
         pass
    else:
         print("unknown mode, supported modes: [create, count, read].")

 
    # main()
# FILE END.
