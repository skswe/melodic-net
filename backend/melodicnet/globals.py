import logging

LOGGING_FORMATTER = logging.Formatter(
    "{asctime}.{msecs:03.0f} {levelname:<8} {name:<50}{funcName:>35}:{lineno:<4} {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
)

### Conversion constants ###
INT_TO_PITCH = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F", 6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}
PITCH_TO_INT = {v: k for k, v in INT_TO_PITCH.items()}  # Reversed map
FLAT_TO_SHARP = {"D-": "C#", "E-": "D#", "G-": "F#", "A-": "G#", "B-": "A#"}
SHARP_TO_FLAT = {v: k for k, v in FLAT_TO_SHARP.items()}  # Reversed map
PITCHES_PER_OCTAVE = 12
QUARTER_TO_SIXTEENTH = 4

### Model params ###
N_OCTAVES = 10
NOTE_SIZE = N_OCTAVES * PITCHES_PER_OCTAVE
LONGEST_DURATION = 8
LONGEST_OFFSET = 4
# number of notes in a training/prediction sequence
INPUT_SEQUENCE_LENGTH = 12
DEFAULT_WEIGHT_OUTPATH = "model_weights/"
DEFAULT_PREDICTION_OUTPATH = "outputs/output.mid"


### Server params ###
MAX_FILE_UPLOAD_BYTES = 3 * 1024  # 3 KB


### Misc ###
# Blacklisted midis that are known to cause issues
BLACKLISTED_MIDIS = {"LiquorPluck70bpm.mid"}
