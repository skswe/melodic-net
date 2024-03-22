type SampleMIDIMetadata = {
  seed: string;
  temperature: number;
};

const metadata: SampleMIDIMetadata[] = [
  {
    seed: '1',
    temperature: 0.9,
  },
  {
    seed: '13',
    temperature: 0.7,
  },
  {
    seed: '24',
    temperature: 0.5,
  },
  {
    seed: '545',
    temperature: 0.8,
  },
  {
    seed: '508',
    temperature: 0.6,
  },
];

export const FetchSampleMidis = async () => {
  const getFile = async (i: number) => {
    try {
      const { default: midiPath } = await import(
        `../../../assets/midis/${i}.mid`
      );
      const file = await fetch(midiPath);
      const blob = await file.blob();
      const { seed, temperature } = metadata[i - 1];
      return {
        name: `${i}.mid`,
        url: URL.createObjectURL(blob),
        seed,
        temperature,
      };
    } catch (e) {
      console.log(e);
    }
  };

  const midis = await Promise.all(
    Array.from(Array(5).keys()).map((i) => getFile(i + 1))
  );

  return midis;
};
