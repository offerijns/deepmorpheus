import pyconll
import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils
import torch.utils.data
import torch.autograd as autograd
from tqdm import tqdm
import pickle, time

from model.lstm_char import LSTMCharTagger
from util import parse_into_list, make_ixs

torch.manual_seed(1)

WORD_EMBEDDING_DIM = 5
CHAR_EMBEDDING_DIM = 6
CHAR_REPR_DIM = 3
HIDDEN_DIM = 6
BATCH_SIZE = 1
NUM_EPOCHS = 20

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def train():
    # Read input
    train_file = pyconll.load_from_file(
        "data/perseus-conllu/grc_perseus-ud-train.conllu"
    )
    val_file = pyconll.load_from_file("data/perseus-conllu/grc_perseus-ud-dev.conllu")

    train = parse_into_list(train_file)
    val = parse_into_list(val_file)

    # Create dicts
    word_to_ix = {"<UNK>": 0}
    char_to_ix = {"<UNK>": 0}
    for words, tags in tqdm(train, desc="Creating word and character indices"):
        for word in words:
            if word not in word_to_ix:
                word_to_ix[word] = len(word_to_ix)

            for char in word:
                if char not in char_to_ix:
                    char_to_ix[char] = len(char_to_ix)

    tag_to_ix = {}
    for sent, tags in tqdm(train, desc="Creating tag index"):
        for tag in tags:
            if tag not in tag_to_ix:
                tag_to_ix[tag] = len(tag_to_ix)

    # Initialize model
    model = LSTMCharTagger(
        WORD_EMBEDDING_DIM,
        CHAR_EMBEDDING_DIM,
        CHAR_REPR_DIM,
        HIDDEN_DIM,
        len(word_to_ix),
        len(char_to_ix),
        len(tag_to_ix),
        BATCH_SIZE,
        device,
    )

    model.to(device)
    loss_function = nn.NLLLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    train_loader = torch.utils.data.DataLoader(
        train, batch_size=BATCH_SIZE, shuffle=True, num_workers=0
    )
    val_loader = torch.utils.data.DataLoader(
        val, batch_size=BATCH_SIZE, shuffle=True, num_workers=0
    )
    train_losses = []

    for epoch in range(NUM_EPOCHS):
        total_loss = 0

        model.train()
        for i, data in tqdm(
            enumerate(train_loader), total=len(train) / BATCH_SIZE, desc="Training..."
        ):
            for i in range(len(data[0])):
                sentence = data[0][i]
                tags = data[1][i]

                word_characters_ixs = {}
                for word in sentence:
                    word_ix = (
                        torch.tensor([word_to_ix[word]]).to(device)
                        if word in word_to_ix
                        else torch.tensor([word_to_ix["<UNK>"]]).to(device)
                    )
                    char_ixs = make_ixs(word, char_to_ix, device)
                    word_characters_ixs[word_ix] = char_ixs

                targets = make_ixs(tags, tag_to_ix, device)

                model.zero_grad()

                model.init_word_hidden()
                tag_scores = model(word_characters_ixs)

                loss = loss_function(tag_scores, targets)
                loss.backward()  # calculate gradients
                optimizer.step()  # update hidden layers based on gradients

                total_loss += loss

        epoch_loss = total_loss / len(train)

        print("Epoch %d, training loss = %.4f" % (epoch + 1, total_loss / len(train)))
        train_losses.append(total_loss / len(train))

        # Evaluate on validation dataset
        model.eval()
        val_loss = 0
        correct = 0
        total = 0

        for i, data in tqdm(
            enumerate(train_loader), total=len(train) / BATCH_SIZE, desc="Evaluating..."
        ):
            model.zero_grad()

            for i in range(len(data[0])):
                sentence = data[0][i]
                tags = data[1][i]

                word_characters_ixs = {}
                for word in sentence:
                    word_ix = (
                        torch.tensor([word_to_ix[word]]).to(device)
                        if word in word_to_ix
                        else torch.tensor([word_to_ix["<UNK>"]]).to(device)
                    )
                    char_ixs = make_ixs(word, char_to_ix, device)
                    word_characters_ixs[word_ix] = char_ixs

                targets = make_ixs(tags, tag_to_ix, device)

                model.zero_grad()

                model.init_word_hidden()
                tag_scores = model(word_characters_ixs)
                loss = loss_function(tag_scores, targets)

                val_loss += loss.item()
                _, predicted = tag_scores.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()

        print(
            "Epoch %d, validation accuracy = %.2f%%"
            % (epoch + 1, 100.0 * correct / total)
        )

        with open("model-%d.pickle" % time.time(), "wb") as f:
            pickle.dump(model, f)


if __name__ == "__main__":
    train()
