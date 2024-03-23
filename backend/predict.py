"""This script generates new MIDI using a trained model.

usage:
    python3 predict.py <model_path> <midi_path> [--partition <partition>] [--output-length <output_length>]
        [--temperature <temperature>] [--n-outputs <n_outputs>] [--octave-range <low> <high>]
        [--key-signature <key_signature>] [--random-seed <random_seed>]
"""

import argparse

import melodicnet as mn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate new MIDI using a trained model.")
    parser.add_argument("model_path", type=str, help="Path to the directory containing the trained model files.")
    parser.add_argument("midi_path", type=str, help="Path to the input MIDI file")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
    )
    parser.add_argument(
        "--partition",
        type=str,
        default=None,
        help="Key type to filter the loaded MIDIs by (`major` or `minor`). Defaults to None.",
    )
    parser.add_argument("--output-length", type=int, default=32, help="Output MIDI length in bars. Defaults to 32.")
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.9,
        help="Controls the randomness of the output. Higher values result in more random output. Defaults to 0.9.",
    )
    parser.add_argument("--n-outputs", type=int, default=1, help="Number of output MIDIs to generate. Defaults to 1.")
    parser.add_argument(
        "--octave-range",
        type=int,
        nargs=2,
        default=[3, 7],
        help="Acceptable octave range for notes to be placed in. Defaults to (3, 7).",
    )
    parser.add_argument(
        "--key-signature", type=str, default=None, help="Desired key signature of the output melody. Defaults to None."
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="If provided, the output will be deterministic with the seed. Defaults to None.",
    )
    args = parser.parse_args()

    driver = mn.MelodicNet(
        log_level=args.log_level,
        config_path=args.model_path,
    )
    driver.load_mappings(prefix=args.partition)
    driver.create_model()
    driver.load_model_weights(prefix=args.partition)

    output_midis = driver.predict(
        midi=args.midi_path,
        output_length=args.output_length,
        temperature=args.temperature,
        n_outputs=args.n_outputs,
        octave_range=tuple(args.octave_range),
        key_signature=args.key_signature,
        random_seed=args.random_seed,
    )

    for i, midi in enumerate(output_midis):
        timestamped_dir = mn.utils.misc.make_timestamped_dir("generated_midis")
        output_path = f"{timestamped_dir}/output_{i}.mid"
        midi.write("midi", output_path)

    print(f"Output MIDI saved to {output_path}")
    print(f"{args.n_outputs} MIDI(s) generated successfully.")
