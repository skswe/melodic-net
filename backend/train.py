"""This script trains a model using the MelodicNet class.

Usage:

    python3 train.py <identifier> [--log-level <log_level>] [--midi-path <midi_path>] 
        [--refresh-encodings] [--refresh-cleaned-midis] [--n-midis <n_midis>] 
        [--partition <partition>] [--epochs <epochs>]
"""

import argparse

import matplotlib.pyplot as plt
import melodicnet as mn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a model")
    parser.add_argument("identifier", type=str, help="Identifier for the model")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
    )
    parser.add_argument(
        "--midi-path",
        type=str,
        default="data/all_midi/*.mid",
    )
    parser.add_argument(
        "--refresh-encodings",
        action="store_true",
        help="If `True`, recomputes encodings instead of using cached versions. Defaults to False.",
    )
    parser.add_argument(
        "--refresh-cleaned-midis",
        action="store_true",
        help="If `True`, recomputes cleaned MIDIs instead of using cached versions. Defaults to False.",
    )
    parser.add_argument(
        "--n-midis",
        type=int,
        default=100,
        help="Number of MIDIs to read and process from the source directory. Defaults to None.",
    )
    parser.add_argument(
        "--partition",
        type=str,
        default=None,
        help="Key type to filter the loaded MIDIs by (`major` or `minor`). Defaults to None.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=130,
        help="Number of epochs to train the model for. Defaults to 130.",
    )

    args = parser.parse_args()

    driver = mn.MelodicNet(
        log_level=args.log_level,
    )

    driver.load_data(
        midi_path=args.midi_path,
        refresh_encodings=args.refresh_encodings,
        refresh_cleaned_midis=args.refresh_cleaned_midis,
        n_midis=args.n_midis,
        partition=args.partition,
    )

    driver.create_model()

    try:
        driver.train_model_weights(
            epochs=args.epochs,
        )
    except KeyboardInterrupt:
        print("Training interrupted")

    config_path_out = driver.generate_config_files(
        identifier=args.identifier,
        prefix=args.partition,
    )

    print(f"Model configuration files saved to {config_path_out}")
    plt.plot(driver.model.history.history["loss"])
    plt.title("Training loss curve")
    plt.show()
