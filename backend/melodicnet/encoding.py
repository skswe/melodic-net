"""This module contains different classes for encoding MIDI data into a format that can be used by the model. 
Many of the encoding classes are experimental, with SingleEvents being the encoding that is used in production.

The SingleEvents encoding works as follows:

1. Requires the entire dataset to be loaded into memory. This is because the encoding is based on the entire dataset.
2. Encode map is created by mapping each unique combination of notes (a chord) into its string representation.
    e.g. [C4, E4, G4] --> "C4_E4_G4"
3. Decode map is created as the inverse of the encode map.
4. MIDI is preprocessed with the following settings:
    - Quantize to nearest sixteenth note
    - Notes are allowed to overlap
    - Notes in the same chord are allowed to have different end times
5. When encoding a MIDI, the pitch, duration, and relative offset are all preserved. Each note is mapped to its string representation
    using the encode_map. If there is no matching key in the map, the note is split into a combination of notes that are in the map.
    e.g. [C4, E4, G4] can be split into [C4 E4] and [G4].
6. Each encoded note is stored as a 1-d array with 3 elements: [pitch, duration, offset]. Pitch is a single integer ranging from 0-len(encode_map).
    Note that a single chord can be split into multiple notes, therefore consecutive notes have relative offset of 0 if they are in the same chord.
    
Example encoded MIDI:

array([[17.  ,  4.  ,  0.  ],
       [10.  ,  0.5 ,  0.  ],
       [ 4.  ,  0.5 ,  0.5 ],
       [ 0.  ,  0.5 ,  0.5 ],
       [19.  ,  0.5 ,  0.5 ],
       [24.  ,  0.5 ,  0.5 ],
       [19.  ,  0.5 ,  0.5 ],
       [15.  ,  0.5 ,  0.5 ]
     ])
     
Looks something like this:

----
-
 -
  -
   -
    - 
     -
      -
"""

import logging
from abc import abstractmethod
from functools import partial
from typing import List, Set, Tuple, Union

import numpy as np
from keras import utils
from music21.chord import Chord
from music21.note import Note
from music21.stream import Stream

from .globals import FLAT_TO_SHARP, INPUT_SEQUENCE_LENGTH, INT_TO_PITCH, NOTE_SIZE, PITCH_TO_INT, PITCHES_PER_OCTAVE
from .utils.midi import MIDIUtils
from .utils.misc import split_key

logger = logging.getLogger(__name__)


class Encoding:
    """Base class for encoding."""

    note_dimension = NOTE_SIZE
    requires_mappings = False

    def __init__(
        self,
        quantize: bool = True,
        same_end_times: bool = False,
        allow_overlap: bool = True,
        preserve_offsets: bool = True,
        preserve_durations: bool = True,
        durations_sep_dim: bool = True,
        relative_offsets: bool = True,
        sequence_length: int = INPUT_SEQUENCE_LENGTH,
        **kwargs,
    ):
        """Create encoding object.

        Args:
            quantize: Quantize note offsets and durations to nearest sixteenth. Defaults to True.
            same_end_times: Force notes with the same start times to end at the same time. Defaults to True.
            allow_overlap: Allow notes with different start times to overlap eachother. Defaults to False.
            preserve_offsets: encode offsets as a seperate dimension for event based encodings. If False,
                notes will be appended with no gaps during decoding phase. Defaults to False.
            preserve_durations: encode durations. If False, all notes will be encoded and decoded as quarter notes.
            durations_sup_dim: If True and `preserve_durations` is True, adds duration as a new dimension.
            relative_offsets: If True, encode offsets relative to the previous note. Defaults to False.
            sequence_length: length of input sequence. Defaults to INPUT_SEQUENCE_LENGTH.
        """
        logger.debug("Initializing encoder...")
        self.quantize = quantize
        self.same_end_times = same_end_times
        self.allow_overlap = allow_overlap
        self.preserve_offsets = preserve_offsets
        self.preserve_durations = preserve_durations
        self.durations_sep_dim = durations_sep_dim
        self.relative_offsets = relative_offsets
        self.sequence_length = sequence_length
        logger.debug("Initializing encoder...Done")

    @staticmethod
    def note_to_int(note: Note) -> int:
        """Convert Music21 Note object to integer"""
        note_pitch = note.pitch.name
        note_pitch = FLAT_TO_SHARP[note_pitch] if "-" in note_pitch else note_pitch
        note_octave = note.octave

        pitch_encoding = PITCH_TO_INT[note_pitch]
        octave_encoding = note_octave * PITCHES_PER_OCTAVE
        return pitch_encoding + octave_encoding

    @staticmethod
    def int_to_note(i: int) -> str:
        """Convert integer to string representation of note"""
        pitch = INT_TO_PITCH[i % PITCHES_PER_OCTAVE]
        octave = str(i // PITCHES_PER_OCTAVE)
        return pitch + octave

    def preprocess(self, midi: Stream) -> Stream:
        """Transform raw MIDI into a format that will be identical to the decoded MIDI.
        i.e. quantizing, trimming chords, aligning key signature, etc."""
        if self.quantize:
            midi = midi.quantize()
        if self.same_end_times:
            midi = MIDIUtils.trim_chords(midi, overlap=self.allow_overlap)

        # standardize flats/sharps
        midi = midi.transpose(0)
        midi = Stream(midi.flat.notes.stream().iter.addFilter(lambda el: el.quarterLength > 0))
        midi = MIDIUtils.normalize_keysig(midi)
        return midi

    def encode(self, midi: Stream) -> np.ndarray:
        """Convert music21 Stream object into encoded MIDI"""
        midi = self.preprocess(midi)
        notes_to_parse = midi.flat.notes

        events = []
        offsets = []
        durations = []
        prev_offset = 0
        for element in notes_to_parse:
            event = self.note_to_event(element)
            if event is None:
                continue
            if self.relative_offsets:
                offset = float(element.offset) - prev_offset
                prev_offset = float(element.offset)
            else:
                offset = float(element.offset)
            if isinstance(event, Tuple):
                events.extend(event)
                offsets.extend(offset for _ in event)
                durations.extend(float(element.quarterLength) for _ in event)
            else:
                events.append(event)
                offsets.append(offset)
                durations.append(float(element.quarterLength))

        encoded_midi = np.array(events)

        if self.preserve_durations:
            if self.durations_sep_dim:
                encoded_midi = np.hstack((encoded_midi, np.array([durations]).T))
            else:
                encoded_midi = encoded_midi * np.array([durations]).T
        if self.preserve_offsets:
            encoded_midi = np.hstack((encoded_midi, np.array([offsets]).T))
        return encoded_midi

    def decode(self, encoded_midi: np.ndarray) -> Stream:
        """Reconstruct MIDI given encoding."""
        midi_out = Stream()
        prev_offset = 0
        for event in encoded_midi:
            if self.preserve_offsets:
                event, offset = np.split(event, [-1])  # Last index is the offset
                if self.relative_offsets:
                    offset = prev_offset + offset
                    prev_offset = offset
                insert_fn = partial(midi_out.insert, offset)
            else:
                insert_fn = midi_out.append

            if self.preserve_durations and self.durations_sep_dim:
                event, duration = np.split(event, [-1])  # Last index is the duration
                duration = duration[0]
            else:
                duration = np.max(event)

            note = self.event_to_note(event)
            if self.preserve_durations:
                note.quarterLength = duration

            insert_fn(note)
        return midi_out.transpose(0)

    def create_sequences(self, encoded_midi: np.ndarray, seq_length: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """Return tuple of (sequences, sequence_outputs) where each sequence is a window from `encoded_midi`
        and each sequence_output is the note following the last note in the sequence.
        """
        seq_length = seq_length or self.sequence_length

        # Loop MIDI if it is shorter than the defined sequence length
        if len(encoded_midi) < seq_length:
            encoded_midi = encoded_midi.repeat(1 + (seq_length // len(encoded_midi)), axis=0)

        # shape = (n_sequences, window_sz)
        sequences = np.lib.stride_tricks.sliding_window_view(encoded_midi, seq_length, axis=0)[:-1].swapaxes(1, 2)
        # shape = (n_sequences,)
        sequence_outputs = encoded_midi[seq_length:]
        return (sequences, sequence_outputs)

    # Abstract methods to be implemented by all child Encoding objects
    @abstractmethod
    def event_to_note(self, event: np.ndarray) -> Union[Note, Chord]:
        pass

    @abstractmethod
    def note_to_event(self, note: Union[Note, Chord]) -> np.ndarray:
        pass


class NonPreservedEncoding(Encoding):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.preserve_durations:
            logger.warning("This encoding does not support preserve_durations=True. Setting to False")
            self.preserve_durations = False

        if self.preserve_offsets:
            logger.warning("This encoding does not support preserve_offsets=True. Setting to False")
            self.preserve_offsets = False


class PreservedEncoding(Encoding):
    """Encoding that preserves the original note durations and offsets as extra columns in the event dimensionality space"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.preserve_durations:
            logger.warning("This encoding does not support preserve_durations=False. Setting to True")
            self.preserve_durations = True

        if not self.preserve_offsets:
            logger.warning("This encoding does not support preserve_offsets=False. Setting to True")
            self.preserve_offsets = True

        if not self.durations_sep_dim:
            logger.warning("This encoding does not support durations_sep_dim=False. Setting to True")
            self.durations_sep_dim = True

    def create_sequences(self, encoded_midi: np.ndarray, seq_length: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """Return tuple of (sequences, sequence_outputs) where each sequence is a window from `encoded_midi`
        and each sequence_output is the note following the last note in the sequence.

        *NOTE* If `self.preserve_offsets` is `True`, this function will not work as expected. A sequence of length n could be n notes playing at the same time.
        """
        sequnces, sequence_outputs = super().create_sequences(encoded_midi, seq_length)
        return sequnces, {label: column for label, column in zip(("pitch", "duration", "offset"), sequence_outputs.T)}


class ManyHotChords(Encoding):
    """Represents MIDI as a sequence of events. An event is one or more notes having the same start time.
    Events are encoded as a numpy array of size `NOTE_SIZE` containing a one in the event at the corresponding
    index. The index is determined using the pitch and octave of the note.

    Example:
        Stream([Note(C#4, duration=2), Chord(C#4, E4, G#4, duration=3)]) --> np.array([[0, 0, ,...2, 0, 0, ,...], [0, 0, ,...3, 0, 0, 3, 0, 0, 3,...]])
    """

    compressed = False
    input_shape = NOTE_SIZE

    def event_to_note(self, event: np.ndarray) -> Union[Note, Chord]:
        indices = np.where(event > 0)[0]
        notes = [self.int_to_note(i) for i in indices]
        if len(notes) == 1:
            return Note(notes[0])
        else:
            return Chord(notes)

    def note_to_event(self, element: Union[Note, Chord]) -> np.ndarray:
        event = np.zeros(NOTE_SIZE)
        if isinstance(element, Note):
            event[self.note_to_int(element)] = 1
        elif isinstance(element, Chord):
            event[[self.note_to_int(n) for n in element]] = 1
        else:
            raise ValueError(f"Unknown music21 element: {element}")
        return event


class OneHotEvents(Encoding):
    """Represents MIDI as a sequence of events. An event is a unique combination of one more more notes.
    Events are encoded as a numpy array of size max max combinations containing the duration of each note
    in the event at the corresponding index. The index is determined by sorting all combinations.

    IMPORTANT: This encoding is memory expensive and TF may error out depending on GPU. If that is the case
    setting n_midis to be less than the entire dataset will fix it. Can also try setting: TF_GPU_ALLOCATOR=cuda_malloc_async

    Example:
        Stream([Note(C#4), Chord(C#4, E4, G#4)]) --> np.array([[0, 1], [1, 0]])
    """

    requires_mappings = True
    compressed = False

    def create_mappings(self, all_midi: List[Stream]):
        """Create the encoding and decoding mappings to the entire dataset"""
        as_strings = []
        for midi in all_midi:
            midi = self.preprocess(midi)
            for element in midi.flat.notes:
                if isinstance(element, Note):
                    as_strings.append(str(element.pitch))
                elif isinstance(element, Chord):
                    as_strings.append("_".join([str(note.pitch) for note in element]))
                else:
                    raise ValueError(f"Unknown music21 element: {element}")

        complete_note_set = sorted(set(as_strings))
        self.decode_map = {index: string for index, string in zip(range(len(complete_note_set)), complete_note_set)}
        self.encode_map = {string: index for index, string in self.decode_map.items()}
        self.note_dimension = len(self.encode_map)
        self.input_shape = self.note_dimension

    def verify_setup(self):
        if not any([hasattr(self, "encode_map"), hasattr(self, "decode")]):
            raise RuntimeError("Must call `create_mappings(all_midi)` before running the encoder")

    def event_to_note(self, event: np.ndarray) -> Union[Note, Chord]:
        notes = self.decode_map[np.argmax(event)].split("_")
        if len(notes) == 1:
            return Note(notes[0])
        else:
            return Chord(notes)

    def note_to_event(self, note: Union[Note, Chord]) -> np.ndarray:
        if isinstance(note, Note):
            as_string = str(note.pitch)
        elif isinstance(note, Chord):
            as_string = "_".join([str(n.pitch) for n in note])
        else:
            raise ValueError(f"Unknown music21 element: {note}")
        try:
            encoded_note = self.encode_map[as_string]
            return utils.to_categorical(encoded_note, num_classes=len(self.encode_map))
        except KeyError:
            partitioned_note = split_key(as_string, self.encode_map)
            if partitioned_note == (-1,):
                return None
            return (
                utils.to_categorical(self.encode_map[subnote], num_classes=len(self.encode_map))
                for subnote in partitioned_note
            )


class SingleNotes(PreservedEncoding):
    """Represents MIDI as a sequence of notes. Each note contains the pitch as a float defined as
    [note_to_int, duration, offset].

    """

    compressed = True
    input_shape = 3

    def event_to_note(self, event: np.ndarray) -> Note:
        return Note(int(event[0]))

    def note_to_event(self, element: Union[Note, Chord]) -> Tuple[np.ndarray]:
        if isinstance(element, Note):
            return (np.array([self.note_to_int(element)]),)
        elif isinstance(element, Chord):
            return tuple(np.array([self.note_to_int(n)]) for n in element)
        else:
            raise ValueError(f"Unknown music21 element: {element}")


class SingleEvents(PreservedEncoding, OneHotEvents):
    """Similar to OneHotEvents but uses integer instead of categorical space for each event. (SingleNotes and OneHotEvents hybrid)"""

    requires_mappings = True
    compressed = True
    input_shape = 3

    def event_to_note(self, event: np.ndarray) -> Union[Note, Chord]:
        notes = self.decode_map[event[0]].split("_")
        if len(notes) == 1:
            return Note(notes[0])
        else:
            return Chord(notes)

    def note_to_event(self, note: Union[Note, Chord]) -> int:
        if isinstance(note, Note):
            as_string = str(note.pitch)
        elif isinstance(note, Chord):
            as_string = "_".join([str(n.pitch) for n in note])
        else:
            raise ValueError(f"Unknown music21 element: {note}")
        try:
            return np.array([self.encode_map[as_string]])
        except KeyError:
            partitioned_note = split_key(as_string, self.encode_map)
            if partitioned_note == (-1,):
                return None
            return tuple(np.array([self.encode_map[subnote]]) for subnote in partitioned_note)

    def create_mappings(self, *args, **kwargs):
        super().create_mappings(*args, **kwargs)
        self.input_shape = 3


class OneHotEventsCD(OneHotEvents):
    """Similar to OneHotEvents but rounds the duration to the nearest value in the duration set and uses duration as part of the
    categorical dimension space.

    e.g. a Single event is encoded as [0 0 0 0 0 1 0 0 ...] where the dimension space is the dimension space of the notes * len(duration_set)
    """

    requires_mappings = True
    compressed = False

    def __init__(self, *args, duration_set: Set[float] = {0.5, 0.75, 1}, **kwargs):
        super().__init__(*args, **kwargs)
        self.duration_set = duration_set

        if self.preserve_durations:
            logger.warning("This encoding does not support preserve_durations=True. Setting to False")
            self.preserve_durations = False

    def snap_duration(self, duration: float) -> float:
        """Snap the duration to the nearest value in the duration set"""
        return min(self.duration_set, key=lambda x: abs(x - duration))

    def create_mappings(self, all_midi: List[Stream]):
        """Create the encoding and decoding mappings to the entire dataset"""
        as_strings = []
        for midi in all_midi:
            midi = self.preprocess(midi)
            for element in midi.flat.notes:
                for length in self.duration_set:
                    if isinstance(element, Note):
                        as_strings.append(str(element.pitch) + "_" + str(length))
                    elif isinstance(element, Chord):
                        as_strings.append("_".join([str(note.pitch) for note in element]) + "_" + str(length))
                    else:
                        raise ValueError(f"Unknown music21 element: {element}")

        complete_note_set = sorted(set(as_strings))
        self.decode_map = {index: string for index, string in zip(range(len(complete_note_set)), complete_note_set)}
        self.encode_map = {string: index for index, string in self.decode_map.items()}
        self.note_dimension = len(self.encode_map)
        self.input_shape = self.note_dimension

    def event_to_note(self, event: np.ndarray) -> Union[Note, Chord]:
        notes, duration = np.split(self.decode_map[np.argmax(event)].split("_"), [-1])
        if len(notes) == 1:
            return Note(notes[0], quarterLength=float(duration))
        else:
            return Chord(notes, quarterLength=float(duration))

    def note_to_event(self, note: Union[Note, Chord]) -> np.ndarray:
        if isinstance(note, Note):
            as_string = str(note.pitch) + "_" + str(self.snap_duration(float(note.quarterLength)))
        elif isinstance(note, Chord):
            as_string = (
                "_".join([str(n.pitch) for n in note]) + "_" + str(self.snap_duration(float(note.quarterLength)))
            )
        else:
            raise ValueError(f"Unknown music21 element: {note}")
        return utils.to_categorical(self.encode_map[as_string], num_classes=len(self.encode_map))


class OneHotEventsWithOD(OneHotEvents, PreservedEncoding):
    """Similar to OneHotEvents preserves duration and offset."""

    requires_mappings = True
    compressed = False

    def create_mappings(self, *args, **kwargs):
        super().create_mapping(*args, **kwargs)
        self.input_shape = self.note_dimension + 2


class SingleEventsWithoutOD(OneHotEvents, NonPreservedEncoding):
    requires_mappings = True
    compressed = True
    input_shape = 1

    def event_to_note(self, event: np.ndarray) -> Union[Note, Chord]:
        notes = self.decode_map[event[0]].split("_")
        if len(notes) == 1:
            return Note(notes[0])
        else:
            return Chord(notes)

    def note_to_event(self, note: Union[Note, Chord]) -> int:
        if isinstance(note, Note):
            as_string = str(note.pitch)
        elif isinstance(note, Chord):
            as_string = "_".join([str(n.pitch) for n in note])
        else:
            raise ValueError(f"Unknown music21 element: {note}")
        return np.array([self.encode_map[as_string]])
