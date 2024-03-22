import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import React from 'react';

import { promptDownload } from '../../../utils/server';
import './style.scss';

type LibraryMIDIProps = {
  name: string;
  url?: string;
  selected: boolean;
  handleSelectMidi: () => void;
};

const LibraryMIDI: React.FC<LibraryMIDIProps> = ({ name, url, selected, handleSelectMidi }) => {
  return (
    <div className='library-midi'>
      <label>{name}</label>
      {!selected ? (
        <AddCircleOutlineIcon className='add-button' onClick={handleSelectMidi} />
      ) : (
        <CheckCircleIcon className='active-button' />
      )}
      {url && (
        <CloudDownloadIcon
          className='download-button'
          onClick={() => promptDownload(url, name)}
        />
      )}
    </div>
  );
};
export default LibraryMIDI;
