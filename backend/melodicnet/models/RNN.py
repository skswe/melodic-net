"""RNN Model for MelodicNet

The network consists of a  2 LSTM layers followed by 3 dense layers for pitch, duration and offset prediction. 
The 3 input features (pitch, duration, offset) are represented as floating point numbers. The network uses 
sparse categorical crossentropy for pitch prediction and mean squared error with positive pressure for 
duration and offset prediction. During prediction, the model's duration and output predictions are rounded 
and scaled in order to generate a pleasant sounding MIDI sequence.

"""

import logging
import os
from functools import partial
from typing import Optional

import numpy as np
import tensorflow as tf
from keras import utils
from keras.layers import LSTM, Dense
from keras.models import Model
from music21.stream import Stream

from ..dataparser import Encoding
from ..globals import LONGEST_DURATION, LONGEST_OFFSET
from ..utils.midi import MIDIUtils

logger = logging.getLogger(__name__)


class RNN(Model):
    def __init__(self, input_shape, note_dimension, **kwargs):
        """Compile the tensorflow model with the given `input_shape` and `note_dimension`.

        Args:
            input_shape: Shape of the input tensors. (None, SEQ_LEN, N_FEATURES)
            note_dimension: Number of unique notes in the dataset.
        """
        logger.debug("Initializing RNN Model...")
        if tf.test.is_built_with_cuda() and not os.environ.get("FLASK_ENV") == "PRODUCTION":
            logger.info("CUDA Support available: using CuDNNLSTM Layers.")
            LSTM_layer = partial(tf.compat.v1.keras.layers.CuDNNLSTM)
        else:
            logger.info("Running in CPU mode")
            LSTM_layer = LSTM

        input = tf.keras.Input(input_shape[1:])
        lstm_1 = LSTM_layer(note_dimension, return_sequences=True)(input)
        lstm_2 = LSTM_layer(note_dimension)(lstm_1)

        outputs = {
            "pitch": Dense(note_dimension, name="pitch")(lstm_2),
            "duration": Dense(1, name="duration", activation="relu")(lstm_2),
            "offset": Dense(1, name="offset", activation="relu")(lstm_2),
        }

        super().__init__(input, outputs)

        loss_fns = {
            "pitch": tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
            "duration": tf.keras.losses.MeanSquaredError(),
            "offset": tf.keras.losses.MeanSquaredError(),
        }

        self.compile(
            loss=loss_fns,
            loss_weights={
                "pitch": 0.1,
                "duration": 1.0,
                "offset": 1.0,
            },
            optimizer="adam",
        )

        self.summary(print_fn=logger.debug)

        self.scaling_factor = [note_dimension, LONGEST_DURATION, LONGEST_OFFSET]

        logger.debug(f"model input_shape: {self.input_shape}")
        logger.debug(f"model output_shape: {self.output_shape}\n")
        logger.debug("Initializing RNN Model...Done")

    def predict_midi(
        self,
        encoder: Encoding,
        midi: Stream,
        output_length: int = 16,
        smallest_step: Optional[float] = 0.5,
        temperature=1.0,
        random_seed: Optional[int] = None,
        **model_predict_kwargs,
    ) -> Stream:
        """Generate a MIDI sequence using the model.

        Args:
            encoder: The encoder object used to encode/decode the MIDI. It should be the same encoder used to train the model.
            midi: The input MIDI to generate the sequence from.
            output_length: Number of bars to generate. Defaults to 32.
            smallest_step: The duration of the smallest step size the model should produce, measured in quarterLength. Defaults to 0.5 (1/8th notes).
            temperature: Temperature of the model's note distribution. A higher temperature results in higher variance in the types of notes produced. Defaults to 2.0.
            random_seed: A seed to make the model's output deterministic. Defaults to None.

        Returns:
            The generated MIDI sequence as a music21 Stream.
        """
        # encoded_midi shape: (MIDI_LENGTH, SINGLE_NOTE_SIZE)
        if random_seed:
            tf.random.set_seed(random_seed)
            np.random.seed(random_seed)

        encoded_midi = encoder.encode(midi)

        model_sequence_length = self.input_shape[1]
        start_position = np.random.randint(0, len(encoded_midi) - model_sequence_length - 1)
        # start_position = 0
        input_sequence = encoded_midi[start_position : start_position + model_sequence_length] / self.scaling_factor

        # Model input expects N_SEQUENCES as the first dimension. Since we only have 1 sequence,
        # just add an empty dimension in axis=0
        input_sequence = np.expand_dims(input_sequence, axis=0)
        output_sequence = []

        # Example: SEQUENCE_LENGTH = 4, initial input_sequence = [A, B, C, D]
        # First iteration: Model generates E, input_sequence = [B, C, D, E]
        # Second Iteration: Model generates F, input_sequence = [C, D, E, F]
        # and so on...
        midi_length = 0
        while midi_length < output_length:
            # Model output shape = (1, SINGLE_NOTE_SIZE).
            single_event = self.predict(input_sequence, verbose=0, **model_predict_kwargs)
            pitch = tf.squeeze(tf.random.categorical(single_event["pitch"] / temperature, num_samples=1))

            # Ensure first note starts at 0
            if midi_length == 0:
                offset = 0
            else:
                offset = single_event["offset"].squeeze()

            duration = single_event["duration"].squeeze()

            actual_event = np.array([[pitch, duration, offset]])
            tweaked_event = np.array([[
                pitch,
                min(max(0.25, round(duration / smallest_step) * smallest_step), 8),
                round(offset / smallest_step) * smallest_step,
            ]])
            # squeeze() removes the empty dimension in axis=0 before adding to the output sequence
            output_sequence.append(tweaked_event.squeeze())
            midi_length = np.array(output_sequence)[:, 2].sum() + duration

            # append single model_output to the end of the midi and drop the first note
            # add empty dimension in axis=0 to match model input shape
            input_sequence = np.append(
                input_sequence, np.expand_dims(actual_event / self.scaling_factor, axis=0), axis=1
            )[:, 1:, :]

        output_sequence = np.array(output_sequence)

        # Validate output quality
        one_hot_notes = utils.to_categorical(output_sequence[:, 0], self.output_shape["pitch"][-1])
        note_concentrations = one_hot_notes.sum(axis=0) / len(output_sequence)
        if (note_concentrations > 0.9).any():
            logger.warning("Note concentrations are too high. This might be a bad prediction.")
            logger.warning(note_concentrations)
        zero_predictions = round((1 - note_concentrations.sum()) * len(output_sequence))
        if zero_predictions > 0:
            logger.warning(
                f"{zero_predictions} time steps contained a zero prediction (no note predicted for that time step). This might be a bad prediction."
            )

        model_output = encoder.decode(output_sequence)

        # Trim notes that go past the output length
        model_output = MIDIUtils.trim_midi_length(model_output, output_length)

        return model_output
