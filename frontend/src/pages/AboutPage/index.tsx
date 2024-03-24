import './style.scss';

const AboutPage = () => {
  return (
    <div className='about-page'>
      <h1>What is MelodicNet?</h1>
      <div className='container'>
        <p>
          <strong>MelodicNet</strong> is a generative AI application tailored to
          aid music producers in melody creation. By inputting an "inspiration"
          MIDI file, the app generates new MIDI files that echo elements of the
          original composition. While the current output may require further
          editing before integration into a final composition,{' '}
          <strong>MelodicNet</strong> serves as a tool for sparking creativity
          and exploration. Rather than providing fully structured melodies, it
          excels in generating unique melodic phrases, offering users a starting
          point for musical experimentation and development.
        </p>
      </div>
    </div>
  );
};

export default AboutPage;
