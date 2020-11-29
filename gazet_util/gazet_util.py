
import os
import numpy as np
from tqdm import tqdm
import torch


class gazet():
    def __init__(self, config):
        self.config = config

    def get_list(self):

        gaz_file = open(os.path.join(self.config["root_dir"], self.config["gazet_file"]), 'r', encoding='utf8')
        # gaz_file = open( os.path.join("../../", "data/gazette.txt"), 'r', encoding='utf8')

        dt_list = []
        ps_list = []
        og_list = []
        ti_list = []
        lc_list = []
        
        for line in gaz_file.readlines():
            word_and_tag = line.strip("\n").split("\t")

            if(word_and_tag[1] == "DT"):
                dt_list.append(word_and_tag[0])
            if(word_and_tag[1] == "PS"):
                ps_list.append(word_and_tag[0])
            if(word_and_tag[1] == "OG"):
                og_list.append(word_and_tag[0])
            if(word_and_tag[1] == "TI"):
                ti_list.append(word_and_tag[0])
            if(word_and_tag[1] == "LC"):
                lc_list.append(word_and_tag[0])
        
        word_tag_list = []
        word_tag_list.append(dt_list)
        word_tag_list.append(ps_list)
        word_tag_list.append(og_list)
        word_tag_list.append(ti_list)
        word_tag_list.append(lc_list)

        return word_tag_list

    def get_a_vec(self, tag_list_set, morphs_of_sentence, max_morphs):
        feature = np.zeros(shape=(len(tag_list_set), max_morphs), dtype=np.int)

        for tag_idx, a_tag_list in enumerate(tag_list_set):
            for idx, morph in enumerate(morphs_of_sentence):
                if(idx == max_morphs):
                    break
                if morph in a_tag_list:
                    feature[tag_idx][idx] = 1
                    break

        return feature

    def get_tensor(self, sentences):
        tag_list_set = self.get_list()

        gaz_feature_list = []
        for sentence in sentences:
            gaz_feature = self.get_a_vec(tag_list_set, sentence, self.config["max_morphs"])
            gaz_feature_list.append(gaz_feature)

        # (sentences_size, number_of_tags, curr_max_length)
        gaz_feature_list = np.array(gaz_feature_list)
        gaz_feature_list = torch.tensor(gaz_feature_list ,dtype=torch.long)
        gaz_feature_list = gaz_feature_list.permute(0, 2, 1)

        return gaz_feature_list