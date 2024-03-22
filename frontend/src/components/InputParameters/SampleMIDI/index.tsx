type SampleMIDIProps = {
  name: string;
  handleClick: () => void;
};

const SampleMIDI: React.FC<SampleMIDIProps> = ({ name, handleClick }) => {
  return (
    <button className='sample-midi' onClick={handleClick}>
      {name}
    </button>
  );
};
export default SampleMIDI;
