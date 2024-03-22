"""This module provides an API to read, preprocess, and encode MIDI files.

The `DataParser` class connects to a directory which should contain subdirectories with MIDI files. It reads the MIDI files into memory
and wraps them using an `Encoding` object. Some encoding types are lossy, therefore a `preprocess` method is provided to clean the MIDI files
such that any lossy encoding is eliminated. Each operation is cached to disk to speed up future runs.

Usage:
Simply initializing the `DataParser` object will perform the read, clean, and encode operations.
```
dataparser = DataParser("data/*/*.mid", encoder=SingleEvents())

# Access the raw file paths
dataparser.raw_files

# Access the raw MIDI files (before any cleaning occurs)
dataparser.raw_midis

# Access the cleaned MIDI files
dataparser.midis_cleaned

# Access the encoded MIDI files
dataparser.midis_encoded

# Access the encoder object
dataparser.encoder
```
"""

import glob
import logging
import os
from typing import List, Optional

import numpy as np
from music21.stream import Stream

from .encoding import Encoding, SingleEvents
from .globals import BLACKLISTED_MIDIS
from .utils.cache import cached
from .utils.midi import MIDIUtils

logger = logging.getLogger(__name__)


class DataParser:
    utils = MIDIUtils

    def __init__(
        self,
        midi_path: str = "data/*/*.mid",
        encoder: Encoding = SingleEvents(),
        refresh_encodings: bool = False,
        refresh_cleaned_midis: bool = False,
        n_midis: int = None,
        partition: Optional[str] = None,
    ):
        """Create a DataParser object. The DataParser provides functionality involving input and output data from the MelodicNet model.

        Args:
            midi_path: Path containing the source MIDI files. Defaults to "data/*/*.mid".
            encoder: Encoder object to use for encoding/decoding MIDIs. Defaults to ManyHotChords().
            refresh_encodings: If `True`, recomputes encodings instead of using cached versions. Defaults to False.
            refresh_cleaned_midis: If `True`, recomputes cleaned MIDIs instead of using cached versions. Defaults to False.
            n_midis: Number of MIDIs to read and process from the source directory. Defaults to None.
            partition: Key type to filter the loaded MIDIs by (`major` or `minor`). Defaults to None. Defaults to None.
        """
        logger.debug("Initializing DataParser...")
        logger.debug(f"Using encoder: {type(encoder)}")
        encoder_settings = {k: v for k, v in encoder.__dict__.items() if not k.startswith("_")}
        logger.debug(f"Encoder settings: {encoder_settings}")
        logger.debug(f"n_midis: {n_midis}")
        self.encoder = encoder
        self.n_midis = n_midis
        self.raw_files = glob.glob(midi_path)[:n_midis]
        self.partition = partition

        for i, file in enumerate(self.raw_files):
            if os.path.basename(file) in BLACKLISTED_MIDIS:
                logger.warn(f"Removing blacklisted file: {file}")
                self.raw_files.pop(i)

        self.raw_midis = self.all_midis_raw()

        if partition:
            assert partition in ("major", "minor")
            partitioned_raw_midis = []
            for midi in self.raw_midis:
                if midi.analyze("key").type == partition:
                    partitioned_raw_midis.append(midi)

            self.raw_midis = partitioned_raw_midis

        self.midis_cleaned: List[Stream] = self.all_midis_cleaned(refresh=refresh_cleaned_midis)
        if self.encoder.requires_mappings:
            logger.debug("Creating mappings... ")
            self.encoder.create_mappings(self.raw_midis)
            logger.debug("Creating mappings...Done ")
        self.midis_encoded = self.all_midis_encoded(refresh=refresh_encodings)

        encoded_shape = ("MIDI_LENGTH", *self.midis_encoded[0].shape[1:])
        sequence_shape = ("N_SEQUENCES", *self.encoder.create_sequences(self.midis_encoded[0])[0].shape[1:])
        logger.debug(f"Single encoded MIDI shape: {encoded_shape}")
        logger.debug(f"Single encoded sequence shape: {sequence_shape}")

        logger.debug("Initializing DataParser...done\n")

    def encode_single_midi(self, midi: Stream):
        """Apply encoding to a single MIDI"""
        return self.encoder.encode(midi)

    def clean_single_midi(self, midi: Stream):
        """Apply quantization and chord trimming to a single MIDI"""
        return self.encoder.preprocess(midi)

    @cached("cache/raw_midis", disabled=False, refresh=False, instance_identifiers=["raw_files"], log_level="DEBUG")
    def all_midis_raw(self, **cache_kwargs) -> List[Stream]:
        """Loads and returns all MIDI files from `self.raw_files`"""
        logger.debug("Reading raw files...")
        raw_midis = [MIDIUtils.midi_from_file(file) for file in self.raw_files]
        logger.debug("Reading raw files...done")
        return raw_midis

    @cached(
        "cache/encoded_midis",
        disabled=False,
        refresh=False,
        instance_identifiers=["raw_files", "encoder", "partition"],
        log_level="DEBUG",
    )
    def all_midis_encoded(self, **cache_kwargs) -> List[np.ndarray]:
        """Encodes and returns all midis from `self.raw_midis`"""
        midis = self.raw_midis
        n_midis = len(midis)
        logger.debug(f"Encoding MIDIs ({n_midis} total)...")
        encoded = []
        for idx, midi in enumerate(midis):
            encoded.append(self.encode_single_midi(midi))
            if idx % ((n_midis // 10) or n_midis) == 0:
                logger.debug(f"{idx} / {n_midis}")
        logger.debug("Encoding MIDIs...done")
        return encoded

    @cached(
        "cache/cleaned_midis",
        disabled=False,
        refresh=False,
        instance_identifiers=["raw_files", "encoder", "partition"],
        log_level="DEBUG",
    )
    def all_midis_cleaned(self, **cache_kwargs) -> List[Stream]:
        """Applies quantization and chord trimming and returns all midis from `self.raw_midis`"""
        midis = self.raw_midis
        n_midis = len(midis)
        logger.debug(f"Cleaning MIDIs ({n_midis} total)...")
        cleaned = []
        for idx, midi in enumerate(midis):
            cleaned.append(self.clean_single_midi(midi))
            if idx % ((n_midis // 10) or n_midis) == 0:
                logger.debug(f"{idx} / {n_midis}")
        logger.debug("Cleaning MIDIs...done")
        return cleaned
