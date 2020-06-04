from argparse import ArgumentParser

import pytorch_lightning as pl

from dataset import PerseusDataset
from model import LSTMCharTagger

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=1)
    parser.add_argument('--learning-rate', type=float, default=1e-3)
    parser.add_argument('--word-embedding-dim', type=int, default=100)
    parser.add_argument('--word-lstm-hidden-dim', type=int, default=500)
    parser.add_argument('--char-embedding-dim', type=int, default=20)
    parser.add_argument('--char-lstm-hidden-dim', type=int, default=200)
    parser.add_argument('--track', action='store_true')

    parser = pl.Trainer.add_argparse_args(parser)
    hparams = parser.parse_args()

    train_data = PerseusDataset("data/perseus-conllu/grc_perseus-ud-train.conllu")
    val_data = PerseusDataset("data/perseus-conllu/grc_perseus-ud-dev.conllu")
    model = LSTMCharTagger(hparams, train_data, val_data)

    pl.seed_everything(1)
    trainer = pl.Trainer.from_argparse_args(
        hparams,
        logger=pl.loggers.WandbLogger(project="nlp_classics", log_model=False) if hparams.track else None,
        deterministic=True
    )
    trainer.fit(model)
