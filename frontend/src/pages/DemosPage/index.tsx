import PauseIcon from '@mui/icons-material/Pause';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious';
import React, { useEffect, useRef, useState } from 'react';
import { Song, SongData, SongPart } from './data.ts';
import './style.scss';

type SongInfo = {
  currentTime: number;
  duration: number;
};

type SkipDirection = 'skip-forward' | 'skip-back';

const DemosPage: React.FC = () => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [songs, setSongs] = useState<Song[]>(SongData());
  const [currentSong, setCurrentSong] = useState<Song>(songs[0]);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [songInfo, setSongInfo] = useState<SongInfo>({
    currentTime: 0,
    duration: 0,
  });

  const setNewSongActive = (newSong: Song) => {
    const newSongs = songs.map((song) => ({
      ...song,
      active: song.id === newSong.id,
    }));
    setSongs(newSongs);
    setCurrentSong(newSong);
  };

  const activateSongPart = (part: SongPart) => {
    const newSongParts = currentSong.parts.map((songPart) => ({
      ...songPart,
      active: songPart.label === part.label,
    }));
    const newSong = { ...currentSong, parts: newSongParts };
    setCurrentSong(newSong);
  };

  const updateTimeHandler = (
    e: React.SyntheticEvent<HTMLAudioElement, Event>
  ) => {
    const { currentTime, duration } = e.currentTarget;
    for (const part of currentSong.parts) {
      if (currentTime >= part.start && currentTime <= part.end) {
        activateSongPart(part);
      }
    }
    setSongInfo({ ...songInfo, currentTime, duration });
  };

  const songEndHandler = () => {
    const currentIndex = songs.findIndex((song) => song.id === currentSong.id);
    const nextIndex = (currentIndex + 1) % songs.length;
    const nextSong = songs[nextIndex];
    setNewSongActive(nextSong);
  };

  const playSongHandler = () => {
    setIsPlaying(!isPlaying);
  };

  const getTime = (time: number) => {
    const minute = Math.floor(time / 60);
    const second = ('0' + Math.floor(time % 60)).slice(-2);
    return `${minute}:${second}`;
  };

  const dragHandler = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    const currentTime = parseFloat(e.target.value);
    audioRef.current!.currentTime = currentTime;
    setSongInfo({ ...songInfo, currentTime });
  };

  const skipTrackHandler = (direction: SkipDirection) => {
    const currentIndex = songs.findIndex((song) => song.id === currentSong.id);
    let nextIndex;
    if (direction === 'skip-forward') {
      nextIndex = (currentIndex + 1) % songs.length;
    } else if (direction === 'skip-back') {
      nextIndex = (currentIndex - 1 + songs.length) % songs.length;
    }
    const nextSong = songs[nextIndex!];
    setNewSongActive(nextSong);
  };

  const togglePartHover = (part: SongPart) => {
    const newSongParts = currentSong.parts.map((songPart) => ({
      ...songPart,
      hover: songPart.label === part.label && !songPart.hover,
    }));
    const newSong = { ...currentSong, parts: newSongParts };
    setCurrentSong(newSong);
  };

  const handlePartClick = (part: SongPart) => {
    const currentTime = part.start;
    audioRef.current!.currentTime = currentTime;
    setSongInfo({ ...songInfo, currentTime });
  };

  useEffect(() => {
    if (isPlaying) {
      audioRef.current?.play();
    } else {
      audioRef.current?.pause();
    }
  }, [currentSong, isPlaying]);

  return (
    <div className='demos-page'>
      <div className='header'>
        <h1>Demo Songs</h1>
      </div>
      <div className='overview'>
        <p>
          The following songs are demos of the MelodicNet model. Each song
          contains 4 parts. 1) The original MIDI file, 2) MelodicNet's output,
          3) MelodicNet's output manually tweaked, and 4) The final musical
          piece. These demos showcase MelodicNet's usecase for helping musicians
          compose new melodies.
        </p>
      </div>
      <div className='now-playing'>
        <div className='song'>
          <img src={currentSong.cover} alt={currentSong.name}></img>
          <h2>{currentSong.name}</h2>
        </div>
        <div className='description'>
          {currentSong.parts.map((part, i) => (
            <p
              key={part.label}
              className={
                'part' +
                `${part.active ? ' active' : ''}` +
                `${part.hover ? ' hover' : ''}`
              }
              onClick={() => handlePartClick(part)}
            >
              {i + 1}) {part.label}
            </p>
          ))}
        </div>
      </div>
      <div className='songs-container'>
        {songs.map((song) => (
          <div
            key={song.id}
            className={`song-card ${song.active ? 'active' : ''}`}
            onClick={() => setNewSongActive(song)}
          >
            <img src={song.cover} alt={song.name}></img>
            <h3>{song.name}</h3>
          </div>
        ))}
      </div>
      <div className='audio-player'>
        <div className='time-container'>
          <p>{getTime(songInfo.currentTime || 0)}</p>
          <div className='time-track'>
            <input
              onChange={dragHandler}
              min={0}
              max={songInfo.duration || 0}
              value={songInfo.currentTime}
              type='range'
            />
            {currentSong.parts.map((part) => (
              <div
                key={part.label}
                className='part-tooltip'
                onMouseEnter={() => togglePartHover(part)}
                onMouseLeave={() => togglePartHover(part)}
                onClick={() => handlePartClick(part)}
                title={part.label}
                style={{
                  left: `${(part.start / songInfo.duration) * 100}%`,
                }}
              />
            ))}
            <div
              className='progress'
              style={{
                width: `${Math.round(
                  (songInfo.currentTime / songInfo.duration) * 100
                )}%`,
              }}
            />
          </div>

          <p>{getTime(songInfo.duration || 0)}</p>
        </div>

        <div className='player-controls'>
          <button onClick={() => skipTrackHandler('skip-back')}>
            <SkipPreviousIcon />
          </button>
          {isPlaying ? (
            <button onClick={playSongHandler}>
              <PauseIcon />
            </button>
          ) : (
            <button onClick={playSongHandler}>
              <PlayArrowIcon />
            </button>
          )}
          <button onClick={() => skipTrackHandler('skip-forward')}>
            <SkipNextIcon />
          </button>
        </div>
      </div>
      <audio
        onLoadedMetadata={updateTimeHandler}
        onTimeUpdate={updateTimeHandler}
        onEnded={songEndHandler}
        ref={audioRef}
        src={currentSong.audio}
      />
    </div>
  );
};

export default DemosPage;
