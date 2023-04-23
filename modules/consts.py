import os

# labels for commands
# Special commands
PREFIX = "prefix"
NEG_PREFIX = "neg-prefix"
GET_PREFIX = "get-prefix"
GET_NEG_PREFIX = "get-neg-prefix"
PROMPT = "prompt"
NEG_PROMPT = "neg-prompt"
RAW_PROMPT = "raw-prompt"
RAW_NEG_PROMPT = "raw-neg-prompt"
GET_MODELS = "get-models"
GET_VAES = "get-vaes"
GET_LORAS = "get-loras"
GET_EMBEDDINGS = "get-embeddings"

# param commands
# param commands support being set to a value with "set-<param name>"
STEPS = "steps"
CFG = "cfg"
SAMPLER = "sampler"
SEED = "seed"
SCALE = "scale"
DENOISING_STR = "denoising-strength"
HIGHRES_STEPS = "highres-steps"
UPSCALER = "upscaler"
WIDTH = "width"
HEIGHT = "height"
BATCH_SIZE = "batch-size"
VAE = "vae"
MODEL = "model"

PARAM_CONFIG = {
    STEPS: {
        "type": int,
        "default": 28,
        "min": 0,
        "max": 50
    },
    CFG: {
        "type": float,
        "default": 11,
        "min": 0,
        "max": 30
    },
    SAMPLER: {
        "type": str,
        "default": "DPM++ 2M Karras",
        "supported_values": ['Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM++ 2S a', 'DPM++ 2M',
                             'DPM++ SDE', 'DPM fast', 'DPM adaptive', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras',
                             'DPM++ 2S a Karras', 'DPM++ 2M Karras', 'DPM++ SDE Karras', "DDIM", "PLMS"]
    },
    SEED: {
        "type": int,
        "default": -1,
        "min": -1,
        "max": 4294967294
    },
    SCALE: {
        "type": float,
        "default": 1,
        "min": 1,
        "max": 2
    },
    DENOISING_STR: {
        "type": float,
        "default": 0.7,
        "min": 0,
        "max": 1
    },
    HIGHRES_STEPS: {
        "type": int,
        "default": 10,
        "min": 1,
        "max": 20
    },
    UPSCALER: {
        "type": str,
        "default": "Latent",
        "supported_values": ['Latent', 'R-ESRGAN 4x+', 'R-ESRGAN 4x+ Anime6B']
    },
    WIDTH: {
        "type": int,
        "default": 512,
        "min": 256,
        "max": 1024
    },
    HEIGHT: {
        "type": int,
        "default": 512,
        "min": 256,
        "max": 1024
    },
    BATCH_SIZE: {
        "type": int,
        "default": 4,
        "min": 1,
        "max": 4
    },
    VAE: {
        "type": str,
        "default": "Automatic",
        "supported_values": ["Automatic", "None"]
    },
    MODEL: {
        "type": str,
        "default": "anythingV5",
        "supported_values": []
    }
}


def update_config():
    model_dir = "./stable-diffusion-webui/models/Stable-diffusion/"
    supported_vaes = PARAM_CONFIG[VAE]["supported_values"]
    supported_models = PARAM_CONFIG[MODEL]["supported_values"]
    for file in os.listdir(model_dir):
        if not os.path.isfile(os.path.join(model_dir, file)):
            continue

        if file.endswith("vae.pt"):
            supported_vaes.append(file)
        elif file.endswith(".safetensors") or file.endswith(".ckpt"):
            supported_models.append(os.path.splitext(file)[0])


# special keywords (not config keywords)
SPECIAL_KEYWORDS = [PREFIX, NEG_PREFIX, GET_PREFIX, GET_NEG_PREFIX, PROMPT, NEG_PROMPT,
                    RAW_PROMPT, RAW_NEG_PROMPT, GET_MODELS, GET_VAES, GET_LORAS, GET_EMBEDDINGS]


# some consts
DEFAULT_TOKEN_GEN_RATE = 2
QUEUE_MAX_SIZE = 10
BASE_PORT = 6900
SOFT_DEADLINE = 30

LORAS = []
EMBEDDINGS = []


def update_loras():
    lora_dir = "./stable-diffusion-webui/models/Lora/"
    for file in os.listdir(lora_dir):
        if not os.path.isfile(os.path.join(lora_dir, file)) or not file.endswith(".safetensors"):
            continue

        name = os.path.splitext(file)[0]
        trigger_words = []
        words_path = os.path.join(lora_dir, name + ".words")
        if os.path.isfile(words_path):
            with open(words_path, "r", encoding="ascii") as f:
                trigger_words += [line.strip() for line in f.readlines()]

        LORAS.append((name, trigger_words))


def update_embeddings():
    embeddings_dir = "./stable-diffusion-webui/embeddings/"
    for file in os.listdir(embeddings_dir):
        if not os.path.isfile(os.path.join(embeddings_dir, file)):
            continue

        if not file.endswith(".pt") and not file.endswith(".safetensors"):
            continue

        name = os.path.splitext(file)[0]
        trigger_words = [name]
        words_path = os.path.join(embeddings_dir, name + ".words")
        if os.path.isfile(words_path):
            with open(words_path, "r", encoding="ascii") as f:
                trigger_words += [line.strip() for line in f.readlines()]

        EMBEDDINGS.append((name, trigger_words))


update_config()
update_loras()
update_embeddings()
