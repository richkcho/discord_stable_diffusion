"""
This module contains the main constants used by other modules.

Chatgpt could just copy-paste the descriptions I already wrote for these parameters, but I figure its better to not do
that. Just read the consts, they're named pretty directly and are self explanatory. 
"""


import os

# labels for args
# these commands are unique to stable diffusion generation requests
PROMPT = "prompt"
PROMPT_DESC = "The prompt for stable diffusion. Used to describe what you want in the image output."

NEG_PROMPT = "negative_prompt"
NEG_PROMPT_DESC = "The negative prompt for stable diffusion. Used to describe what you don't want in the image output."

BATCH_SIZE = "batch_size"
BATCH_SIZE_DESC = "how many images to generate at once (may be lowered due to vram constraints)"

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
VAE = "vae"
MODEL = "model"
DENOISING_STR_IMG2IMG = "denoising_strength_img2img"
RESIZE_MODE = "resize_mode"
AUTOSIZE = "autosize"
AUTOSIZE_MAXSIZE = "autosize_maxsize"
RESIZE_SCALE = "resize_scale"
REFINER = "refiner"
REFINER_SWITCH_AT = "refiner_switch_at"

PREFIX_PARAMS = {
    PREFIX: {
        "type": str,
        "default": "",
        "description": "prefix for stable diffusion prompts"
    },
    NEG_PREFIX: {
        "type": str,
        "default": "",
        "description": "prefix for stable diffusion negative prompts"
    }
}

BASE_PARAMS = {
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
        "default": "DPM++ 2M",
        "description": "which sampler to use",
        "supported_values": ['DPM++ 2M', 'DPM++ SDE', 'DPM++ 2M SDE', 'DPM++ 2M SDE Heun', 'DPM++ 2S a', 
            'DPM++ 3M SDE', 'Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM fast', 
            'DPM adaptive', 'Restart', 'DDIM', 'PLMS', 'LCM']
    },
    SEED: {
        "type": int,
        "default": -1,
        "description": "Seed to use for generation. Use -1 to get a random seed",
        "min": -1,
        "max": 4294967294
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
    },
    REFINER: {
        "type": str,
        "default": "None",
        "description": "which model to use for refining (required for SDXL)",
        "supported_values": ["None"]
    },
    REFINER_SWITCH_AT: {
        "type": float,
        "default": 0.8,
        "description": "when to switch to the refiner (when enabled)",
        "min": 0,
        "max": 1
    }
}

UPSCALE_PARAMS = {
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
    }
}

IMG2IMG_PARAMS = {
    AUTOSIZE: {
        "type": bool,
        "default": True,
        "description": "Automatically set width and height, keeping original aspect ratio."
    },
    AUTOSIZE_MAXSIZE: {
        "type": int,
        "default": 512,
        "min": 256,
        "max": 1024,
        "description": "Maximum size for width/height if autosize is set."
    },
    DENOISING_STR_IMG2IMG: {
        "type": float,
        "default": 0.55,
        "description": "denoising strength to use for img2img. Higher values increase deviation from input.",
        "min": 0,
        "max": 1
    },
    RESIZE_MODE: {
        "type": str,
        "default": "Crop and resize",
        "description": "how to resize images for img2img",
        "supported_values": ["Just resize", "Crop and resize", "Resize and fill", "Just resize (latent upscale)"]
    },
    RESIZE_SCALE: {
        "type": float,
        "default": 1,
        "description": f"ratio to resize the image by. Applies after `{AUTOSIZE}` if set.",
        "min": 0.5,
        "max": 2
    },
}


def resize_mode_str_to_int(resize_mode: str) -> int:
    """
    Converts the string value of resize mode to int value

    Args:
        Resize mode string. Assumed to be a valid resize mode. 
    Returns:
        Resize mode int value. 
    """
    return IMG2IMG_PARAMS[RESIZE_MODE]["supported_values"].index(resize_mode)


def update_config():
    """
    Updates the configuration parameters for the stable diffusion model based on the available files in the 
    model directory. It adds the supported vae and model names to the corresponding lists in BASE_PARAMS.

    Args:
        None

    Returns:
        None
    """
    model_dir = "./stable-diffusion-webui/models/Stable-diffusion/"
    supported_vaes = BASE_PARAMS[VAE]["supported_values"]
    supported_models_list = [BASE_PARAMS[MODEL]["supported_values"], BASE_PARAMS[REFINER]["supported_values"]]
    for file in os.listdir(model_dir):
        if not os.path.isfile(os.path.join(model_dir, file)):
            continue

        if file.endswith("vae.pt"):
            supported_vaes.append(file)
        elif file.endswith(".safetensors") or file.endswith(".ckpt"):
            for supported_models in supported_models_list:
                supported_models.append(os.path.splitext(file)[0])


# special keywords (not config keywords)
SPECIAL_KEYWORDS = [PREFIX, NEG_PREFIX, PROMPT, NEG_PROMPT]

# some consts
DEFAULT_IN_FLIGHT_GEN_CAP = 1
QUEUE_MAX_SIZE = 10
BASE_PORT = 6900
SOFT_DEADLINE = 30
# maximum total pixels that fit when latent upscaling
MAX_PIXEL_COUNT_LATENT = 1536 * 1536
# max total pixels that fit when upscaling with R-ESRGAN
MAX_PIXEL_COUNT_ESRGAN = 1024 * 2000

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

# configurable parameters for txt2img
TXT2IMG_CONFIG = PREFIX_PARAMS | BASE_PARAMS | UPSCALE_PARAMS

# configurable parameters for img2img
IMG2IMG_CONFIG = PREFIX_PARAMS | BASE_PARAMS | IMG2IMG_PARAMS

# configurable parameters for again
AGAIN_CONFIG = BASE_PARAMS | UPSCALE_PARAMS | IMG2IMG_PARAMS

# all possible configurable parameters
ALL_CONFIG = PREFIX_PARAMS | BASE_PARAMS | UPSCALE_PARAMS | IMG2IMG_PARAMS

COMMAND_DOCUMENTATION = {}


def get_command_documentation():
    """
    Updates the COMMAND_DOCUMENTATION dictionary from files in the docs directory
    """

    docs_dir = "./modules/docs/"
    for file in os.listdir(docs_dir):
        if not os.path.isfile(os.path.join(docs_dir, file)):
            continue

        if not file.endswith(".md"):
            continue

        name = os.path.splitext(file)[0]
        with open(os.path.join(docs_dir, file), "r", encoding="utf-8") as f:
            doc_str = f.read()

        COMMAND_DOCUMENTATION[name] = doc_str


get_command_documentation()
