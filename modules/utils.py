"""
Some utility functions for the discord stable diffusion modules. 

Functions:
- async_add_arguments: Decorator to "modify" the signature of a function according to the input dictionary
- max_batch_size: Computes the maximum image batch size that can be handled by the supported GPUs
"""
import asyncio
import base64
import inspect
import io
import re
from functools import wraps
from typing import Optional

import aiohttp
import PIL
from PIL import Image

from modules.consts import *


def async_add_arguments(arguments: dict):
    """
    A decorator function to modify the signature of a function based on the input dictionary.

    Args:
        arguments (dict): A dictionary of arguments to be added to the function signature. Each key in the dictionary is 
        an argument name, and the corresponding value is another dictionary with the following keys:
            - type (type): The type of the argument.

    Returns:
        A function that has its signature modified according to the input dictionary.
    """
    def decorator(func):
        sig = inspect.signature(func)
        parameters = list(sig.parameters.values())

        # remove kwargs from function signature
        parameters.pop()

        # the expected number of args when we invoke func
        func_param_len = len(parameters)

        # create new param list, based off arguments dict
        for arg_name, arg_data in arguments.items():
            parameters.append(
                inspect.Parameter(
                    arg_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=arg_data["type"]
                )
            )

        new_sig = sig.replace(parameters=parameters)

        # new func takes in anything, lmao
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # since func takes in only its args + kwargs dict, fix up args here
            # we expect args to have additional params
            func_args = []
            for i, arg in enumerate(args):
                if i < func_param_len:
                    func_args.append(arg)
                else:
                    kwargs[parameters[i].name] = arg

            await func(*func_args, **kwargs)
        wrapper.__signature__ = new_sig
        return wrapper
    return decorator


def max_batch_size(width: int, height: int, scale: Optional[float], upscaler: Optional[str]) -> int:
    """
    Computes the maximum image batch size that can be handled by the supported GPUs.

    Args:
        width (int): The width of the input image.
        height (int): The height of the input image.
        scale (float): The upscale factor of the image
        upscaler (str): The upscaler to be used, if the image is upscaled.

    Returns:
        The maximum batch size of images that can be processed.
    """
    if scale is None:
        scale = 1
    if upscaler is None:
        upscaler = "Latent"

    max_pixel_count = MAX_PIXEL_COUNT_LATENT if upscaler == "Latent" else MAX_PIXEL_COUNT_ESRGAN
    pixel_count = width * height * scale * scale

    return min(int(max_pixel_count / pixel_count), 4)


def default_batch_size(width: int, height: int, scale: Optional[float]) -> int:
    if scale is None:
        scale = 1

    if width * height * scale * scale > 768 * 768:
        return 2

    return 4


async def download_image(url: str, timeout=10) -> Optional[Image.Image]:
    """
    Downloads an image at a given url, and returns an Image object

    Args:
        url: the url to download the image from
        timeout: how long to let the request go, in seconds
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=timeout) as response:
                if not response.ok:
                    return None
                try:
                    image_data = await response.read()
                    return Image.open(io.BytesIO(image_data))
                except PIL.UnidentifiedImageError:
                    return None
        except asyncio.TimeoutError:
            return None


def b64encode_image(image: Image.Image, fmt: str = "PNG") -> str:
    """
    Converts an image to a base64 encoded image with the specified format.

    Args:
        image: the image to encode
        format: the underlying image format
    """
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


def make_message_str(prompt: str, negative_prompt: str, batch_size: int, image_url: Optional[str], **values: dict) -> str:
    """
    Make ack message from values
    """
    ack_message = f"Generating {batch_size} images for prompt: {prompt}\n"
    ack_message += f"negative prompt: {negative_prompt}\n"
    ack_message += f"Using model: {values[MODEL]}, vae: {values[VAE]}, image size: {values[WIDTH]}x{values[HEIGHT]}\n"
    ack_message += f"Using steps: {values[STEPS]}, cfg: {values[CFG]:.2f}, sampler: {values[SAMPLER]}, seed {values[SEED]}\n"

    if image_url is not None:
        ack_message += f"img2img resize mode: {values[RESIZE_MODE]}, denoising str {values[DENOISING_STR_IMG2IMG]:.2f}, url: {image_url}"
    elif values[SCALE] is not None and values[SCALE] > 1:
        ack_message += f"Upscaling by {values[SCALE]:.2f} using highres upscaler {values[UPSCALER]}, {values[HIGHRES_STEPS]} steps. Denoising str {values[DENOISING_STR]:.2f}\n"

    if values[REFINER] not in ("None", None):
        ack_message += f"Using refiner model: {values[REFINER]}, refiner switch at value: {values[REFINER_SWITCH_AT]:.2f}"

    return ack_message


def parse_message_str(message_str: str) -> dict:
    """
    Get values from a message string created by make_message_str

    Args:
        message_str (str): string generated by make_message_str
    Returns:
        A dictionary containing the parsed values
    """

    arg_regexes = [
        r"Generating (\d+) images for prompt: (.+)",
        r"negative prompt: (.+)"
    ]
    arg_meta = [
        [(BATCH_SIZE, int), (PROMPT, str)],
        [(NEG_PROMPT, str)],
    ]

    param_regexes = [
        r"Using model: (.+?), vae: (.+?), image size: (\d+?)x(\d+)",
        r"Using steps: (\d+?), cfg: (\d*.\d{2}), sampler: (.+?), seed (\d+)",
    ]
    param_keynames = [
        [MODEL, VAE, WIDTH, HEIGHT],
        [STEPS, CFG, SAMPLER, SEED],
    ]

    img2img_regex = r"img2img resize mode: (.+?), denoising str (\d*.\d{2}), url: (.+)"
    img2img_keynames = [RESIZE_MODE, DENOISING_STR_IMG2IMG]

    hires_regex = r"Upscaling by (\d*.\d{2}) using highres upscaler (.+?), (\d+) steps\. Denoising str (\d*.\d{2})"
    hires_keynames = [
        SCALE,
        UPSCALER,
        HIGHRES_STEPS,
        DENOISING_STR
    ]

    refiner_regex = r"Using refiner model: (.+?), refiner switch at value: (\d*.\d{2})"
    refiner_keynames = [REFINER, REFINER_SWITCH_AT]

    lines = message_str.splitlines()

    if len(lines) < (len(arg_regexes) + len(param_regexes)):
        raise ValueError("message string smaller than expected")

    values = {
        SCALE: 1
    }

    # process args first
    for regex, meta in zip(arg_regexes, arg_meta):
        line = lines.pop(0)
        match = re.match(regex, line)

        for i, (key_name, value_type) in enumerate(meta):
            values[key_name] = value_type(match.group(i + 1))

    # then params
    for regex, line_keynames in zip(param_regexes, param_keynames):
        line = lines.pop(0)
        match = re.match(regex, line)

        for i, key_name in enumerate(line_keynames):
            value_type = ALL_CONFIG[key_name]["type"]
            values[key_name] = value_type(match.group(i + 1))

    if len(lines) == 0:
        return validate_params(values)

    # see if img2img or highres
    line = lines.pop(0)
    img2img_match = re.match(img2img_regex, line)
    hires_match = re.match(hires_regex, line)
    if img2img_match is not None:
        for i, key_name in enumerate(img2img_keynames):
            value_type = ALL_CONFIG[key_name]["type"]
            values[key_name] = value_type(img2img_match.group(i + 1))
        values["image_url"] = img2img_match.group(3)
    elif hires_match is not None:
        for i, key_name in enumerate(hires_keynames):
            value_type = ALL_CONFIG[key_name]["type"]
            values[key_name] = value_type(hires_match.group(i + 1))
    else:
        lines.insert(0, line)

    if len(lines) == 0:
        return validate_params(values)

    # check for refiner
    line = lines.pop(0)
    refiner_match = re.match(refiner_regex, line)
    if refiner_match is not None:
        for i, key_name in enumerate(refiner_keynames):
            value_type = ALL_CONFIG[key_name]["type"]
            values[key_name] = value_type(refiner_match.group(i + 1))

    return validate_params(values)


def validate_params(values: dict) -> dict:
    """
    Looks through a param dict and enforces that all parameters are within a valid range

    Args:
        values (dict): dictionary of name, value parameters
    Returns:
        the provided dictionary
    """
    for name, data in ALL_CONFIG.items():
        if name in values:
            if data["type"] == str and "supported_values" in data:
                if values[name] not in data["supported_values"]:
                    values[name] = data["default"]
            elif data["type"] == int or data["type"] == float:
                values[name] = max(values[name], data["min"])
                values[name] = min(values[name], data["max"])
        else:
            values[name] = None

    return values
