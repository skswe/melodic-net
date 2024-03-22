import React, { ChangeEvent, useState } from 'react';
import './style.scss';

type UploadProps = {
  file: File | undefined;
  setFile: (file: File | undefined) => void;
};

const Upload: React.FC<UploadProps> = ({ file, setFile }) => {
  const [error, setError] = useState<string>('');
  const [drag, setDrag] = useState<boolean>(false);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    event.preventDefault();
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (files.length > 1) {
      setError('Uploading multiple files not supported yet.');
      return;
    }

    if (!['audio/midi', 'audio/x-midi', 'audio/mid'].includes(files[0].type)) {
      setError('Only MIDI files are supported.');
      return;
    }

    setError('');
    setFile(files[0]);
  };

  return (
    <div
      className={`upload-zone${drag ? ' drag-over' : ''}`}
      onDragEnter={() => setDrag(true)}
      onDragLeave={() => setDrag(false)}
      onDragOver={(e) => e.preventDefault()}
      onDrop={() => setDrag(false)}
    >
      <input
        type='file'
        onChange={handleFileChange}
        accept='audio/midi, audio/x-midi, audio/mid'
      />
      <span id='input-text'>
        {file ? file.name : 'Upload Inspiration MIDI'}
      </span>
      {file && <span id='input-text'>(click to change)</span>}
      {error && <span id='error'>{error}</span>}
    </div>
  );
};

export default Upload;
