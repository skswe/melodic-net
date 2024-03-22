import Slider from '@mui/material/Slider';
import React, { ChangeEvent } from 'react';
import Upload from './FileUpload';
import './style.scss';

type InputParametersProps = {
  nOutputs: number;
  octaveRange: [number, number];
  keySignature: string;
  mood: string;
  outputLength: number;
  temperature: number;
  seed: string;
  inpMidi: File | undefined;
  handleNOutputsChange: (event: Event, value: number | number[]) => void;
  handleOctaveRangeChange: (event: Event, value: number | number[]) => void;
  handleKeySignatureChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  handleMoodChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  handleOutputLengthChange: (event: Event, value: number | number[]) => void;
  handleTemperatureChange: (event: Event, value: number | number[]) => void;
  handleSeedChange: (event: ChangeEvent<HTMLInputElement>) => void;
  handleInpMidiChange: (file: File | undefined) => void;
};

const makeSliderMarks = (min: number, max: number, step: number = 1) => {
  return Array.from(
    { length: (max - min) / step + 1 },
    (_, i) => i * step + min
  ).map((i) => ({
    value: i,
    label: i.toString(),
  }));
};

const InputParameters: React.FC<InputParametersProps> = ({
  nOutputs,
  // octaveRange,
  keySignature,
  // mood,
  outputLength,
  temperature,
  seed,
  inpMidi,
  handleNOutputsChange,
  // handleOctaveRangeChange,
  handleKeySignatureChange,
  // handleMoodChange,
  handleOutputLengthChange,
  handleTemperatureChange,
  handleSeedChange,
  handleInpMidiChange,
}) => {
  return (
    <div className='input-parameters'>
      <div
        title='Control the number of MIDI files to generate'
        id='n-outputs-input'
      >
        <h3>Number of files to generate</h3>
        <Slider
          value={nOutputs}
          valueLabelDisplay='auto'
          onChange={handleNOutputsChange}
          min={1}
          max={5}
          marks={makeSliderMarks(1, 5)}
          className='slider'
        />
      </div>
      {/* <div
        id='octave-range-input'
        title='Control the octave range of the generated MIDI(s)'
      >
        <h3>Octave Range</h3>
        <Slider
          value={octaveRange}
          valueLabelDisplay='auto'
          onChange={handleOctaveRangeChange}
          min={1}
          max={8}
          marks={makeSliderMarks(1, 8)}
          className='slider'
        />
      </div> */}
      <div
        title='Control how long (measured in bars) the output MIDI(s) is(are)'
        id='output-length-input'
      >
        <h3>Generated MIDI length (bars):</h3>
        <Slider
          value={outputLength}
          valueLabelDisplay='auto'
          onChange={handleOutputLengthChange}
          min={8}
          max={64}
          step={4}
          marks={makeSliderMarks(8, 64, 8)}
          className='slider'
        />
      </div>
      <div
        title='Control the randomness of the generated MIDI(s). Higher values will result in more random output.'
        id='temperature-input'
      >
        <h3>Temperature</h3>
        <Slider
          value={temperature}
          valueLabelDisplay='auto'
          onChange={handleTemperatureChange}
          min={0.5}
          max={1.5}
          step={0.1}
          marks={[{ value: 0.5, label: '0.5' }, { value: 1.5, label: '1.5' }]}
          className='slider'
        />
      </div>
      <div className='dropdown-inputs'>
        <div
          title='Control the key signature of the generated MIDI(s)'
          id='keysig-input'
        >
          <h3>Key Signature</h3>
          <select value={keySignature} onChange={handleKeySignatureChange}>
            <option value='orig'>Same as input</option>
            <option value='C'>C</option>
            <option value='C#'>C#</option>
            <option value='D'>D</option>
            <option value='D#'>D#</option>
            <option value='E'>E</option>
            <option value='F'>F</option>
            <option value='F#'>F#</option>
            <option value='G'>G</option>
            <option value='G#'>G#</option>
            <option value='A'>A</option>
            <option value='A#'>A#</option>
            <option value='B'>B</option>
          </select>
        </div>
        {/* <div title='Control the mood of the generated MIDI(s)' id='mood-input'>
          <h3>Mood</h3>
          <select value={mood} onChange={handleMoodChange}>
            <option value='fast'>fast</option>
            <option value='regular'>regular</option>
            <option value='slow'>slow</option>
            <option value='peaceful'>peaceful</option>
          </select>
        </div> */}
        <div
          title='Set the random seed to generate reproducible output(s)'
          id='seed-input'
        >
          <h3>Random seed:</h3>
          <input type='number' value={seed} onChange={handleSeedChange} />
        </div>
      </div>
      <Upload file={inpMidi} setFile={handleInpMidiChange} />
    </div>
  );
};

export default InputParameters;
