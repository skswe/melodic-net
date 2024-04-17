import { MidiObj, SampleMIDI } from '../../../types';

type SampleMIDIProps = {
  sampleMidi: SampleMIDI;
  setInpMidi: (inpMidi: MidiObj) => void;
  setSeed: (seed: string) => void;
  setTemperature: (temperature: number) => void;
};

const SampleMIDIComponent: React.FC<SampleMIDIProps> = ({
  sampleMidi,
  setInpMidi,
  setSeed,
  setTemperature,
}) => {
  const handleClick = async () => {
    const res = await fetch(sampleMidi.url);
    const blob = await res.blob();
    const file = new File([blob], sampleMidi.name, {
      type: 'audio/midi',
    });
    const imageRes = await fetch(sampleMidi.imageUrl);
    const imageBlob = await imageRes.blob();
    const imageFile = new File([imageBlob], `${sampleMidi.name}.jpg`, {
      type: 'image/jpeg',
    });
    setInpMidi({ midiFile: file, imageFile });
    setSeed(sampleMidi.seed);
    setTemperature(sampleMidi.temperature);
  };

  return (
    <button className='sample-midi' onClick={handleClick}>
      {sampleMidi.name}
    </button>
  );
};
export default SampleMIDIComponent;
