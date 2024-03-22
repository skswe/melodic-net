import React from 'react';

type SampleMIDIProps = {
  name: string;
  url: string;
  setInpMidi: (file: File | undefined) => void;
};

const SampleMIDI: React.FC<SampleMIDIProps> = ({ name, url, setInpMidi }) => {
  const handleClick = () => {
    fetch(url)
      .then((res) => res.blob())
      .then((blob) => {
        const file = new File([blob], name, { type: 'audio/midi' });
        setInpMidi(file);
      });
  };
  return (
    <button className='sample-midi' onClick={handleClick}>
      {name}
    </button>
  );
};
export default SampleMIDI;
