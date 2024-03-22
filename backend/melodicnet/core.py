"""This module provides a high level API for MelodicNet. It handles loading data, training the model, and predicting.

Usage:

```
# Load data and train
driver = MelodicNet()
driver.load_data("path/to/data/directory/*.mid")
driver.create_model()
driver.train_model_weights()

# Save configuration files for future use
print(driver.generate_config_files())

# Predict
output_midis = driver.predict("path/to/input/midi.mid")

```

"""

import json
import logging
import os
import pickle
from typing import Optional, Tuple, Union

import numpy as np
from keras.callbacks import EarlyStopping, ModelCheckpoint
from music21.stream import Stream

from .dataparser import DataParser
from .encoding import SingleEvents
from .globals import (
    DEFAULT_WEIGHT_OUTPATH,
    FLAT_TO_SHARP,
    INPUT_SEQUENCE_LENGTH,
    LONGEST_DURATION,
    LONGEST_OFFSET,
    PITCH_TO_INT,
)
from .models import RNN
from .utils.midi import MIDIUtils
from .utils.misc import format_dict, make_timestamped_dir

DEFAULT_ENCODER_SETTINGS = {
    "same_end_times": 0,
    "allow_overlap": 1,
    "preserve_offsets": 1,
    "preserve_durations": 1,
    "durations_sep_dim": 1,
    "relative_offsets": 1,
    "round_duration": 0.5,
    "sequence_length": INPUT_SEQUENCE_LENGTH,
}

DEFAULT_MODEL_SETTINGS = {}


class MelodicNet:
    def __init__(
        self,
        log_level="INFO",
        config_path: Optional[str] = None,
        encoder_settings: dict = {},
        model_settings: dict = {},
    ):
        """MelodicNet Core Class. Handles loading data, creating model, training model, and predicting.

        Args:
            log_level: Log level. Defaults to "INFO".
            config_path: Directory containing necessary configuration files. Defaults to None.
            encoder_settings: Fields to override default encoder settings. Defaults to {}.
            model_settings: Fields to override default model settings. Defaults to {}.
        """
        self.logger = logging.getLogger("melodicnet")
        self.logger.setLevel(log_level)
        self._config_path = config_path

        if config_path:
            if os.path.exists(os.path.join(config_path, "encoder_settings.json")):
                with open(os.path.join(config_path, "encoder_settings.json"), "r") as f:
                    encoder_settings = {**json.load(f), **encoder_settings}

            if os.path.exists(os.path.join(config_path, "model_settings.json")):
                with open(os.path.join(config_path, "model_settings.json"), "r") as f:
                    model_settings = {**json.load(f), **model_settings}

        self._model_cls = RNN
        self._encoder_cls = SingleEvents
        self._model_settings = {**DEFAULT_MODEL_SETTINGS, **model_settings}
        self._encoder_settings = {**DEFAULT_ENCODER_SETTINGS, **encoder_settings}

        self.logger.debug("****** MelodicNet ******")
        self.logger.debug(f"Using encoder: {self._encoder_cls.__name__}")
        self.logger.debug(f"Encoder settings: {format_dict(self._encoder_settings)}")
        self.logger.debug(f"Using model: {self._model_cls.__name__}")
        self.logger.debug(f"Model settings: {format_dict(self._model_settings)}")
        self.logger.debug("************************")

    def load_data(
        self,
        midi_path: str = "data/all_midi/*.mid",
        refresh_encodings: bool = False,
        refresh_cleaned_midis: bool = False,
        n_midis: int = 20,
        partition: Optional[str] = None,
    ):
        """Load MIDI data into memory for training. This method initializes the `DataParser` class which does the following:
         - Reads `n_midis` MIDI files from `midi_path` (cached).
         - Filters out MIDIs according to the `partition`, if provided.
         - Cleans the MIDIs (cached).
         - Encodes the MIDIs (cached).

        Args:
            midi_path: Glob path containing the midi files. Defaults to "data/all_midi/*.mid".
            refresh_encodings: If `True`, recomputes encodings instead of using cached versions. Defaults to False.
            refresh_cleaned_midis: If `True`, recomputes cleaned MIDIs instead of using cached versions. Defaults to False.
            n_midis: Number of MIDIs to be loaded. Defaults to 20.
            partition: Key type to filter the loaded MIDIs by (`major` or `minor`). Defaults to None.
        """
        self.encoder = self._encoder_cls(**self._encoder_settings)
        self.dp = DataParser(midi_path, self.encoder, refresh_encodings, refresh_cleaned_midis, n_midis, partition)

    def load_mappings(self, mapping_path: Optional[str] = None, prefix: Optional[str] = None):
        """Load encode/decode mappings into the encoder. Initializes the encoder if not already initialized.

        Args:
            mapping_path: If provided, overrides the default config path as the location to load the mapping files from. Defaults to None.
            prefix: Partition key if key type partitioning is being used. Defaults to None.
        """
        self.logger.debug("Loading mappings....")
        if not hasattr(self, "encoder"):
            self.encoder = self._encoder_cls(**self._encoder_settings)

        e_filename = "encode_map.pkl" if not prefix else f"{prefix}_encode_map.pkl"
        d_filename = "decode_map.pkl" if not prefix else f"{prefix}_decode_map.pkl"

        if not mapping_path:
            assert self._config_path, "No config path specified"
            mapping_path = self._config_path

        encode_map_path = os.path.join(mapping_path, e_filename)
        decode_map_path = os.path.join(mapping_path, d_filename)
        assert os.path.exists(encode_map_path), f"No {e_filename} found in mapping path"
        assert os.path.exists(decode_map_path), f"No {d_filename} found in mapping path"

        with open(encode_map_path, "rb") as f:
            self.encoder.encode_map = pickle.load(f)

        with open(decode_map_path, "rb") as f:
            self.encoder.decode_map = pickle.load(f)

        assert len(self.encoder.encode_map) == len(
            self.encoder.decode_map
        ), "Encode and decode maps are not the same length"
        self.encoder.note_dimension = len(self.encoder.encode_map)
        self.logger.debug("Loading mappings....Done")

    def create_model(self):
        """Create model that is compatible with encoder mappings.

        Raises:
            AttributeError: If `encoder.note_dimension` is not set.
        """
        self.logger.debug("Creating model....")
        if not hasattr(self.encoder, "note_dimension"):
            raise AttributeError("No note dimension found. Please load data or mappings first.")
        input_shape = (None, self.encoder.sequence_length, self.encoder.input_shape)
        self.model = self._model_cls(input_shape, self.encoder.note_dimension, **self._model_settings)
        self.logger.debug("Creating model....Done")

    def load_model_weights(self, model_weights_path: Optional[str] = None, prefix: Optional[str] = None):
        """Load model weights for pre-trained model prediction. Initializes the model if not already initialized.

        Args:
            model_weights_path: If provided, overrides the default config path as the location to load the weight files from. Defaults to None.
            prefix: Partition key if key type partitioning is being used. Defaults to None.
        """
        self.logger.debug("Loading model weights....")
        if not hasattr(self, "model"):
            self.logger.warning("No model found. Creating model...")
            self.create_model()

        filename = "trained_weights.hdf5" if not prefix else f"{prefix}_trained_weights.hdf5"

        if not model_weights_path:
            assert self._config_path, "No config path specified"
            model_weights_path = os.path.join(self._config_path, filename)

        assert os.path.exists(model_weights_path), "Weights file not found"

        self.model.load_weights(model_weights_path)
        self.logger.debug("Loading model weights....Done")

    def train_model_weights(
        self,
        epochs: int = 200,
        batch_size: int = 64,
        save_weights: bool = True,
        early_stopping: bool = True,
        n_train: Optional[int] = None,
        **model_fit_kwargs,
    ):
        """Train model weights on loaded data.

        Args:
            epochs: Number of epochs to train for. Defaults to 200.
            batch_size: Size of one training batch. Each batch has shape `(batch_size, sequence_length, note_size)`. Defaults to 64.
            save_weights: If `True`, saves model weights after each Epoch which decreased loss. Defaults to True.
            early_stopping: If `True`, applies early stopping. Defaults to True.
            n_train: Number of loaded MIDIs to use for training. Defaults to all.
        """
        callbacks_list = []
        if save_weights:
            saved_weight_dir = os.path.join(
                make_timestamped_dir(DEFAULT_WEIGHT_OUTPATH), "weights-improvement-{epoch:02d}-{loss:.4f}.hdf5"
            )
            callbacks_list.append(
                ModelCheckpoint(saved_weight_dir, monitor="loss", verbose=0, save_best_only=True, mode="min")
            )
        if early_stopping:
            callbacks_list.append(
                EarlyStopping(
                    monitor="loss", min_delta=0, patience=17, verbose=0, mode="auto", restore_best_weights=True
                )
            )

        input_sequences = []
        if isinstance(self.model.output_shape, dict):
            sequence_outputs = {"pitch": [], "duration": [], "offset": []}
        else:
            sequence_outputs = []

        for encoded_midi in self.dp.midis_encoded[:n_train]:
            inputs, outputs = self.encoder.create_sequences(encoded_midi)
            input_sequences.append(inputs)
            if isinstance(self.model.output_shape, dict):
                for key in sequence_outputs:
                    sequence_outputs[key].append(outputs[key])
            else:
                sequence_outputs.append(outputs)

        inputs = np.concatenate(input_sequences) / [self.encoder.note_dimension, LONGEST_DURATION, LONGEST_OFFSET]

        if isinstance(self.model.output_shape, dict):
            outputs = {key: np.concatenate(sequence_outputs[key]) for key in sequence_outputs}
        else:
            outputs = np.concatenate(sequence_outputs)

        self.model.fit(
            inputs, outputs, epochs=epochs, batch_size=batch_size, callbacks=callbacks_list, **model_fit_kwargs
        )

    def generate_config_files(
        self, root_path: str = "configs", identifier: Optional[str] = None, prefix: Optional[str] = None
    ) -> str:
        """Generates configuration files for the encoder, model, and encoding mappings. Returns the path to the directory where the files were saved.

        Args:
            root_path: Directory where files should be saved. Defaults to "configs".
            identifier: Optional identifier for this configuration. Defaults to None.
            prefix: Optional partition key if key type partitioning is being used. Defaults to None.
        """
        if not hasattr(self, "encoder"):
            raise AttributeError("No encoder found. Please load data or mappings first.")
        if not hasattr(self, "model"):
            raise AttributeError("No model found. Please create model first.")

        model_name = self._model_cls.__name__
        encoder_name = self._encoder_cls.__name__
        seq_length = self.encoder.sequence_length
        config_path = os.path.join(
            root_path, model_name, encoder_name, f"seq_len_{seq_length}", *([identifier] if identifier else [])
        )

        os.makedirs(config_path, exist_ok=True)
        with open(os.path.join(config_path, "encoder_settings.json"), "w") as f:
            json.dump(self._encoder_settings, f, indent=4)

        with open(os.path.join(config_path, "model_settings.json"), "w") as f:
            json.dump(self._model_settings, f, indent=4)

        with open(os.path.join(config_path, f"{prefix+'_' if prefix else ''}encode_map.pkl"), "wb") as f:
            pickle.dump(self.encoder.encode_map, f)

        with open(os.path.join(config_path, f"{prefix+'_' if prefix else ''}decode_map.pkl"), "wb") as f:
            pickle.dump(self.encoder.decode_map, f)

        self.model.save_weights(os.path.join(config_path, f"{prefix+'_' if prefix else ''}trained_weights.hdf5"))

        return config_path

    def predict(
        self,
        midi: Union[str, Stream],
        output_length: int = 32,
        temperature: float = 0.1,
        n_outputs: int = 1,
        octave_range: Tuple[int, int] = (3, 7),
        key_signature: Optional[str] = None,
        random_seed: Optional[str] = None,
        **model_predict_kwargs,
    ):
        """Given a MIDI file and parameters, generate new MIDI(s) using the loaded model. This function wraps the `predict_midi` method of the model.

        Args:
            midi: Either the path to a .mid file or a MIDI Object.
            output_length: Output MIDI length in bars. Defaults to 32.
            temperature: Controls the shape of the output probability distribution. Set higher for more random results. Defaults to 0.1.
            n_outputs: Number of output MIDIs to generate. Defaults to 1.
            octave_range: Acceptable octave range for notes to be placed in. Defaults to (3, 7).
            key_signature: Desired key signature of the output melody. Defaults to None.
            random_seed: If provided, the output will be deterministic with the seed. Defaults to None.

        Returns:
            List of output MIDI objects
        """
        if isinstance(midi, Stream):
            input_midi = self.encoder.preprocess(midi)
        else:
            input_midi = self.encoder.preprocess(MIDIUtils.midi_from_file(midi))

        outputs = []
        for i in range(n_outputs):
            model_output = self.model.predict_midi(
                self.encoder,
                input_midi,
                output_length=output_length,
                temperature=temperature,
                random_seed=random_seed * (i + 1) if random_seed else None,
                smallest_step=0.5,
                **model_predict_kwargs,
            )

            if key_signature is None:
                # Use key signature of input midi
                model_output = model_output.transpose(-input_midi.transpose_by).transpose(0)
            else:
                transpose_by = (
                    PITCH_TO_INT[key_signature]
                    if key_signature in PITCH_TO_INT
                    else PITCH_TO_INT[FLAT_TO_SHARP[key_signature]]
                )
                model_output = model_output.transpose(transpose_by).transpose(0)

            model_output = MIDIUtils.trim_midi_octave_range(model_output, *octave_range)

            # Transpose octave range if the generated MIDI max octave differs from the input MIDI
            # octave_diff = MIDIUtils.highest_octave(model_output) - MIDIUtils.highest_octave(input_midi)
            # if octave_diff > 0:
            #     model_output = model_output.transpose(-12)

            outputs.append(model_output)

        return outputs
