import React, { ChangeEvent, useEffect, useState } from 'react';
import 'react-multi-carousel/lib/styles.css';
import { GenMidi } from '../../types';
import { promptDownload, zipFiles } from '../../utils/server';
import LibraryMIDI from './LibraryMIDI';
import MIDIImage from './MIDIImage';
import MIDIPlayer from './MIDIPlayer';
import './style.scss';

type PreviewZoneProps = {
  inputMidi?: File;
  generatedMidis: GenMidi[];
};

const PreviewZone: React.FC<PreviewZoneProps> = ({
  inputMidi,
  generatedMidis,
}) => {
  const [sound, setSound] = useState<number>(53);
  const [selectedMidi, setSelectedMidi] = useState<GenMidi | undefined>(
    Object({ midiFile: inputMidi, imageFile: undefined })
  );
  const [playerPosition, setPlayerPosition] = useState<number>(0);

  const handleSoundChange = (event: ChangeEvent<HTMLInputElement>) => {
    let newSound = Number(event.target.value);
    if (newSound === 0 && sound === 1) {
      newSound = 100;
    } else if (newSound === 101 && sound === 100) {
      newSound = 1;
    } else if (newSound < 1 || newSound > 100) {
      return;
    }
    setSound(newSound);
  };

  const handleDownloadAll = async () => {
    const zip = await zipFiles(
      generatedMidis.map((genMidi) => genMidi.midiFile)
    );
    promptDownload(zip, 'all_midis.zip');
  };

  useEffect(() => {
    setSelectedMidi(generatedMidis[0]);
  }, [generatedMidis]);

  useEffect(() => {
    setSelectedMidi(Object({ midiFile: inputMidi, imageFile: undefined }));
  }, [inputMidi]);

  return (
    <div className='preview-zone'>
      <div className='header'>
        <h3>MIDI Player</h3>
        <div className='instrument-selector'>
          <label>Sound</label>
          <input
            type='number'
            min={0}
            value={sound}
            onChange={handleSoundChange}
          />
        </div>
      </div>
      <MIDIPlayer
        midi={selectedMidi?.midiFile}
        sound={sound}
        handlePlayerPositionChange={setPlayerPosition}
      />
      <MIDIImage
        midi={selectedMidi?.midiFile}
        image={selectedMidi?.imageFile}
        playerPosition={playerPosition}
      />
      <div className='library'>
        {inputMidi && (
          <LibraryMIDI
            name='Input MIDI'
            selected={inputMidi === selectedMidi?.midiFile}
            handleSelectMidi={() =>
              setSelectedMidi(
                Object({ midiFile: inputMidi, imageFile: undefined })
              )
            }
          />
        )}
        {generatedMidis.map((genMidi, i) => (
          <LibraryMIDI
            key={i}
            name={genMidi.midiFile.name}
            url={URL.createObjectURL(genMidi.midiFile)}
            selected={selectedMidi === generatedMidis[i]}
            handleSelectMidi={() => setSelectedMidi(generatedMidis[i])}
          />
        ))}
      </div>
      {generatedMidis.length > 1 && (
        <button onClick={handleDownloadAll}>Download all </button>
      )}
    </div>
  );
};
export default PreviewZone;
