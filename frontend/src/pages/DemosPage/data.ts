export type SongPart = {
  label: string;
  start: number;
  end: number;
  active: boolean;
  hover: boolean;
};

export type Song = {
  id: number;
  name: string;
  cover: string;
  audio: string;
  active: boolean;
  parts: SongPart[];
};

import beat_2 from '/assets/demos/beat_2.mp3';
import beat_3 from '/assets/demos/beat_3.mp3';
import beat_4 from '/assets/demos/beat_4.mp3';
import music_cover_2 from '/assets/music_cover2.jpg';
import music_cover_3 from '/assets/music_cover3.jpeg';
import music_cover_4 from '/assets/music_cover4.jpeg';

export const SongData = (): Song[] => {
  return [
    {
      id: 0,
      name: 'Demo 1',
      cover: music_cover_2,
      audio: beat_2,
      active: true,
      parts: [
        {
          label: 'The inspiration/input MIDI file',
          start: 0,
          end: 6,
          active: true,
          hover: false,
        },
        {
          label: "MelodicNet's Output",
          start: 7,
          end: 14,
          active: false,
          hover: false,
        },
        {
          label: "MelodicNet's Output manually tweaked",
          start: 15,
          end: 27,
          active: false,
          hover: false,
        },
        {
          label: 'The final musical piece',
          start: 28,
          end: 53,
          active: false,
          hover: false,
        },
      ],
    },
    {
      id: 1,
      name: 'Demo 2',
      cover: music_cover_3,
      audio: beat_3,
      active: false,
      parts: [
        {
          label: 'The inspiration/input MIDI file',
          start: 0,
          end: 7,
          active: true,
          hover: false,
        },
        {
          label: "MelodicNet's Output",
          start: 8,
          end: 16,
          active: false,
          hover: false,
        },
        {
          label: "MelodicNet's Output manually tweaked",
          start: 17,
          end: 30,
          active: false,
          hover: false,
        },
        {
          label: 'The final musical piece',
          start: 30,
          end: 58,
          active: false,
          hover: false,
        },
      ],
    },
    {
      id: 2,
      name: 'Demo 3',
      cover: music_cover_4,
      audio: beat_4,
      active: false,
      parts: [
        {
          label: 'The inspiration/input MIDI file',
          start: 0,
          end: 6,
          active: true,
          hover: false,
        },
        {
          label: "MelodicNet's Output",
          start: 7,
          end: 15,
          active: false,
          hover: false,
        },
        {
          label: "MelodicNet's Output manually tweaked",
          start: 16,
          end: 29,
          active: false,
          hover: false,
        },
        {
          label: 'The final musical piece',
          start: 30,
          end: 56,
          active: false,
          hover: false,
        },
      ],
    },
  ];
};
