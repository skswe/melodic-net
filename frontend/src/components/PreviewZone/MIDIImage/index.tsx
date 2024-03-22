import axios from 'axios';
import React, { useEffect, useState } from 'react';
import './style.scss';

type MIDIImageProps = {
  image?: File;
  midi?: File;
  playerPosition: number;
};

const MIDIImage: React.FC<MIDIImageProps> = ({
  image,
  midi,
  playerPosition,
}) => {
  const [midiImage, setMidiImage] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);

  const getMidiImage = async (midi: File) => {
    try {
      const backendUrl =
        import.meta.env.VITE_BACKEND_URL;
      const formData = new FormData();
      formData.append('file', midi);
      const res = await axios.post(`${backendUrl}/midi_image`, formData);
      return URL.createObjectURL(res.data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    // If an image is provided, it is loaded
    // If an image is not provided, but a midi is, the midi is sent to the backend to generate an image
    if (image) {
      setMidiImage(undefined);
      setLoading(false);
    }
    if (!image && midi) {
      (async () => {
        setMidiImage(undefined);
        setLoading(true);
        const _midiImage = await getMidiImage(midi);
        if (_midiImage) {
          setMidiImage(_midiImage);
          setLoading(false);
        }
      })();
    }
  }, [image, midi]);

  return (
    <>
      {(midiImage || image) && (
        <div className='midi-image'>
          <img
            alt='midi'
            src={
              midiImage || URL.createObjectURL(image!.slice(0, image!.size!))
            }
          />
          <span style={{ left: `${13.3 + (91 - 13.3) * playerPosition}%` }} />
        </div>
      )}
      {loading && <div className='loading'>Loading image...</div>}
    </>
  );
};
export default MIDIImage;
