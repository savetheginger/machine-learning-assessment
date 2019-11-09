#!/usr/bin/env python
import re
import random
import math
import collections
import itertools

import io_functions

PRINT_ERRORS = 0


# calculates p(W|Positive), p(W|Negative) and p(W) for all words in training data
def trainBayes(sentencesTrain, pWordPos, pWordNeg, pWord):
    posFeatures = [] # [] initialises a list [array]
    negFeatures = [] 
    freqPositive = {} # {} initialises a dictionary [hash function]
    freqNegative = {}
    dictionary = {}
    posWordsTot = 0
    negWordsTot = 0
    allWordsTot = 0

    # iterate through each sentence/sentiment pair in the training data
    for sentence, sentiment in sentencesTrain.items():
        wordList = re.findall(r"[\w']+", sentence)

        # TODO:
        # Populate bigramList (initialised below) by concatenating adjacent words in the sentence.
        # You might want to seperate the words by _ for readability, so bigrams such as:
        # You_might, might_want, want_to, to_seperate.... 

        bigramList = wordList.copy()  # initialise bigramList
        for x in range(len(wordList)-1):
           bigramList.append(wordList[x]+"_" + wordList[x+1])
 
        # -------------Finish populating bigramList ------------------#
        
        # TODO: 
        #  when you have populated bigramList, 
        #  uncomment out the line below and , 
        #  and comment out the unigram line to make use of bigramList rather than wordList
        
        for word in bigramList:  # calculate over bigrams
        # for word in wordList:  # calculate over unigrams
            allWordsTot += 1    # keeps count of total words in dataset
            if not (word in dictionary):
                dictionary[word] = 1
            if sentiment == "positive":
                posWordsTot += 1  # keeps count of total words in positive class

                # keep count of each word in positive context
                if not (word in freqPositive):
                    freqPositive[word] = 1
                else:
                    freqPositive[word] += 1    
            else:
                negWordsTot += 1  # keeps count of total words in negative class
                
                #  keep count of each word in positive context
                if not (word in freqNegative):
                    freqNegative[word] = 1
                else:
                    freqNegative[word] += 1

    for word in dictionary:
        # do some smoothing so that minimum count of a word is 1
        if not (word in freqNegative):
            freqNegative[word] = 1
        if not (word in freqPositive):
            freqPositive[word] = 1

        # Calculate p(word|positive)
        pWordPos[word] = freqPositive[word] / float(posWordsTot)

        # Calculate p(word|negative) 
        pWordNeg[word] = freqNegative[word] / float(negWordsTot)

        # Calculate p(word)
        pWord[word] = (freqPositive[word] + freqNegative[word]) / float(allWordsTot) 

# ---------------------------End Training ----------------------------------


# implement naive bayes algorithm
# INPUTS:
#  sentencesTest is a dictionary with sentences associated with sentiment
#  dataName is a string (used only for printing output)
#  pWordPos is dictionary storing p(word|positive) for each word
#     i.e., pWordPos["apple"] will return a real value for p("apple"|positive)
#  pWordNeg is dictionary storing p(word|negative) for each word
#  pWord is dictionary storing p(word)
#  pPos is a real number containing the fraction of positive reviews in the dataset
def testBayes(sentencesTest, dataName, pWordPos, pWordNeg, pWord,pPos):
    pNeg = 1-pPos

    # These variables will store results (you do not need them)
    total = 0
    correct = 0
    totalpos = 0
    totalpospred = 0
    totalneg = 0
    totalnegpred = 0
    correctpos = 0
    correctneg = 0

    # for each sentence, sentiment pair in the dataset
    for sentence, sentiment in sentencesTest.items():
        wordList = re.findall(r"[\w']+", sentence)  #collect all words

        # TODO: Exactly what you did in the training function:
        # Populate bigramList by concatenating adjacent words in wordList.

        bigramList = wordList.copy() #initialise bigramList
        for x in range(len(wordList)-1):
           bigramList.append(wordList[x]+"_" + wordList[x+1])


#------------------finished populating bigramList--------------
        pPosW = pPos
        pNegW = pNeg

        for word in bigramList:  # calculate over bigrams
        # for word in wordList:  # calculate over unigrams
            if word in pWord:
                if pWord[word] > 0.00000001:
                    pPosW *= pWordPos[word]
                    pNegW *= pWordNeg[word]

        prob = 0
        if pPosW+pNegW > 0:
            prob = pPosW/float(pPosW+pNegW)


        total += 1
        if sentiment == "positive":
            totalpos += 1
            if prob > 0.5:
                correct += 1
                correctpos += 1
                totalpospred += 1
            else:
                correct += 0
                totalnegpred += 1
                if PRINT_ERRORS:
                    print("ERROR (pos classed as neg %0.2f):" %prob + sentence)
        else:
            totalneg += 1
            if prob <= 0.5:
                correct += 1
                correctneg += 1
                totalnegpred += 1
            else:
                correct += 0
                totalpospred += 1
                if PRINT_ERRORS:
                    print("ERROR (neg classed as pos %0.2f):" %prob + sentence)
 
    acc = correct/float(total)
    print(dataName + " Accuracy (All)=%0.2f" % acc + " (%d" % correct + "/%d" % total + ")\n")

    precision_pos=correctpos/float(totalpospred)
    recall_pos=correctpos/float(totalpos)
    precision_neg=correctneg/float(totalnegpred)
    recall_neg=correctneg/float(totalneg)
    f_pos = 2*precision_pos*recall_pos/(precision_pos+recall_pos)
    f_neg = 2*precision_neg*recall_neg/(precision_neg+recall_neg)

    print(dataName + " Precision (Pos)=%0.2f" % precision_pos + " (%d" % correctpos + "/%d" % totalpospred + ")")
    print(dataName + " Recall (Pos)=%0.2f" % recall_pos + " (%d" % correctpos + "/%d" % totalpos + ")")
    print(dataName + " F-measure (Pos)=%0.2f" % f_pos)

    print(dataName + " Precision (Neg)=%0.2f" % precision_neg + " (%d" % correctneg + "/%d" % totalnegpred + ")")
    print(dataName + " Recall (Neg)=%0.2f" % recall_neg + " (%d" % correctneg + "/%d" % totalneg + ")")
    print(dataName + " F-measure (Neg)=%0.2f" % f_neg + "\n")


# This is a simple classifier that uses a sentiment dictionary to classify 
# a sentence. For each word in the sentence, if the word is in the positive 
# dictionary, it adds 1, if it is in the negative dictionary, it subtracts 1. 
# If the final score is above a threshold, it classifies as "Positive", 
# otherwise as "Negative"
def testDictionary(sentencesTest, dataName, sentimentDictionary, threshold):
    total = 0
    correct = 0
    totalpos = 0
    totalneg = 0
    totalpospred = 0
    totalnegpred = 0
    correctpos = 0
    correctneg = 0
    for sentence, sentiment in sentencesTest.items():
        Words = re.findall(r"[\w']+", sentence)
        score = 0
        for word in Words:
            if word in sentimentDictionary:
               score += sentimentDictionary[word]
 
        total += 1
        if sentiment == "positive":
            totalpos += 1
            if score >= threshold:
                correct += 1
                correctpos += 1
                totalpospred += 1
            else:
                correct += 0
                totalnegpred += 1
        else:
            totalneg += 1
            if score < threshold:
                correct += 1
                correctneg += 1
                totalnegpred += 1
            else:
                correct += 0
                totalpospred += 1
 
    acc = correct/float(total)
    print(dataName + " Accuracy (All)=%0.2f" % acc + " (%d" % correct + "/%d" % total + ")\n")
    precision_pos = correctpos/float(totalpospred)
    recall_pos = correctpos/float(totalpos)
    precision_neg = correctneg/float(totalnegpred)
    recall_neg = correctneg/float(totalneg)
    f_pos = 2*precision_pos*recall_pos/(precision_pos+recall_pos)
    f_neg = 2*precision_neg*recall_neg/(precision_neg+recall_neg)

    print(dataName + " Precision (Pos)=%0.2f" % precision_pos + " (%d" % correctpos + "/%d" % totalpospred + ")")
    print(dataName + " Recall (Pos)=%0.2f" % recall_pos + " (%d" % correctpos + "/%d" % totalpos + ")")
    print(dataName + " F-measure (Pos)=%0.2f" % f_pos)

    print(dataName + " Precision (Neg)=%0.2f" % precision_neg + " (%d" % correctneg + "/%d" % totalnegpred + ")")
    print(dataName + " Recall (Neg)=%0.2f" % recall_neg + " (%d" % correctneg + "/%d" % totalneg + ")")
    print(dataName + " F-measure (Neg)=%0.2f" % f_neg + "\n")


# Print out n most useful predictors
def mostUseful(pWordPos, pWordNeg, pWord, n):
    predictPower={}
    for word in pWord:
        if pWordNeg[word] < 0.0000001:
            predictPower[word] = 1000000000
        else:
            predictPower[word] = pWordPos[word] / (pWordPos[word] + pWordNeg[word])
            

    sortedPower = sorted(predictPower, key=predictPower.get)
    head, tail = sortedPower[:n], sortedPower[len(predictPower)-n:]
    print("NEGATIVE:")
    print(head)
    print("\nPOSITIVE:")
    print(tail)


# ---------- Main Script --------------------------

# initialise datasets and dictionaries
sentimentDictionary, sentencesTrain, sentencesTest, sentencesNokia = io_functions.read_files()

pWordPos = {}  # p(W|Positive)
pWordNeg = {}  # p(W|Negative)
pWord = {}     # p(W) 

# build conditional probabilities using training data
trainBayes(sentencesTrain, pWordPos, pWordNeg, pWord)

# run naive bayes classifier on datasets
# print("Naive Bayes")
# testBayes(sentencesTrain,  "Films (Train Data, Naive Bayes)\t", pWordPos, pWordNeg, pWord,0.5)
testBayes(sentencesTest,  "Films  (Test Data, Naive Bayes)\t", pWordPos, pWordNeg, pWord,0.5)
# testBayes(sentencesNokia, "Nokia   (All Data,  Naive Bayes)\t", pWordPos, pWordNeg, pWord,0.7)


# run sentiment dictionary based classifier on datasets
# testDictionary(sentencesTrain,  "Films (Train Data, Rule-Based)\t", sentimentDictionary, -4)
# testDictionary(sentencesTest,  "Films  (Test Data, Rule-Based)\t",  sentimentDictionary, -4)
# testDictionary(sentencesNokia, "Nokia   (All Data, Rule-Based)\t",  sentimentDictionary, -3)


# print most useful words
# mostUseful(pWordPos, pWordNeg, pWord, 50)



