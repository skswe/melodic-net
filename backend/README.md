# MelodicNet Backend

The backend for MelodicNet is built using Python and TensorFlow. Two scripts are
provided: `train.py` and `predict.py`. The former is used to train the model,
while the latter is used to generate melodies using a trained model.

## Installation

1. Clone the repository:

`git clone https://github.com/skswe/melodicnet.git`

2. Install dependencies:

`cd melodicnet/backend && pip install -r requirements.txt`

## Usage

### Training

```
python3 train.py <identifier> [--log-level <log_level>] [--midi-path <midi_path>]
    [--refresh-encodings] [--refresh-cleaned-midis] [--n-midis <n_midis>]
    [--partition <partition>] [--epochs <epochs>]
```

- identifier: Identifier for the model.
- --log-level: (Optional) Logging level (default: "INFO").
- --midi-path: (Optional) Path to the MIDI files (default:
  "data/all_midi/\*.mid").
- --refresh-encodings: (Optional) Recompute encodings instead of using cached
  versions.
- --refresh-cleaned-midis: (Optional) Recompute cleaned MIDIs instead of using
  cached versions.
- --n-midis: (Optional) Number of MIDIs to read and process from the source
  directory (default: 100).
- --partition: (Optional) Key type to filter the loaded MIDIs by (major or
  minor).
- --epochs: (Optional) Number of epochs to train the model for (default: 130).

The training script will print the location of the saved model files. Pass this
path as the `<model_path>` argument of the prediction script.

### Prediction

```
python3 predict.py <model_path> <midi_path> [--partition <partition>] [--output-length <output_length>]
    [--temperature <temperature>] [--n-outputs <n_outputs>] [--octave-range <low> <high>]
    [--key-signature <key_signature>] [--random-seed <random_seed>]
```

- model_path: Path to the directory containing the trained model files.
- midi_path: Path to the input MIDI file.
- --log-level: (Optional) Logging level (default: "INFO").
- --partition: (Optional) Key type to filter the loaded MIDIs by (major or
  minor).
- --output-length: (Optional) Output MIDI length in bars (default: 32).
- --temperature: (Optional) Controls the randomness of the output. Higher values
  result in more random output (default: 0.9).
- --n-outputs: (Optional) Number of output MIDIs to generate (default: 1).
- --octave-range: (Optional) Acceptable octave range for notes to be placed in
  (default: (3, 7)).
- --key-signature: (Optional) Desired key signature of the output melody.
- --random-seed: (Optional) If provided, the output will be deterministic with
  the seed.
