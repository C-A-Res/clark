import math

import numpy as np
from sklearn.metrics import confusion_matrix

from graphing_helpers import plot_confusion_matrix
from models.base.base_emotion_model import BaseEmotionModel
from nlp_helpers import (determine_pronoun, determine_tense, flatten,
                         ngrams_and_remove_stop_words, normalize,
                         parts_of_speech, tokenize)

np.seterr(all="raise")


class AVModel(BaseEmotionModel):
    """
    TODO 
    """

    def __init__(self, ngram_choice):
        super().__init__()
        self.ngrams = {}
        self.priors = {}
        self.variable_dimensions = ["low", "med", "high"]
        self.micro_fscores = {}
        self.macro_fscores = {}
        self.tense = {var: self.__init_tense() for var in self.variables}
        self.pronouns = {var: self.__init_pronouns() for var in self.variables}
        self.true = {}
        self.pred = {}
        self.ngram_choice = ngram_choice

    def __init_tense(self):
        return {
            "past": {dim: 1 for dim in self.variable_dimensions},
            "present": {dim: 1 for dim in self.variable_dimensions},
            "future": {dim: 1 for dim in self.variable_dimensions}
        }

    def __init_pronouns(self):
        return {
            "first": {dim: 1 for dim in self.variable_dimensions},
            "second": {dim: 1 for dim in self.variable_dimensions},
            "third": {dim: 1 for dim in self.variable_dimensions}
        }

    def train(self, training_data):
        """
        Builds a trained CLARK model

        Parameters:
        training_data (array): training data used to train the model

        Returns:
        Model: a trained model
        """

        for var in self.variables:
            self.__train_by_variable(training_data, var)

    def _train_by_variable(self, training_set, variable, data_points={}):
        """
        Calculates the counts for each unigram and priors for each classification

        Parameters:
        training_set (array): training data used to train the model
        variable (string): variable in use in training

        Returns:
        Object: ngrams with associated counts
        Object: sums for each classification
        Object: priors for each classification
        """

        words = {}
        words_totals = {dim: 0 for dim in self.variable_dimensions}
        tense_totals = {dim: 0 for dim in self.variable_dimensions}
        pronoun_totals = {dim: 0 for dim in self.variable_dimensions}
        words_vocab = set()
        tense_vocab = set()
        pronoun_vocab = set()

        for row in training_set:
            for turn in ["turn1", "turn2", "turn3"]:
                true_dim = self.variable_dimensions[int(
                    row[turn]["appraisals"][variable])]
                tokenized_res = tokenize(row[turn]["text"])

                pos = parts_of_speech(tokenized_res)
                tense_vocab, tense_totals, pronoun_vocab, pronoun_totals = self.__build_pos_counts(
                    pos, tense_vocab, variable, true_dim, tense_totals, pronoun_vocab, pronoun_totals)

                res = ngrams_and_remove_stop_words(
                    tokenized_res, self.ngram_choice)
                words_vocab, words, words_totals = self.__build_word_counts(
                    res, words_vocab, words, true_dim, words_totals)

        denom = sum(words_totals.values())
        self.priors[variable] = {dim: float(
            words_totals[dim])/float(denom) for dim in self.variable_dimensions}

        self.__calculate_probabilities(
            words, words_totals, words_vocab, tense_totals, tense_vocab, pronoun_totals, pronoun_vocab, variable)

    def __build_word_counts(self, res, words_vocab, words, true_dim, words_totals):
        for word in res:
            words_vocab.add(word)
            if word in words:
                words[word][true_dim] += 1
                words_totals[true_dim] += 1
            else:
                words[word] = self.__initialize_av_weights()
                words[word][true_dim] += 1
                words_totals[true_dim] += 1
        return words_vocab, words, words_totals

    def __build_pos_counts(self, pos, tense_vocab, variable, true_dim, tense_totals, pronoun_vocab, pronoun_totals):
        for p in pos:
            p_tense = determine_tense(p)
            p_pronoun = determine_pronoun(p)
            if p_tense != "":
                tense_vocab.add(p_tense)
                self.tense[variable][p_tense][true_dim] += 1
                tense_totals[true_dim] += 1
            if p_pronoun != "":
                pronoun_vocab.add(p_pronoun)
                self.pronouns[variable][p_pronoun][true_dim] += 1
                pronoun_totals[true_dim] += 1
        return tense_vocab, tense_totals, pronoun_vocab, pronoun_totals

    def __initialize_av_weights(self):
        return {dim: 1 for dim in self.variable_dimensions}

    def __calculate_probabilities(self, words, words_totals, words_vocab, tense_totals, tense_vocab, pronoun_totals, pronoun_vocab, curr_var):
        """
        TODO
        """

        len_vocab = len(words_vocab)

        for word in words:
            for dim in self.variable_dimensions:
                words[word][dim] = float(
                    words[word][dim])/float(words_totals[dim] + len_vocab)

        self.ngrams[curr_var] = words

        for tense in ["past", "present", "future"]:
            for dim in self.variable_dimensions:
                self.tense[curr_var][tense][dim] = float(
                    self.tense[curr_var][tense][dim])/float(tense_totals[dim]+len(tense_vocab))

        for pronoun in ["first", "second", "third"]:
            for dim in self.variable_dimensions:
                self.pronouns[curr_var][pronoun][dim] = float(
                    self.pronouns[curr_var][pronoun][dim])/float(pronoun_totals[dim]+len(pronoun_vocab))

    def test(self, testing_data):
        """
        Tests the precision/recall of the model

        Parameters:
        testing_data (array): data on which to test the model

        Returns:
        Null
        """

        for var in self.variables:
            self.true[var] = []
            self.pred[var] = []

        for row in testing_data:
            u_priors = dict(self.priors)

            tokenized_turn1 = tokenize(row["turn1"]["text"])
            tokenized_turn2 = tokenize(row["turn2"]["text"])
            tokenized_turn3 = tokenize(row["turn3"]["text"])

            conv = tokenized_turn1 + tokenized_turn2 + tokenized_turn3

            parsed_message = flatten([ngrams_and_remove_stop_words(x, self.ngram_choice) for x in [
                                     tokenized_turn1, tokenized_turn2, tokenized_turn3]])
            for var in self.variables:
                classification = normalize(self.__classify(
                    self.ngrams[var], parsed_message, conv, u_priors[var], var))
                for i, e in enumerate(self.variable_dimensions):
                    u_priors[var][e] = classification[i]

            parsed_message = ngrams_and_remove_stop_words(
                tokenized_turn1, self.ngram_choice)
            for var in self.variables:
                classification = normalize(self.__classify(
                    self.ngrams[var], parsed_message, tokenized_turn1, u_priors[var], var))
                for i, e in enumerate(self.variable_dimensions):
                    u_priors[var][e] = classification[i]

            parsed_message = ngrams_and_remove_stop_words(
                tokenized_turn3, self.ngram_choice)
            for var in self.variables:
                weight = self.variable_dimensions[int(
                    row["turn3"]["appraisals"][var])]
                self.true[var].append(weight)
                classification = self.__classify(
                    self.ngrams[var], parsed_message, tokenized_turn3, u_priors[var], var, False)
                self.pred[var].append(classification)

        self.calculate_scores()

    def _classify(self, training_dict, content, tokenized_content, priors, curr_var, raw=True):
        """
        Classifies each message according to the trained model

        Parameters:
        training_dict (Object): trained model
        content (String): message to be tested
        priors (Object): priors

        Returns:
        String: classification according to the trained model
        """

        low = [math.log(priors["low"]), "low"]
        med = [math.log(priors["med"]), "med"]
        high = [math.log(priors["high"]), "high"]

        pos = parts_of_speech(tokenized_content)
        for p in pos:
            tense = determine_tense(p)
            pronoun = determine_pronoun(p)

            if tense in self.tense[curr_var]:
                low[0] += float(math.log(self.tense[curr_var][tense]["low"]))
                med[0] += float(math.log(self.tense[curr_var][tense]["med"]))
                high[0] += float(math.log(self.tense[curr_var][tense]["high"]))

            if tense in self.pronouns[curr_var]:
                low[0] += float(math.log(self.pronouns[curr_var]
                                         [pronoun]["low"]))
                med[0] += float(math.log(self.pronouns[curr_var]
                                         [pronoun]["med"]))
                high[0] += float(math.log(self.pronouns[curr_var]
                                          [pronoun]["high"]))

        for word in content:
            if word in training_dict:
                low[0] += float(math.log(training_dict[word]["low"]))
                med[0] += float(math.log(training_dict[word]["med"]))
                high[0] += float(math.log(training_dict[word]["high"]))

        if raw:
            return list(map(lambda x: x[0], [low, med, high]))

        return max([low, med, high], key=lambda item: item[0])[1]

    def calculate_scores(self):
        """
        Calculates the micro and macro f scores for each variable

        Parameters:
        None

        Returns:
        None
        """

        for var in self.variables:
            self.pred[var] = np.asarray(self.pred[var])
            self.true[var] = np.asarray(self.true[var])

            tp = np.sum(np.logical_or(np.logical_or(np.logical_and(self.pred[var] == "low", self.true[var] == "low"), np.logical_and(
                self.pred[var] == "med", self.true[var] == "med")), np.logical_and(self.pred[var] == "high", self.true[var] == "high")))
            tp_fp = len(self.pred[var])
            tp_fn = len(self.true[var])

            pi = tp / tp_fp
            ro = tp / tp_fn

            try:
                self.micro_fscores[var] = 2 * pi * ro / (pi + ro)
            except ZeroDivisionError:
                self.micro_fscores[var] = 0.0

            temp_macro = 0
            for c in ["high", "med", "low"]:
                tp_c = np.sum(np.logical_and(
                    self.pred[var] == c, self.true[var] == c))
                tp_fp_c = len([x for x in self.pred[var] if x != c])
                tp_fn_c = len([x for x in self.true[var] if x == c])

                try:
                    pi_c = tp_c / tp_fp_c
                except (ZeroDivisionError, FloatingPointError):
                    pi_c = 0.0

                try:
                    ro_c = tp_c / tp_fn_c
                except (ZeroDivisionError, FloatingPointError):
                    ro_c = 0.0

                try:
                    temp_macro += 2 * pi_c * ro_c / (pi_c + ro_c)
                except (ZeroDivisionError, FloatingPointError):
                    temp_macro += 0.0

            self.macro_fscores[var] = temp_macro / 3

    def confusion_matrix(self, normalized=False):
        """
        Computes the confusion matrices for each of the variables
        """

        for var in self.variables:
            cn_matrix = confusion_matrix(self.true[var], self.pred[var])
            plot_confusion_matrix(
                cn_matrix, ["low", "med", "high"], var, normalized)
