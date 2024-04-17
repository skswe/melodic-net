import React, { FormEvent, useEffect, useState } from 'react';

import axios from 'axios';
import InputParameters from '../../components/InputParameters';
import SampleMIDIComponent from '../../components/InputParameters/SampleMIDI';
import { GenMidi, SampleMIDI } from '../../types';
import { extractFilesFromZip } from '../../utils/server';

import PreviewZone from '../../components/PreviewZone';
import { FetchSampleMidis } from './data';
import './style.scss';

const HomePage: React.FC = () => {
  const [nOutputs, setNOutputs] = useState<number>(1);
  const [octaveRange, setOctaveRange] = useState<[number, number]>([2, 6]);
  const [keySignature, setKeySignature] = useState<string>('orig');
  const [mood, setMood] = useState<string>('regular');
  const [outputLength, setOutputLength] = useState<number>(16);
  const [temperature, setTemperature] = useState<number>(0.9);
  const [seed, setSeed] = useState<string>('');
  const [inpMidi, setInpMidi] = useState<File | undefined>(undefined);
  const [inpImage, setInpImage] = useState<File | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [genMidis, setGenMidis] = useState<GenMidi[]>([]);
  const [sampleMidis, setSampleMidis] = useState<(SampleMIDI | undefined)[]>(
    []
  );

  const handleGenerate = async (event: FormEvent<HTMLButtonElement>) => {
    event.preventDefault();

    const formData = new FormData();
    formData.append('outputCount', String(nOutputs));
    formData.append('minOctave', String(octaveRange[0]));
    formData.append('maxOctave', String(octaveRange[1]));
    formData.append('keySignature', keySignature);
    formData.append('mood', mood);
    formData.append('outputLength', String(outputLength));
    formData.append('temperature', String(temperature));
    formData.append('seed', seed);
    if (inpMidi) {
      formData.append('file', inpMidi);
    }

    setLoading(true);
    setError(undefined);
    setGenMidis([]);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      const res = await axios.post(`${backendUrl}/predict`, formData);

      const fileList = await extractFilesFromZip(res);

      const _genMidis: GenMidi[] = [];

      for (let i = 0; i < fileList.length; i += 2) {
        const jpgFile = fileList[i];
        const midFile = fileList[i + 1];

        _genMidis.push({
          midiFile: midFile,
          imageFile: jpgFile,
        });
      }

      setGenMidis(_genMidis);
    } catch (error) {
      console.error(error);
      if (axios.isAxiosError(error) && error.response) {
        const errorMsg = await JSON.parse(error.response.data);
        setError(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    FetchSampleMidis().then((files) => setSampleMidis(files));
  }, []);

  return (
    <div className='home-page'>
      <h1>MelodicNet</h1>
      <InputParameters
        nOutputs={nOutputs}
        octaveRange={octaveRange}
        keySignature={keySignature}
        mood={mood}
        outputLength={outputLength}
        temperature={temperature}
        seed={seed}
        inpMidi={inpMidi}
        handleNOutputsChange={(_, value) => setNOutputs(value as number)}
        handleOctaveRangeChange={(_, value) =>
          setOctaveRange(value as [number, number])
        }
        handleKeySignatureChange={(e) => setKeySignature(e.target.value)}
        handleMoodChange={(e) => setMood(e.target.value)}
        handleOutputLengthChange={(_, value) =>
          setOutputLength(value as number)
        }
        handleTemperatureChange={(_, value) => setTemperature(value as number)}
        handleSeedChange={(e) => {
          let newSeed = e.target.value;
          if (isNaN(Number(newSeed)) || Number(newSeed) < 1) newSeed = '';
          setSeed(newSeed.toString());
        }}
        handleInpMidiChange={(file) => setInpMidi(file)}
      />

      {inpMidi && (
        <button id='generate' onClick={handleGenerate}>
          Generate New MIDI{nOutputs > 1 && 's'}
        </button>
      )}
      {loading && <h3>Generating new MIDI{nOutputs > 1 && 's'}...</h3>}
      {error && <h2 className='error'>{error}</h2>}
      <PreviewZone inputMidi={inpMidi} inputImage={inpImage} generatedMidis={genMidis} />
      <div className='sample-midis'>
        <h3>Sample input MIDIs</h3>
        <p>(Click to select)</p>
        <div className='draggables'>
          {sampleMidis.map(
            (sampleMidi, i) =>
              sampleMidi && (
                <SampleMIDIComponent
                  key={i}
                  sampleMidi={sampleMidi}
                  setInpMidi={setInpMidi}
                  setInpImage={setInpImage}
                  setSeed={setSeed}
                  setTemperature={setTemperature}
                />
              )
          )}
        </div>
      </div>
    </div>
  );
};

export default HomePage;
