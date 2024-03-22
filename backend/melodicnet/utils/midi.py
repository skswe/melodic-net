"""This module provides some useful utility functions for MIDI files.

Functions are provided as classmethods on the `MIDIUtils` class.

"""

import itertools
import logging
import os
import random
from io import BytesIO

import numpy as np
import pandas as pd
from music21.analysis.discrete import DiscreteAnalysisException
from music21.chord import Chord
from music21.converter import parse
from music21.graph.plot import HorizontalBarPitchSpaceOffset
from music21.interval import Interval
from music21.note import Note
from music21.stream import Stream

from ..globals import DEFAULT_PREDICTION_OUTPATH
from .misc import make_timestamped_dir

logger = logging.getLogger(__name__)


class MIDIUtils:
    """Collection of utility operations to perform on music21 objects"""

    @classmethod
    def trim_chords(cls, midi: Stream, overlap: bool = False):
        """Returns a new Stream object where all notes having the same start time have the same end time. If `overlap` is False, note
        endings will be trimmed to stop when the next note plays
        """
        note_info = cls.stream_to_dataframe(midi)

        # Trim chords to the same length
        note_info = note_info.drop(columns="duration").merge(
            note_info[["offset", "duration"]].groupby("offset", as_index=False).min(), how="left"
        )

        if not overlap:
            # Trim the end of notes to stop when the next note starts
            timings = note_info[["offset", "duration"]].drop_duplicates()
            timings["end_time"] = timings["offset"] + timings["duration"]
            timings["too_long"] = timings.end_time > timings.shift(-1).offset
            timings["correct_duration"] = timings.shift(-1).offset - timings.offset
            timings.loc[timings.too_long, "duration"] = timings.loc[timings.too_long, "correct_duration"]

            note_info = note_info.drop(columns="duration").merge(timings[["offset", "duration"]])

        return cls.dataframe_to_stream(note_info)

    @classmethod
    def stream_to_dataframe(cls, midi: Stream) -> pd.DataFrame:
        """Represent MIDI as a dataframe containing [offset, pitch, octave, duration]"""
        as_notes = []
        for element in midi.flat.notes:
            if isinstance(element, Note):
                as_notes.append(element)
            elif isinstance(element, Chord):
                chord_notes = [note for note in element]
                for note in chord_notes:
                    note.offset = element.offset
                    note.quarterLength = element.quarterLength
                as_notes.extend(chord_notes)

        note_info = pd.DataFrame(
            [
                {
                    "offset": note.offset,
                    "pitch": note.pitch.name,
                    "octave": note.octave,
                    "duration": note.quarterLength,
                }
                for note in as_notes
            ]
        )

        return note_info

    @classmethod
    def dataframe_to_stream(cls, df: pd.DataFrame) -> Stream:
        """Returns a new Stream object representing the MIDI from a dataframe"""

        def group_notes(g: pd.DataFrame):
            """Aggregate function to create a note / chord from a group of notes having the same start time"""
            duration = g.duration.min()
            offset = g.iloc[0].offset
            if len(g) == 1:
                note = g.iloc[0]
                return Note(note.pitch + str(note.octave), quarterLength=duration, offset=offset)
            else:
                notes = [
                    Note(note.pitch + str(note.octave), quarterLength=duration, offset=offset)
                    for idx, note in g.iterrows()
                ]
                return Chord(notes, offset=offset)

        stream = Stream()

        for offset, element in df.groupby("offset").apply(group_notes).items():
            stream.insert(offset, element)

        return stream

    @classmethod
    def midi_from_file(cls, path: str) -> Stream:
        """Read MIDI from file and return a music21 Stream object"""
        return parse(path, quantizePost=False)

    @classmethod
    def export_to_midi(
        cls,
        midi: Stream,
        output_dir: str = DEFAULT_PREDICTION_OUTPATH,
    ):
        """Export MIDI object to disk in `output_dir`/<timestamp>/midi.mid"""
        output_dir = os.path.join(make_timestamped_dir(os.path.dirname(output_dir)), os.path.basename(output_dir))
        midi.write("midi", output_dir)

    @classmethod
    def midi_to_bytes(cls, midi: Stream) -> BytesIO:
        """Returns MIDI object as bytes"""
        path = midi.write("midi")
        file = open(path, "rb")
        tmp = BytesIO(file.read())
        file.close()
        os.remove(path)
        return tmp

    @classmethod
    def print_midi(cls, midi: Stream, end: int = None, start: int = None):
        """Print Chord/Note, Offset, Duration of each event in the MIDI. specify `start` and `end` indices to control range of MIDI to print"""
        print(f"{'Chord/Note':44} {'Offset':8} {'Duration (QuarterLength)':8}")
        print("-" * 77)
        for element in midi.flat.notes[start:end]:
            print(f"{str(element):40} |{float(element.offset):8.2f} |{float(element.quarterLength):8.2f}")

    @classmethod
    def midi_as_strings(cls, midi):
        """Returns a list of strings representing each individual note in the MIDI. Each string is of the form `offset_duration_pitch`"""
        notes = []
        for element in midi.flat.notes:
            if isinstance(element, Note):
                notes.append(f"{element.offset}_{element.quarterLength}_{str(element)}")
            elif isinstance(element, Chord):
                notes.extend([f"{element.offset}_{element.quarterLength}_{str(note)}" for note in element])
        return sorted(notes)

    @classmethod
    def normalize_keysig(cls, midi: Stream) -> Stream:
        """Normalize the key signature of a midi to C maj/min"""
        try:
            key = midi.analyze("key").tonic.pitchClass
        except DiscreteAnalysisException:
            logger.warn("Could not analyze key signature, assuming C major")
            key = 0

        if key >= 6:
            transpose_by = 12 - key
        else:
            transpose_by = -key

        # Second transpose is to normalize flats to sharps
        midi = Stream(midi.transpose(transpose_by).transpose(0))
        midi.transpose_by = transpose_by
        return midi

    @classmethod
    def restore_keysig(cls, midi: Stream) -> Stream:
        """Restore the key signature of a normalized midi to its original key signature"""
        assert hasattr(midi, "transpose_by"), "Midi must have a `transpose_by` attribute"
        # Second transpose is to normalize flats to sharps
        return midi.transpose(-midi.transpose_by).transpose(0)

    @classmethod
    def trim_midi_length(cls, midi: Stream, length) -> Stream:
        """Truncate the MIDI to the specified length in quarter notes. If a note extends beyond the length, it will be trimmed to fit within the length.
        If a note starts after the length, it will be ignored."""
        new_output = Stream()
        for element in midi.flat.notes:
            if element.offset > length:
                pass
            elif element.offset + element.quarterLength > length:
                element.quarterLength = length - element.offset

            new_output.insert(element.offset, element)
        return new_output

    @classmethod
    def trim_midi_octave_range(cls, midi: Stream, min_octave: int = 3, max_octave: int = 7) -> Stream:
        """Trim the MIDI to the specified octave range. Notes outside the range will be clipped to the min/max octave."""
        midi = midi.__deepcopy__()

        # Adjust for 0-indexing
        min_octave = min_octave - 1
        max_octave = max_octave - 1

        def clip(element):
            if element.octave < min_octave:
                element.octave = min_octave
            elif element.octave > max_octave:
                element.octave = max_octave

        for event in midi.flat.notes:
            if isinstance(event, Note):
                clip(event)
            elif isinstance(event, Chord):
                for note in event:
                    clip(note)

        return midi

    @classmethod
    def midi_to_image_bytes(cls, midi: Stream, dpi: int = 300, title: str = "MIDI"):
        """Returns MIDI Image as bytes"""

        rand = int(random.random() * 10e9)
        path = f"mid_image{rand}.jpg"
        plot = HorizontalBarPitchSpaceOffset(midi, title=title)
        plot.dpi = dpi
        plot.doneAction = None
        plot.run()
        plot.figure.tight_layout()
        plot.figure.savefig(path, dpi=dpi)
        file = open(path, "rb")
        tmp = BytesIO(file.read())
        file.close()
        os.remove(path)
        return tmp

    @classmethod
    def interval_quality(cls, note_a: Note, note_b: Note, intervals: dict) -> float:
        """Returns the quality of the interval between two notes, according to the intervals dictionary"""
        interval = Interval(noteStart=note_a, noteEnd=note_b)
        return intervals[interval.simpleName]

    @classmethod
    def chord_quality(cls, chord: Chord, intervals) -> float:
        """Returns the quality of a chord, measured as the sum of all combinations of interval qualities between notes in the chord."""
        q = 0
        for note_a, note_b in itertools.combinations(chord, 2):
            q += cls.interval_quality(note_a, note_b, intervals)
        return q

    @classmethod
    def highest_octave(cls, midi: Stream) -> int:
        """Returns the highest octave in the MIDI"""
        return max(map(lambda el: max([x.octave for x in el]) if el.isChord else el.octave, midi.flat.notes))

    @classmethod
    def lowest_octave(cls, midi: Stream) -> int:
        """Returns the lowest octave in the MIDI"""
        return min(map(lambda el: min([x.octave for x in el]) if el.isChord else el.octave, midi.flat.notes))

    @classmethod
    def avg_note_duration(cls, midi: Stream) -> float:
        """Returns the average duration of the notes in the MIDI"""

        def mean(arr):
            return sum(arr) / len(arr)

        return mean(
            list(
                map(
                    lambda el: mean([x.quarterLength for x in el]) if el.isChord else el.quarterLength, midi.flat.notes
                )
            )
        )

    @classmethod
    def avg_note_offset(cls, midi: Stream) -> float:
        """Returns the average offset of the notes in the MIDI"""
        
        return cls.stream_to_dataframe(midi).offset.mean()