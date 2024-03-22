import './style.scss';

const AboutPage = () => {
  return (
    <div className='about-page'>
      <h1>What is MelodicNet?</h1>
      <div className='container'>
        <p>
          MelodicNet is an AI model that generates new melodies in the style of
          a given MIDI file. It is built using a deep learning model called a
          Long Short-Term Memory (LSTM) network. To try it out, upload a MIDI
          file and click "Generate New MIDI". You can listen to the generated
          MIDI files using the built-in MIDI player, or download them to your
          computer.
        </p>
      </div>
    </div>
  );
};

export default AboutPage;
