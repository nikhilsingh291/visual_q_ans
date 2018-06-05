# -*- coding: utf-8 -*-
"""NIKHIL_SINGH_Session7.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eVWYyPEquFMS8oaVh6wJkxh9FsGZEnjE
"""



"""#Deep Learning for Visual Question Answering


![alt text](https://avisingh599.github.io/images/vqa/sample_results.jpg)

This is about answering general english questions based on images by deep learning.

I will be using LSTM+CNN approach to solve this problem and get a better accuracy.
"""

!mkdir data
# %cd data

# Downloads the training and validation sets from visualqa.org. 

!wget http://visualqa.org/data/mscoco/vqa/Questions_Train_mscoco.zip
!wget http://visualqa.org/data/mscoco/vqa/Questions_Val_mscoco.zip
!wget http://visualqa.org/data/mscoco/vqa/Annotations_Train_mscoco.zip
!wget http://visualqa.org/data/mscoco/vqa/Annotations_Val_mscoco.zip

!unzip \*.zip

!ls
# %cd ..
!ls
!mkdir features

# %cd features
!ls
# Downloads and unzips the VGG features computed on the COCO dataset. 

!wget http://cs.stanford.edu/people/karpathy/deepimagesent/coco.zip
!unzip coco.zip -d .

!ls

!pwd
!ls
!pip install spacy

!python3 -m spacy download en

import operator
from itertools import zip_longest
from collections import defaultdict

def selectFrequentAnswers(questions_train, answers_train, images_train, maxAnswers):
	answer_fq= defaultdict(int)
	#build a dictionary of answers
	for answer in answers_train:
		answer_fq[answer] += 1

	sorted_fq = sorted(answer_fq.items(), key=operator.itemgetter(1), reverse=True)[0:maxAnswers]
	top_answers, top_fq = zip(*sorted_fq)
	new_answers_train=[]
	new_questions_train=[]
	new_images_train=[]
	#only those answer which appear int he top 1K are used for training
	for answer,question,image in zip(answers_train, questions_train, images_train):
		if answer in top_answers:
			new_answers_train.append(answer)
			new_questions_train.append(question)
			new_images_train.append(image)

	return (new_questions_train,new_answers_train,new_images_train)

def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)

import numpy as np
from keras.utils import np_utils


def get_questions_tensor_timeseries(questions, nlp, timesteps):
	'''
	Returns a time series of word vectors for tokens in the question

	Input:
	questions: list of unicode objects
	nlp: an instance of the class English() from spacy.en
	timesteps: the number of 

	Output:
	A numpy ndarray of shape: (nb_samples, timesteps, word_vec_dim)
	'''
	assert not isinstance(questions, basestring)
	nb_samples = len(questions)
	word_vec_dim = nlp(questions[0])[0].vector.shape[0]
	questions_tensor = np.zeros((nb_samples, timesteps, word_vec_dim))
	for i in xrange(len(questions)):
		tokens = nlp(questions[i])
		for j in xrange(len(tokens)):
			if j<timesteps:
				questions_tensor[i,j,:] = tokens[j].vector

	return questions_tensor

def get_questions_matrix_sum(questions, nlp):
	'''
	Sums the word vectors of all the tokens in a question
	
	Input:
	questions: list of unicode objects
	nlp: an instance of the class English() from spacy.en

	Output:
	A numpy array of shape: (nb_samples, word_vec_dim)	
	'''
	assert not isinstance(questions, basestring)
	nb_samples = len(questions)
	word_vec_dim = nlp(questions[0])[0].vector.shape[0]
	questions_matrix = np.zeros((nb_samples, word_vec_dim))
	for i in xrange(len(questions)):
		tokens = nlp(questions[i])
		for j in xrange(len(tokens)):
			questions_matrix[i,:] += tokens[j].vector

	return questions_matrix

def get_answers_matrix(answers, encoder):
	'''
	Converts string objects to class labels

	Input:
	answers:	a list of unicode objects
	encoder:	a scikit-learn LabelEncoder object

	Output:
	A numpy array of shape (nb_samples, nb_classes)
	'''
	assert not isinstance(answers, basestring)
	y = encoder.transform(answers) #string to numerical class
	nb_classes = encoder.classes_.shape[0]
	Y = np_utils.to_categorical(y, nb_classes)
	return Y

def get_images_matrix(img_coco_ids, img_map, VGGfeatures):
	'''
	Gets the 4096-dimensional CNN features for the given COCO
	images
	
	Input:
	img_coco_ids: 	A list of strings, each string corresponding to
				  	the MS COCO Id of the relevant image
	img_map: 		A dictionary that maps the COCO Ids to their indexes 
					in the pre-computed VGG features matrix
	VGGfeatures: 	A numpy array of shape (nb_dimensions,nb_images)

	Ouput:
	A numpy matrix of size (nb_samples, nb_dimensions)
	'''
	assert not isinstance(img_coco_ids, basestring)
	nb_samples = len(img_coco_ids)
	nb_dimensions = VGGfeatures.shape[0]
	image_matrix = np.zeros((nb_samples, nb_dimensions))
	for j in xrange(len(img_coco_ids)):
		image_matrix[j,:] = VGGfeatures[:,img_map[img_coco_ids[j]]]

	return image_matrix

import numpy as np
import scipy.io
import sys

from keras.models import Sequential
from keras.layers.core import Dense, Activation, Dropout, Reshape
from keras.layers import Merge
from keras.layers.recurrent import LSTM
from keras.utils import np_utils, generic_utils
from keras.callbacks import ModelCheckpoint, RemoteMonitor

from sklearn.externals import joblib
from sklearn import preprocessing

#from spacy.en import English

#from utils import grouper, selectFrequentAnswers
#from features import get_images_matrix, get_answers_matrix, get_questions_tensor_timeseries

!ls

word_vec_dim= 300
img_dim = 4096
max_len = 30
nb_classes = 1000

questions_train = open('../data/preprocessed/questions_train2014.txt', 'r').read().decode('utf8').splitlines()
questions_lengths_train = open('../data/preprocessed/questions_lengths_train2014.txt', 'r').read().decode('utf8').splitlines()
answers_train = open('../data/preprocessed/answers_train2014_modal.txt', 'r').read().decode('utf8').splitlines()
images_train = open('../data/preprocessed/images_train2014.txt', 'r').read().decode('utf8').splitlines()
vgg_model_path = '../features/coco/vgg_feats.mat'

