# MelodicNet Backend

## Overview

This is the backend for the MelodicNet project. It can be used to train a model
from a custom dataset of MIDI files, and to generate new music from a trained
model. The model can be used programatically via Python or exposed as a REST
API.

## Installation

## Usage

### Training

```
import melodicnet as mn

melodicnet = mn.MelodicNet()

melodicnet.load_data("path/to/midis/*.mid")
melodicnet.create_model()
melodicnet.train_model_weights()
config_path = melodicnet.generate_config_files()
```

### Generation

```
import melodicnet as mn

melodicnet = mn.MelodicNet(config_path="path/to/config/dir")
input_midi = mn.MIDIUtils.midi_from_file("path/to/midi/file")

melodicnet.load_mappings()
melodicnet.create_model()
melodicnet.load_model_weights()
output_midi = melodicnet.predict(
    input_midi,
    output_length=16,
    n_outputs=1,
)

mn.MIDIUtils.midi_to_file(output_midi, "path/to/output/midi/file")
```
