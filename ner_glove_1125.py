# -*- coding: utf-8 -*-
"""ner_glove_1125.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RvKJJ8dvfOfuMDNXZFO9EczNhj8WX7nW

# 해커톤 2차 baseline + Glove
- updated 1125
- ref https://keep-steady.tistory.com/20

## ready
"""

from google.colab import drive
drive.mount('/content/drive')

cd /content/drive/MyDrive/AI_Hackathon_konkuk2/baseline

# Commented out IPython magic to ensure Python compatibility.
# ready 한꺼번에 import 
import pandas as pd
import numpy as np

import sys
np.set_printoptions(threshold=sys.maxsize)
import os
import tqdm
import warnings
warnings.filterwarnings(action='ignore')
import pickle
import joblib

from IPython.display import display
pd.options.display.max_rows = 999
pd.options.display.max_columns = 999

import re

# visualization
from matplotlib import pyplot as plt
plt.style.use('seaborn')
import seaborn as sns
# %matplotlib inline

# display
from IPython.display import Image

"""## Load data & Tokenizing
- elmo -> tf 1.0 필요
- https://github.com/lovit/soynlp (비지도학습 지향)

"""

!pip install glove_python

# !pip install soynlp

"""### train data 로드하고 전처리 없이 형태소 분석한 후에 glove 로 임베딩"""

!pip install konlpy

from konlpy.tag import * 
from gensim.models import Word2Vec, fasttext

# load data
def load_data(path):
    sentences = []
    labels = []

    with open(path, 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
        for line in lines:
            _, sentence, label = line.strip().split('\t')
            cleaned_sentence = re.sub('[^ㄱ-ㅎㅏ-ㅣ가-힣]+', ' ', sentence).strip()
            if cleaned_sentence:
                sentences.append(re.sub(' ','',str(cleaned_sentence)))
               
        return sentences

train = load_data("/content/drive/MyDrive/AI_Hackathon_konkuk2/baseline/ner_train.txt")

# 1차 해커톤 문근님 함수 이용
okt=Okt()  
# sentence는 한 문장임.
def tknz(sentence):
    s = okt.pos(sentence)
    x = []
    for w in s:
				# w[0] : 단어 / w[1] = 품사
				# modifer 오타 실화? ~..~
        if w[1] == 'Josa' or w[1] == 'Punctuation' or w[1] == 'Number' or w[1] == 'Modifer' or w[1] == 'Eomi':
            continue
        else: x.append(w[0])
	 # 거를 거 거른 단어들의 리스트를 반환한다.
    return x

tokens = []
for sentence in train:
    x = tknz(str(sentence))
    tokens.append(x)

with open('train_token_1124.pickle', 'wb') as f:
    pickle.dump(tokens, f)

# load token
train_token = joblib.load(os.path.join('train_token_1124.pickle'))

from glove import Corpus, Glove

# corpus
corpus = Corpus() 
corpus.fit(tokens, window=10)

# model
glove = Glove(no_components=128, learning_rate=0.05)
glove.fit(corpus.matrix, epochs=10000, no_threads=4, verbose=False)
glove.add_dictionary(corpus.dictionary)

"""## Save & Load Glove
sentence representation 보기위한 임베딩  
오버피팅
"""

# # save
# glove.save('glove_train_1124.model')

"""https://www.kaggle.com/francoisdubois/build-a-word-embedding-with-glove-matrix"""

# load glove
glove_model = Glove.load('glove_train_1124.model')

# word dict
word_dict = {}
for word in  glove_model.dictionary.keys():
    word_dict[word] = glove_model.word_vectors[glove_model.dictionary[word]]

print('Lengh of word dict... : ', len(word_dict))

# embedding_vectors
emb_mat = np.zeros((len(train_token),128))

for i,morphs in enumerate(train_token):
    vector = np.array([word_dict[morph] for morph in morphs])
    #print(vector.shape)
    final_vector = np.mean(vector,axis=0)
    #final_vector = vector.T.mean(axis=1)
    #emb_sentences.append(final_vector)
    emb_mat[i] = final_vector

print('Eebedding vector 120 dim.... : ', emb_mat.shape)

# 저장을 원한다면 pickle 파일로





"""# Model"""

# ready
!pip install pytorch-crf
!pip install seqeval==1.0.0

# torch
import torch
import torch.nn as nn
from torchcrf import CRF
from torch.utils.data import (DataLoader, TensorDataset)
import torch.optim as optim

# eval
from seqeval.metrics import classification_report

class RNN_CRF(nn.Module):
    def __init__(self, config):
        super(RNN_CRF, self).__init__()

        # 전체 음절 개수
        self.eumjeol_vocab_size = config["word_vocab_size"]

        # 음절 임베딩 사이즈
        self.embedding_size = config["embedding_size"]

        # GRU 히든 사이즈
        self.hidden_size = config["hidden_size"]

        # 분류할 태그의 개수
        self.number_of_tags = config["number_of_tags"]

        # 입력 데이터에 있는 각 음절 index를 대응하는 임베딩 벡터로 치환해주기 위한 임베딩 객체
        self.embedding = nn.Embedding(num_embeddings=self.eumjeol_vocab_size,
                                      embedding_dim=self.embedding_size,
                                      padding_idx=0)

        self.dropout = nn.Dropout(config["dropout"])

        # Bi-GRU layer
        self.bi_gru = nn.GRU(input_size = self.embedding_size,
                             hidden_size= self.hidden_size,
                             num_layers=1,
                             batch_first=True,
                             bidirectional=True)

        # CRF layer
        self.crf = CRF(num_tags=self.number_of_tags, batch_first=True)

        # fully_connected layer를 통하여 출력 크기를 number_of_tags에 맞춰줌
        # (batch_size, max_length, hidden_size*2) -> (batch_size, max_length, number_of_tags)
        self.hidden2num_tag = nn.Linear(in_features=self.hidden_size*2, out_features=self.number_of_tags)

    def forward(self, inputs, labels=None):
        # (batch_size, max_length) -> (batch_size, max_length, embedding_size)
        eumjeol_inputs = self.embedding(inputs)

        encoder_outputs, hidden_states = self.bi_gru(eumjeol_inputs)

        # (batch_size, curr_max_length, hidden_size*2)
        d_hidden_outputs = self.dropout(encoder_outputs)

        # (batch_size, curr_max_length, hidden_size*2) -> (batch_size, curr_max_length, number_of_tags)
        logits = self.hidden2num_tag(d_hidden_outputs)

        if(labels is not None):
            log_likelihood = self.crf(emissions=logits,
                                      tags=labels,
                                      reduction="mean")

            loss = log_likelihood * -1.0

            return loss
        else:
            output = self.crf.decode(emissions=logits)

            return output

"""# Load data"""

# 파라미터로 입력받은 파일에 저장된 단어 리스트를 딕셔너리 형태로 저장
def load_vocab(f_name):
    vocab_file = open(os.path.join(root_dir, f_name),'r',encoding='utf8')
    print("{} vocab file loading...".format(f_name))

    # default 요소가 저장된 딕셔너리 생성
    symbol2idx, idx2symbol = {"<PAD>":0, "<UNK>":1}, {0:"<PAD>", 1:"<UNK>"}

    # 시작 인덱스 번호 저장
    index = len(symbol2idx)
    for line in tqdm(vocab_file.readlines()):
        symbol = line.strip()
        symbol2idx[symbol] = index
        idx2symbol[index]= symbol
        index+=1

    print(f'total len of {f_name}... : ',len(symbol2idx))   # Add length
    return symbol2idx, idx2symbol

# 입력 데이터를 고정 길이의 벡터로 표현하기 위한 함수
def convert_data2feature(data, symbol2idx, max_length=None):
    # 고정 길이의 0 벡터 생성
    feature = np.zeros(shape=(max_length), dtype=np.int)
    # 입력 문장을 공백 기준으로 split
    words = data.split()

    for idx, word in enumerate(words[:max_length]):
        if word in symbol2idx.keys():
            feature[idx] = symbol2idx[word]
        else:
            feature[idx] = symbol2idx["<UNK>"]
    return feature

# 파라미터로 입력받은 파일로부터 tensor객체 생성
def load_data(config, f_name, word2idx, tag2idx):
    file = open(os.path.join(root_dir, f_name),'r',encoding='utf8')

    # return할 문장/라벨 리스트 생성
    indexing_inputs, indexing_tags = [], []

    print("{} file loading...".format(f_name))

    # 실제 데이터는 아래와 같은 형태를 가짐
    # 문장 \t 태그
    # 세 종 대 왕 은 <SP> 조 선 의 <SP> 4 대 <SP> 왕 이 야 \t B_PS I_PS I_PS I_PS O <SP> B_LC I_LC O <SP> O O <SP> O O O
    for line in tqdm(file.readlines()):
        try:
            id, sentence, tags = line.strip().split('\t')
        except:
            id, sentence = line.strip().split('\t')
        input_sentence = convert_data2feature(sentence, word2idx, config["max_length"])
        indexing_tag = convert_data2feature(tags, tag2idx, config["max_length"])

        indexing_inputs.append(input_sentence)
        indexing_tags.append(indexing_tag)
    indexing_inputs = torch.tensor(indexing_inputs, dtype=torch.long)
    indexing_tags = torch.tensor(indexing_tags, dtype=torch.long)

    # Add check load data
    print('\ncheck indexing_inputs... : ', indexing_inputs.shape, indexing_inputs[0])   
    print('check indexing_tags... : ',indexing_tags.shape, indexing_tags[0])   

    return indexing_inputs, indexing_tags

# tensor 객체를 리스트 형으로 바꾸기 위한 함수
def tensor2list(input_tensor):
    return input_tensor.cpu().detach().numpy().tolist()

"""# Setting Train & Test"""

def train(config):
    # 모델 객체 생성
    model = RNN_CRF(config).cuda()
    # 단어 딕셔너리 생성
    word2idx, idx2word = load_vocab(config["word_vocab_file"])
    tag2idx, idx2tag = load_vocab(config["tag_vocab_file"])

    # 데이터 Load
    train_input_features, train_tags = load_data(config, config["train_file"], word2idx, tag2idx)
    test_input_features, test_tags = load_data(config, config["dev_file"], word2idx, tag2idx)

    # 불러온 데이터를 TensorDataset 객체로 변환
    train_features = TensorDataset(train_input_features, train_tags)
    train_dataloader = DataLoader(train_features, shuffle=True, batch_size=config["batch_size"])

    test_features = TensorDataset(test_input_features, test_tags)
    test_dataloader = DataLoader(test_features, shuffle=False, batch_size=config["batch_size"])

    # 모델을 학습하기위한 optimizer
    optimizer = optim.Adam(model.parameters(), lr=0.005)

    accuracy_list = []
    for epoch in range(config["epoch"]):
        model.train()
        losses = []
        for step, batch in enumerate(train_dataloader):
            # .cuda()를 이용하여 메모리에 업로드
            batch = tuple(t.cuda() for t in batch)
            input_features, labels = batch

            # loss 계산
            loss = model.forward(input_features, labels)

            # 변화도 초기화
            optimizer.zero_grad()

            # loss 값으로부터 모델 내부 각 매개변수에 대하여 gradient 계산
            loss.backward()

            # 모델 내부 각 매개변수 가중치 갱신
            optimizer.step()

            if (step + 1) % 50 == 0:
                # Add epoch
                print(f'epoch_{epoch + 1}_train')
                print("{} step processed.. current loss : {}".format(step + 1, loss.data.item()))
            losses.append(loss.data.item())



        print("Average Loss : {}".format(np.mean(losses)))

        # 모델 저장
        torch.save(model.state_dict(), os.path.join(config["output_dir_path"], "epoch_{}.pt".format(epoch + 1)))

        do_test(model, test_dataloader, idx2tag)



def test(config):
    # 모델 객체 생성
    model = RNN_CRF(config).cuda()
    # 단어 딕셔너리 생성
    word2idx, idx2word = load_vocab(config["word_vocab_file"])
    tag2idx, idx2tag = load_vocab(config["tag_vocab_file"])


    # 저장된 가중치 Load
    model.load_state_dict(torch.load(os.path.join(config["output_dir_path"], config["trained_model_name"])))

    # 데이터 Load
    test_input_features, test_tags = load_data(config, config["dev_file"], word2idx, tag2idx)

    # 불러온 데이터를 TensorDataset 객체로 변환
    test_features = TensorDataset(test_input_features, test_tags)
    test_dataloader = DataLoader(test_features, shuffle=False, batch_size=config["batch_size"])
    # 평가 함수 호출
    do_test(model, test_dataloader, idx2tag)

def do_test(model, test_dataloader, idx2tag):
    model.eval()
    predicts, answers = [], []
    for step, batch in enumerate(test_dataloader):
        # .cuda() 함수를 이용하요 메모리에 업로드
        batch = tuple(t.cuda() for t in batch)

        # 데이터를 각 변수에 저장
        input_features, labels = batch

        # 예측 라벨 출력
        output = model(input_features)

        # 성능 평가를 위해 예측 값과 정답 값 리스트에 저장
        for idx, answer in enumerate(tensor2list(labels)):
            answers.extend([idx2tag[e].replace("_", "-") for e in answer if idx2tag[e] != "<SP>" and idx2tag[e] != "<PAD>"])
            predicts.extend([idx2tag[e].replace("_", "-") for i, e in enumerate(output[idx]) if idx2tag[answer[i]] != "<SP>" and idx2tag[answer[i]] != "<PAD>"] )
    
    # 성능 평가
    print(classification_report(answers, predicts))

"""# main"""

##########################################################
#                                                        #
#        평가 기준이 되는 지표는 Macro F1 Score                #
#           제출 포맷은 id \t predict_tag                   #
#            25 \t B_PS I_PS <SP> O O O ...              #
#                                                        #
##########################################################


import os
if(__name__=="__main__"):
    output_dir = os.path.join(root_dir, "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    config = {"mode": "train",
              "train_file":"ner_train.txt",
              "dev_file": "ner_dev.txt",
              "word_vocab_file":"vocab.txt",
              "tag_vocab_file":"tag_vocab.txt",
              "trained_model_name":"epoch_{}.pt".format(5),
              "output_dir_path":output_dir,
              "word_vocab_size":2160,
              "number_of_tags": 14,
              "hidden_size": 100,
              "dropout":0.2,
              "embedding_size":100,
              "max_length": 120,
              "batch_size":64,
              "epoch":5,
              }

    if(config["mode"] == "train"):
        train(config)
    else:
        test(config)



"""## baseline
- bi-GRU + CRF 모델 -> 2-layer


## 시도해볼만한 것
- deep layer
- pos 인풋으로 넣기
- CNN layer
- pre train 임베딩
- 후처리
- 텐서보드 empirical 한 실험

"""

