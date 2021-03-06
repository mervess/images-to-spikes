"""poisson_tools.py:
   Collection of functions to generate Poisson spike trains.
"""
import math
import random
import sys
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime

def plot_digit(img_raw):
    '''Generates a matplotlib plot from the raw pixel array.

        :param img_raw: array containing the pixels for an MNIST digit,
                       should contain 28*28 entries
        '''
    img_raw = np.uint8(img_raw)
    plt.figure(figsize=(5,5))
    im = plt.imshow(np.reshape(img_raw,(28,28)))
    plt.colorbar(im, fraction=0.046, pad=0.04)


def plot_weight(img_raw):
    '''Generates a matplotlib plot from the raw weights array.

        :param img_raw: array containing the weights for
                        pixel-to-neuron connections
    '''
    plt.figure(figsize=(5,5))
    img = plt.imshow(np.reshape(img_raw,(28,28)))
    plt.colorbar(img, fraction=0.046, pad=0.04)


def get_train_data():
    '''Extracts images and labels from the train files obtained from
       http://yann.lecun.com/exdb/mnist/

       :returns: A tuple containing arrays of the images (train_x) and
                 labels (train_y).
    '''
    file_name = 'train-images.idx3-ubyte'
    f = open(file_name, "rb")
    magic_number, list_size, image_hight, image_width  = np.fromfile(f, dtype='>i4', count=4)
    train_x = np.fromfile(f, dtype='>u1', count=list_size*image_hight*image_width)
    train_x = np.reshape(train_x, (list_size,image_hight*image_width))
    f.close()

    file_name = 'train-labels.idx1-ubyte'
    f = open(file_name, "rb")
    magic_number, list_size = np.fromfile(f, dtype='>i4', count=2)
    train_y = np.fromfile(f, dtype='>u1', count=list_size*image_hight*image_width)
    f.close()

    return np.double(train_x), np.double(train_y)


def get_test_data():
    '''Extracts images and labels from the test files obtained from
       http://yann.lecun.com/exdb/mnist/

       :returns: A tuple containing arrays of the images (test_x) and
                 labels (test_y).
    '''
    file_name = 't10k-images.idx3-ubyte'
    f = open(file_name, "rb")
    magic_number, list_size, image_hight, image_width  = np.fromfile(f, dtype='>i4', count=4)
    test_x = np.fromfile(f, dtype='>u1', count=list_size*image_hight*image_width)
    test_x = np.reshape(test_x, (list_size,image_hight*image_width))
    f.close()

    file_name = 't10k-labels.idx1-ubyte'
    f = open(file_name, "rb")
    magic_number, list_size = np.fromfile(f, dtype='>i4', count=2)
    test_y = np.fromfile(f, dtype='>u1', count=list_size*image_hight*image_width)
    f.close()

    return np.double(test_x), np.double(test_y)


def nextTime(rateParameter):
    '''Helper function to Poisson generator
       :param rateParameter: The rate at which a neuron will fire (Hz)

       :returns: Time at which the neuron should spike next (seconds)
    '''
    return -math.log(1.0 - random.random()) / rateParameter
    #random.expovariate(rateParameter)


def poisson_generator(rate, t_start, t_stop):
    '''Poisson train generator
       :param rate: The rate at which a neuron will fire (Hz)
       :param t_start: When should the neuron start to fire (milliseconds)
       :param t_stop: When should the neuron stop firing (milliseconds)

       :returns: Poisson train firing at rate, from t_start to t_stop (milliseconds)
    '''
    poisson_train = []
    if rate > 0:
        next_isi = nextTime(rate)*1000.
        last_time = next_isi + t_start
        while last_time  < t_stop:
            poisson_train.append(last_time)
            next_isi = nextTime(rate)*1000.
            last_time += next_isi
    return poisson_train


def image_to_poisson_trains(image_list, image_height, image_width, max_freq, duration, silence):
    '''Generate Poisson trains for images.
       :param image_list: MNIST image list,  numpy array of size (num images, width*height)
       :param image_height: MNIST digit height
       :param image_width: MNIST digit width
       :param max_freq: Maximum frequency a neuron representing a pixel can fire (Hz)
       :param duration: How long should Poisson trains last (milliseconds)
       :param silence: Time for which no spikes are emmited (milliseconds)

       :returns: A PyNN SpikeSourceArray-formatted representation of a sequence of
                 MNIST digits, interleaved by silence periods
    '''
    if max_freq > 0:
        for i in range(image_list.shape[0]):
            """ NOTE:
            If the spike array wasn't produced at the end, max_freq below
            is more likely to be insufficient(low) for your data.
            """
            image_list[i] = image_list[i]/sum(image_list[i])*max_freq

    spike_source_data = [[] for i in range(image_height*image_width)]

    for i in range(image_list.shape[0]):
        t_start = i*(duration+silence)
        t_stop = t_start+duration
        for j in range(image_height*image_width):
            spikes = poisson_generator(image_list[i][j], t_start, t_stop)
            if spikes != []:
                spike_source_data[j].extend(spikes)

    return spike_source_data


def aerfile_to_spike(file_name, image_size, jaer_size):
    '''Reads an AER file and converts it to a couple of PyNN SpikeSourceArrays.
        :param file_name: Name of the file to open
        :param image_size: Width and height of the image
        :param jaer_size: -Not used?-

        :returns: A spike array for each polarity
    '''
    if os.path.exists(file_name):
        f = open(file_name,'r')
        for i in range(5):
            f.readline()
        All = np.fromfile(f, dtype='>u4')
        All = np.transpose(np.reshape(All,(All.shape[0]/2 , 2)))
        AllTs = np.uint32(All[1])
        AllTs = AllTs.astype(float)/1000.
        AllAddr = np.uint32(All[0])

        xmask = 254 #hex2dec ('fE')  x are 7 bits (64 cols) ranging from bit 1-7
        ymask = 32512 #hex2dec ('7f00')  y are also 7 bits ranging from bit 8 to 14.
        xshift=1 # bits to shift x to right
        yshift=8 # bits to shift y to right
        polmask=1 # polarity bit is LSB


        pol= (AllAddr & polmask) # 0 is on, 1(Polirity = -1) is off
        AllAddr = AllAddr + pol
        x=(AllAddr & xmask) >> xshift
        y=(AllAddr & ymask) >> yshift
        neuron_id = y*image_size+x
        #print pol
        spike_source_array_on = [[] for i in range(image_size*image_size)]
        spike_source_array_off = [[] for i in range(image_size*image_size)]
        for i in range(image_size*image_size):
            index_i = np.where(neuron_id == i)[0]
            index_on = np.where(pol[index_i] == 0)[0]
            index_off = np.where(pol[index_i] == 1)[0]
            if len(index_on) > 0:
                spike_source_array_on[i] = AllTs[index_i[index_on]].tolist()
            if len(index_off) > 0:
                spike_source_array_off[i] = AllTs[index_i[index_off]].tolist()
        return spike_source_array_on, spike_source_array_off
    else:
        return [], []



def spike_to_aerfile(spike_source_array_on, spike_source_array_off,
                     file_name, image_size, jaer_size):
    '''Converts and writes SpikeSourceArrays for ON and OFF polarities
       into an aer-formated file.
        :param spike_source_array_on: Array containing ON events for pixels
        :param spike_source_array_off: Array containing OFF events for pixels
        :param file_name: Name of file to write to
        :param image_size: Width and height of image
        :param jaer_size: -Not used?-

        :returns: An AER representation of the arrays (times, ids, polarities)
    '''

    time_stamp = []
    neuron_id = []

    num_neuron = image_size * image_size
    pol=[]
    # ON events
    if len(spike_source_array_on) == num_neuron:
        for i in range(num_neuron):
            spikes = spike_source_array_on[i]
            if spikes != []:
                time_stamp.extend(spikes)
                neuron_id.extend([i]*len(spikes))
        num_on = len(time_stamp)
        pol = [0] * num_on

    # OFF events
    if len(spike_source_array_off) == num_neuron:
        for i in range(num_neuron):
            spikes = spike_source_array_off[i]
            if spikes != []:
                time_stamp.extend(spikes)
                neuron_id.extend([i]*len(spikes))
        if len(pol)>0:
            pol.extend([-1] * (len(time_stamp)-num_on))
        else:
            pol = [-1] * len(time_stamp)

    if len(time_stamp)>0:
        sort_index = sorted(range(len(time_stamp)), key=time_stamp.__getitem__)
        AllTs = np.uint32(np.ceil(np.array(time_stamp)[sort_index]*1000.)) #in mus
        Polarity = np.array(pol)[sort_index]

        neuron_id = np.array(neuron_id)[sort_index]

        y = neuron_id/image_size
        x = neuron_id%image_size
        AllAddr = np.uint32((x << 1) + (y << 1) * jaer_size + Polarity)
        f = open(file_name,'w')
        tok='#!AER-DAT'
        tok2='# This is a raw AE data file - do not edit'
        tok3='# Data format is int32 address, int32 timestamp (8 bytes total), repeated for each event'
        tok4='# Timestamps tick is 1 us'
        tok5='# Created %s'%(datetime.datetime.now())
        v=2.0

        f.write('%s'%tok)
        f.write('%1.1f\r\n'%v)
        f.write('%s\r\n'%tok2)
        f.write('%s\r\n'%tok3)
        f.write('%s\r\n'%tok4)
        f.write('%s\r\n'%tok5)

        All = np.uint32(np.zeros((2,len(AllTs))))
        All[0] = AllAddr
        All[1] = AllTs
        All = np.reshape(np.transpose(All),(1,len(AllTs)+len(AllAddr)))[0]
        All = All.astype(dtype='>u4')
        All.tofile(f)
        f.close()
        return AllTs, neuron_id, Polarity
    else:
        print('Output is []')
        return []
