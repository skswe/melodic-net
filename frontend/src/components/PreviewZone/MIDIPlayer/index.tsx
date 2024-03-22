import JZZ from 'jzz';
// @ts-expect-error doesnt support TS
import add_gui_player from 'jzz-gui-player';
// @ts-expect-error doesnt support TS
import add_smf from 'jzz-midi-smf';
// @ts-expect-error doesnt support TS
import add_tiny_synth from 'jzz-synth-tiny';
import { useEffect, useRef, useState } from 'react';
import { fileToArrayBuffer } from '../../../utils/server';
import './style.scss';

add_gui_player(JZZ);
add_smf(JZZ);
add_tiny_synth(JZZ);
// @ts-expect-error doesnt support TS
JZZ.synth.Tiny.register('Web Audio');

type Player = {
  _out: {
    getSynth: (sound: number) => { r: number }[];
    setSynth: (channel: number, synth: { r: number }[]) => void;
  };
  _player: {
    _pos: number;
  };
  load: (midi: File) => void;
  play: () => void;
  stop: () => void;
};

type MIDIPlayerProps = {
  midi?: File;
  sound: number;
  handlePlayerPositionChange: (position: number) => void;
};

const MIDIPlayer: React.FC<MIDIPlayerProps> = ({
  midi,
  sound,
  handlePlayerPositionChange,
}) => {
  const [player, setPlayer] = useState<Player | undefined>(undefined);
  const playerRef = useRef<HTMLSpanElement>(null);
  const [intervalRef, setIntervalRef] = useState<number | undefined>(undefined);

  useEffect(() => {
    // Create player
    if (playerRef?.current?.children?.length) return;
    // @ts-expect-error doesnt support TS
    const _player = JZZ.gui.Player(playerRef.current);

    _player.onSelect = () => {
      const _synth = _player._out.getSynth(sound);
      _synth[0].r = 0.5;
      _synth[1].r = 0.5;
      _player._out.setSynth(0, _synth);
    };
    _player.onLoad = () => {
      _player.play();
      _player.stop();
      _player.loop(-1);
    };
    _player.onPlay = () => {
      const _update = () => {
        handlePlayerPositionChange(
          _player._player._pos / _player._player._duration
        );
      };
      setIntervalRef(setInterval(_update, 20));
      _player.playBtn.div.classList.add('active');
      _player.pauseBtn.div.classList.remove('active');
      _player.stopBtn.div.classList.remove('active');
    };
    _player.onResume = () => {
      _player.playBtn.div.classList.add('active');
      _player.pauseBtn.div.classList.remove('active');
    };
    _player.onStop = () => {
      if (intervalRef) clearInterval(intervalRef);
      handlePlayerPositionChange(0);
      _player.stopBtn.div.classList.add('active');
      _player.pauseBtn.div.classList.remove('active');
      _player.playBtn.div.classList.remove('active');
    };
    _player.onEnd = () => {
      if (_player._loop === -1) return;
      if (intervalRef) clearInterval(intervalRef);
      handlePlayerPositionChange(0);
      _player.stopBtn.div.classList.add('active');
      _player.pauseBtn.div.classList.remove('active');
      _player.playBtn.div.classList.remove('active');
    };
    _player.onPause = () => {
      _player.pauseBtn.div.classList.add('active');
      _player.playBtn.div.classList.remove('active');
    };
    _player.onLoop = (loop: boolean) => {
      if (loop) {
        _player.loopBtn.div.classList.add('active');
      } else {
        _player.loopBtn.div.classList.remove('active');
      }
    };

    _player.onJump = () => {
      handlePlayerPositionChange(
        _player._player._pos / _player._player._duration
      );
    };
    setPlayer(_player);

    return () => {
      _player.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // MIDI loaded
    if (player && midi) {
      (async function x() {
        player.stop();
        const midiBuffer = await fileToArrayBuffer(midi);
        // @ts-expect-error doesnt support TS
        player.load(new JZZ.MIDI.SMF(midiBuffer));
      })();
    }
  }, [midi, player]);

  useEffect(() => {
    // Sound changed
    try {
      if (!player || !player._out) return;
      const _synth = player._out.getSynth(sound);
      _synth[0].r = 0.5;
      _synth[1].r = 0.5;
      player._out.setSynth(0, _synth);
    } catch (e) {
      console.log(e);
    }
  }, [player, sound]);

  return (
    <div className='midi-player'>
      <div className='player-header'>
        <div className='player-controls'>
          <span ref={playerRef} />
          <label>{midi ? midi.name : 'No MIDI Selected'}</label>
        </div>
      </div>
    </div>
  );
};

export default MIDIPlayer;
