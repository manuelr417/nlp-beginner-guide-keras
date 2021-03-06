import os
import numpy as np
import pandas as pd
import data_helpers
import pickle
from data_helpers import TrainValTensorBoard
from keras.callbacks import EarlyStopping
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from keras.layers import Input, Embedding, Activation, Flatten, Dense, Concatenate
from keras.layers import Conv1D, MaxPooling1D, Dropout, LSTM
from keras.models import Model
from keras.callbacks import CSVLogger
from data_helpers import BPE


# read data from saved file
dataset = np.load('../data/twitter/preprocessed_dataset.npz')

x_train = dataset['x_train'][:25000]
y_train = dataset['y_train'][:25000]
x_test = dataset['x_test'][:25000]
y_test = dataset['y_test'][:25000]

print('Training data size is: ', x_train.shape)
print('Validation data size is: ', x_test.shape)


# Load vocab
bpe = BPE("./pre-trained-model/en.wiki.bpe.op25000.vocab")
# Build vocab, {token: index}
vocab = {}
for i, token in enumerate(bpe.words):
    vocab[token] = i + 1

# Embedding Initialization
from gensim.models import KeyedVectors
model = KeyedVectors.load_word2vec_format("./pre-trained-model/en.wiki.bpe.op25000.d50.w2v.bin", binary=True)

from keras.layers import Embedding

sequence_length = 364
embedding_dim = 50
embedding_weights = np.zeros((len(vocab) + 1, embedding_dim)) # (25001, 50)


for subword, i in vocab.items():
    if subword in model.vocab:
        embedding_vector = model[subword]
        if embedding_vector is not None:
            embedding_weights[i] = embedding_vector
    else:
        continue

embedding_layer = Embedding(len(vocab)+1,
                            embedding_dim,
                            weights=[embedding_weights],
                            input_length=sequence_length,
                            mask_zero=True)

#===================CNN Model===================
# Model Hyperparameters
embedding_dim = 50
dropout_prob = 0.5
hidden_dims = 50
batch_size = 32
num_epochs = 10
sequence_length = 364


# Create model
# Input
inputs = Input(shape=(sequence_length,))
# Embedding
embedded_sequence = embedding_layer(inputs)
# x = LSTM(128, dropout=0.2, recurrent_dropout=0.2,
#         return_sequences=True, activation='relu')(embedded_sequence)
# x = LSTM(128, dropout=0.2, recurrent_dropout=0.2,
#         return_sequences=False, activation='relu')(x)
# x = Dense(128, activation='relu')(x)
# x = Dense(32, activation='relu')(x)
# prediction = Dense(2, activation='sigmoid')(x)
x = LSTM(128, return_sequences=True, activation='relu')(embedded_sequence)
x = LSTM(128, return_sequences=False, activation='relu')(x)
x = Dropout(dropout_prob)(x)
x = Dense(128, activation='relu')(x)
x = Dropout(dropout_prob)(x)
x = Dense(32, activation='relu')(x)
prediction = Dense(2, activation='sigmoid')(x)


model = Model(inputs=inputs, outputs=prediction)
model.compile(optimizer='adam',
              loss='binary_crossentropy',
              metrics=['accuracy'])

print(model.summary())


# Train model with Early Stopping
earlystopper = EarlyStopping(monitor='val_loss', patience=3, verbose=1)
csv_logger = CSVLogger('log.csv', append=False, separator=';')

history = model.fit(x_train, y_train, batch_size=batch_size, epochs=num_epochs, callbacks=[earlystopper, csv_logger],
          validation_split=0.1, shuffle=True, verbose=1)

# Evaluate
score = model.evaluate(x_test, y_test)
print('test_loss, test_acc: ', score)

# Write result to txt
result = 'test_loss, test_acc: {0}'.format(score)
f = open('result.txt', 'w')
f.write(result)
f.close()
