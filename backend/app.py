import datetime
import io
import logging
import os
import zipfile
from tempfile import NamedTemporaryFile

import matplotlib
import melodicnet as mn
from flask import Flask, jsonify, make_response, request, send_file
from flask_cors import CORS

matplotlib.use("Agg")

VALID_FILE_MIMETYPES = ["audio/midi", "audio/mid"]
VALID_MOODS = ["regular", "fast", "slow", "peaceful"]
VALID_KEY_SIGNATURES = {"orig"} | set(mn.globals.PITCH_TO_INT.keys())
VALID_OCTAVE_RANGE = range(1, 8 + 1)
VALID_OUTPUT_LENGTH = range(8, 64 + 1)
VALID_N_OUTPUTS = range(1, 10 + 1)
VALID_TEMPERATURES = (0.5, 1.5)
MODEL_CONFIG_PATH = "./model_config"


def create_app():
    app = Flask("melodicnet backend server")
    app.logger.setLevel(logging.INFO)
    app.logger.info(f"Server started at {datetime.datetime.now()}")
    app.config["MAX_CONTENT_LENGTH"] = mn.globals.MAX_FILE_UPLOAD_BYTES
    CORS(app)

    mn_major = mn.MelodicNet(log_level="INFO", config_path=MODEL_CONFIG_PATH)
    mn_major.load_mappings(prefix="major")
    mn_major.create_model()
    mn_major.load_model_weights(prefix="major")
    app.mn_major = mn_major

    mn_minor = mn.MelodicNet(log_level="INFO", config_path=MODEL_CONFIG_PATH)
    mn_minor.load_mappings(prefix="minor")
    mn_minor.create_model()
    mn_minor.load_model_weights(prefix="minor")
    app.mn_minor = mn_minor

    return app


app = create_app()


def err_response(message):
    return make_response(jsonify(error=message), 400)


def extract_parameters(request, file_fields, form_fields):
    request_data = {}
    for field in file_fields:
        try:
            request_data[field] = request.files[field]
        except KeyError:
            raise KeyError(f"No {field} found in request. Ensure the {field} field is populated")

    for field in form_fields:
        try:
            request_data[field] = request.form[field]
        except KeyError:
            raise KeyError(f"No {field} found in request. Ensure the {field} field is populated")

    return request_data


def load_midi_file(midi_file):
    if not midi_file.mimetype in VALID_FILE_MIMETYPES:
        raise Exception(f"Invalid file type. Only accepts files of the following types: {VALID_FILE_MIMETYPES}")
    try:
        tmp = NamedTemporaryFile(suffix=".mid", delete=False)
        tmp.write(midi_file.stream.read())
        tmp.close()
        input_midi = mn.MIDIUtils.midi_from_file(tmp.name)
        os.remove(tmp.name)
    except Exception as e:
        app.logger.info(str(e))
        raise Exception(f"Invalid file. Could not read file")

    return input_midi


@app.route("/ping", methods=["GET"])
def handle_ping():
    return "", 204


@app.route("/predict", methods=["POST"])
def handle_predict():
    app.logger.info(f"recieved request of type {request.content_type} / size {request.content_length}")
    app.logger.info(f"request files: {request.files}")
    app.logger.info(f"request form: {request.form}")

    # Extract parameters
    try:
        request_data = extract_parameters(
            request,
            ["file"],
            ["keySignature", "minOctave", "maxOctave", "outputCount", "outputLength", "temperature", "seed", "mood"],
        )
    except KeyError as e:
        return err_response(str(e))

    midi_file = request_data["file"]
    key_signature = request_data["keySignature"]
    min_octave = request_data["minOctave"]
    max_octave = request_data["maxOctave"]
    output_count = request_data["outputCount"]
    output_length = request_data["outputLength"]
    temperature = request_data["temperature"]
    seed = request_data["seed"]
    mood = request_data["mood"]

    # Input MIDI
    try:
        input_midi = load_midi_file(midi_file)
    except Exception as e:
        return err_response(str(e))

    # Input Params
    if not key_signature in VALID_KEY_SIGNATURES:
        return err_response(f"Invalid key signature. Only accepts the following values: {VALID_KEY_SIGNATURES}")

    if key_signature == "orig":
        key_signature = None

    if not mood in VALID_MOODS:
        return err_response(f"Invalid mood. Only accepts the following values: {VALID_MOODS}")

    try:
        octave_range = (int(min_octave), int(max_octave))
        assert octave_range[0] < octave_range[1]
        assert octave_range[0] in VALID_OCTAVE_RANGE
        assert octave_range[1] in VALID_OCTAVE_RANGE
    except ValueError:
        return err_response(f"Invalid octave range. Only accepts integers")
    except AssertionError:
        return err_response(
            f"Invalid octave range. Min octave must be less than max octave and in range {VALID_OCTAVE_RANGE[0], VALID_OCTAVE_RANGE[-1]}"
        )

    try:
        output_count = int(output_count)
        assert output_count in VALID_N_OUTPUTS
    except ValueError:
        return err_response(f"Invalid output count. Only accepts integers")
    except AssertionError:
        return err_response(
            f"Invalid output count. Only accepts values in range {VALID_N_OUTPUTS[0], VALID_N_OUTPUTS[-1]}"
        )

    try:
        output_length = int(output_length)
        assert output_length in VALID_OUTPUT_LENGTH
    except ValueError:
        return err_response(f"Invalid midi length. Only accepts integers")
    except AssertionError:
        return err_response(
            f"Invalid midi length. Only accepts values in range {VALID_OUTPUT_LENGTH[0], VALID_OUTPUT_LENGTH[-1]}"
        )

    try:
        temperature = float(temperature)
        assert VALID_TEMPERATURES[0] <= temperature <= VALID_TEMPERATURES[1]
    except ValueError:
        return err_response(f"Invalid temperature. Only accepts floats")
    except AssertionError:
        return err_response(
            f"Invalid temperature. Only accepts values in range {VALID_TEMPERATURES[0], VALID_TEMPERATURES[1]}"
        )

    try:
        if seed == "":
            seed = None
        else:
            seed = int(seed)
            if seed <= 0:
                raise ValueError
    except ValueError:
        return err_response(f"Invalid seed. Only accepts integers")

    prefix = input_midi.analyze("key").type
    if prefix == "major":
        app.logger.info("Using major model")
        model = app.mn_major
    else:
        app.logger.info("Using minor model")
        model = app.mn_minor

    outputs = model.predict(
        input_midi,
        output_length=output_length,
        temperature=temperature,
        n_outputs=output_count,
        octave_range=octave_range,
        key_signature=key_signature,
        random_seed=seed,
        # mood=mood,
    )

    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, mode="w") as zip_file:
        for i, output in enumerate(outputs):
            filename = f"melodicnet_midi_{i+1}"

            output_bytes = mn.MIDIUtils.midi_to_bytes(output)
            image_bytes = mn.MIDIUtils.midi_to_image_bytes(output, title="", dpi=100)

            zip_file.writestr(filename + ".jpg", image_bytes.getvalue())
            zip_file.writestr(filename + ".mid", output_bytes.getvalue())
    zip_bytes.seek(0)

    return send_file(
        zip_bytes,
        mimetype="application/zip",
        download_name="download.zip",
        as_attachment=True,
    )


@app.route("/midi_image", methods=["POST"])
def handle_midi_image():
    app.logger.info(f"recieved request of type {request.content_type} / size {request.content_length}")
    app.logger.info(f"request files: {request.files}")
    app.logger.info(f"request form: {request.form}")

    try:
        request_data = extract_parameters(
            request,
            ["file"],
            [],
        )
    except KeyError as e:
        return err_response(str(e))

    midi_file = request_data["file"]
    try:
        input_midi = load_midi_file(midi_file)
    except Exception as e:
        return err_response(str(e))

    image_bytes = mn.MIDIUtils.midi_to_image_bytes(input_midi, title="", dpi=100)

    return send_file(image_bytes, mimetype="image/jpg")
