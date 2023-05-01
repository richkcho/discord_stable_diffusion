from modules.consts import *
from modules.utils import *

TEST_MODEL = "test model"
TEST_VAE = "test vae"

# inject test model and vae into supported values
if TEST_MODEL not in BASE_PARAMS[MODEL]["supported_values"]:
    BASE_PARAMS[MODEL]["supported_values"].append(TEST_MODEL)
if TEST_VAE not in BASE_PARAMS[VAE]["supported_values"]:
    BASE_PARAMS[VAE]["supported_values"].append(TEST_VAE)


def check_params(values: dict):
    for name, data in ALL_CONFIG.items():
        if name in values:
            if data["type"] == str and "supported_values" in data:
                if values[name] not in data["supported_values"]:
                    raise ValueError(f"Unexpected string {values[name]}")
            elif data["type"] == int or data["type"] == float:
                if values[name] < data["min"] or values[name] > data["max"]:
                    raise ValueError(
                        f"Numeric value out of range: {values[name]}")


def test_validate_params():
    bad_string = "dkjhasdluhlgkjhduskl???????"

    bad_config_min = {}
    bad_config_max = {}

    for name, data in ALL_CONFIG.items():
        if data["type"] == str and "supported_values" in data:
            bad_config_min[name] = bad_string
            bad_config_max[name] = bad_string
        elif data["type"] == int or data["type"] == float:
            bad_config_min[name] = data["min"] - 1
            bad_config_max[name] = data["max"] + 1

    validate_params(bad_config_min)
    validate_params(bad_config_max)

    check_params(bad_config_min)
    check_params(bad_config_max)


def test_message_parsing():
    # basic style test
    initial_values = {
        BATCH_SIZE: 4,
        PROMPT: "a test prompt",
        NEG_PROMPT: "a test negative prompt",
        MODEL: TEST_MODEL,
        VAE: TEST_VAE,
        WIDTH: 256,
        HEIGHT: 512,
        STEPS: 28,
        CFG: 8.5,
        SAMPLER: "Euler",
        SEED: 420,
        SCALE: 1
    }

    parsed_dict = parse_message_str(
        make_message_str(image_url=None, **initial_values))
    assert parsed_dict == initial_values

    # hires test
    highres_values = initial_values | {
        SCALE: 2,
        UPSCALER: "Latent",
        HIGHRES_STEPS: 10,
        DENOISING_STR: 0.66
    }

    parsed_dict = parse_message_str(
        make_message_str(image_url=None, **highres_values))
    assert parsed_dict == highres_values

    # img2img test
    img2img_values = initial_values | {
        RESIZE_MODE: "Just resize",
        DENOISING_STR_IMG2IMG: 0.66,
        "image_url": "https://www.test.image"
    }

    parsed_dict = parse_message_str(
        make_message_str(**img2img_values))
    assert parsed_dict == img2img_values
