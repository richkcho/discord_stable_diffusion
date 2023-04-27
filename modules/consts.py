"""
This module contains the main constants used by other modules.

Chatgpt could just copy-paste the descriptions I already wrote for these parameters, but I figure its better to not do
that. Just read the consts, they're named pretty directly and are self explanatory. 
"""


import os

# labels for commands
# these commands are unique to stable diffusion generation requests
PROMPT = "prompt"
PROMPT_DESC = "The prompt for stable diffusion. Used to describe what you want in the image output."

NEG_PROMPT = "neg_prompt"
NEG_PROMPT_DESC = "The negative prompt for stable diffusion. Used to describe what you don't want in the image output."

# these commands can be set as user preferences
PREFIX = "prefix"
NEG_PREFIX = "neg_prefix"
STEPS = "steps"
CFG = "cfg"
SAMPLER = "sampler"
SEED = "seed"
SCALE = "scale"
DENOISING_STR = "denoising_strength"
HIGHRES_STEPS = "highres_steps"
UPSCALER = "upscaler"
WIDTH = "width"
HEIGHT = "height"
BATCH_SIZE = "batch_size"
VAE = "vae"
MODEL = "model"

PARAM_CONFIG = {
    PREFIX: {
        "type": str,
        "default": "",
        "description": "prefix for stable diffusion prompts"
    },
    NEG_PREFIX: {
        "type": str,
        "default": "",
        "description": "prefix for stable diffusion negative prompts"
    },
    STEPS: {
        "type": int,
        "default": 28,
        "description": "how many steps to use for the sampler",
        "min": 0,
        "max": 50
    },
    CFG: {
        "type": float,
        "default": 8,
        "description":
            "classifier free guidance, higher values force the image generation to be \"closer\" to the prompt",
        "min": 0,
        "max": 30
    },
    SAMPLER: {
        "type": str,
        "default": "DPM++ 2M Karras",
        "description": "which sampler to use",
        "supported_values": ['Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM++ 2S a', 'DPM++ 2M',
                             'DPM++ SDE', 'DPM fast', 'DPM adaptive', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras',
                             'DPM++ 2S a Karras', 'DPM++ 2M Karras', 'DPM++ SDE Karras', "DDIM", "PLMS"]
    },
    SEED: {
        "type": int,
        "default": -1,
        "description": "Seed to use for generation. Use -1 to get a random seed",
        "min": -1,
        "max": 4294967294
    },
    SCALE: {
        "type": float,
        "default": 1,
        "description": "ratio to upscale the image by. Leave at 1 for no upscaling",
        "min": 1,
        "max": 2
    },
    DENOISING_STR: {
        "type": float,
        "default": 0.7,
        "description": "denoising strength to use for upscaler, if scale > 1",
        "min": 0,
        "max": 1
    },
    HIGHRES_STEPS: {
        "type": int,
        "default": 10,
        "description": "how many steps to use for upscaler, if scale > 1",
        "min": 1,
        "max": 20
    },
    UPSCALER: {
        "type": str,
        "default": "Latent",
        "description": "which upscaler to use, if scale > 1",
        "supported_values": ['Latent', 'R-ESRGAN 4x+', 'R-ESRGAN 4x+ Anime6B']
    },
    WIDTH: {
        "type": int,
        "default": 512,
        "description": "image width",
        "min": 256,
        "max": 1024
    },
    HEIGHT: {
        "type": int,
        "default": 512,
        "description": "image height",
        "min": 256,
        "max": 1024
    },
    BATCH_SIZE: {
        "type": int,
        "default": 4,
        "description": "how many images to generate at once (may be lowered due to vram constraints)",
        "min": 1,
        "max": 4
    },
    VAE: {
        "type": str,
        "default": "Automatic",
        "description": "which vae to apply",
        "supported_values": ["Automatic", "None"]
    },
    MODEL: {
        "type": str,
        "default": "anythingV5",
        "description": "which stable diffusion model to use for generation",
        "supported_values": []
    }
}


def update_config():
    """
    Updates the configuration parameters for the stable diffusion model based on the available files in the 
    model directory. It adds the supported vae and model names to the corresponding lists in PARAM_CONFIG.

    Args:
        None

    Returns:
        None
    """
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
SPECIAL_KEYWORDS = [PREFIX, NEG_PREFIX, PROMPT, NEG_PROMPT]

# some consts
DEFAULT_IN_FLIGHT_GEN_CAP = 1
QUEUE_MAX_SIZE = 10
BASE_PORT = 6900
SOFT_DEADLINE = 30

LORAS = []
EMBEDDINGS = []


def update_loras():
    """
    Updates the Lora models and their associated trigger words.

    Args:
        None

    Returns:
        None
    """
    lora_dir = "./stable-diffusion-webui/models/Lora/"
    for file in os.listdir(lora_dir):
        if not os.path.isfile(os.path.join(lora_dir, file)) or not file.endswith(".safetensors"):
            continue

        name = os.path.splitext(file)[0]
        trigger_words = []
        words_path = os.path.join(lora_dir, name + ".words")
        if os.path.isfile(words_path):
            with open(words_path, "r", encoding="utf-8") as f:
                trigger_words += [line.strip() for line in f.readlines()]

        LORAS.append((name, trigger_words))


def update_embeddings():
    """
    Updates the available embeddings and their associated trigger words.

    Args:
        None

    Returns:
        None.
    """
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
            with open(words_path, "r", encoding="utf-8") as f:
                trigger_words += [line.strip() for line in f.readlines()]

        EMBEDDINGS.append((name, trigger_words))


update_config()
update_loras()
update_embeddings()
